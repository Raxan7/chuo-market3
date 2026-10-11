from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings


STEP = Decimal("500")
MIN_COMPONENT = Decimal("1000")
FREE_CERTIFICATE_PRICE = Decimal("15000")
CERTIFICATE_RATIO = Decimal("0.30")


class PricingError(ValueError):
    pass


@dataclass(frozen=True)
class PricingPlan:
    package_price: Decimal
    certificate_price: Decimal
    module_prices: tuple
    module_pool: Decimal

    @property
    def total(self):
        return self.certificate_price + sum(self.module_prices, Decimal("0"))


def _money(value):
    try:
        amount = Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        raise PricingError("Price must be a valid Tanzanian shilling amount.")

    if amount != amount.to_integral_value():
        raise PricingError("TZS prices must use whole shillings.")

    return amount.quantize(Decimal("1"))


def _round_to_step(value):
    value = Decimal(value)
    return (
        (value / STEP).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        * STEP
    )


def validate_component_price(value, label="Price"):
    amount = _money(value)

    if amount < MIN_COMPONENT:
        raise PricingError(
            f"{label} cannot be below TSh {int(MIN_COMPONENT):,}."
        )

    if amount % STEP:
        raise PricingError(
            f"{label} must be in increments of TSh {int(STEP):,}."
        )

    return amount


def validate_package_price(value):
    return validate_component_price(value, "Course package price")


def certificate_price_from_package(package_price):
    total = validate_package_price(package_price)
    certificate = _round_to_step(total * CERTIFICATE_RATIO)

    if certificate < MIN_COMPONENT:
        certificate = MIN_COMPONENT

    if certificate > total:
        certificate = total

    return certificate


def minimum_valid_package_price(module_count):
    module_count = int(module_count or 0)

    if module_count <= 0:
        return MIN_COMPONENT

    candidate = max(
        MIN_COMPONENT,
        MIN_COMPONENT * Decimal(module_count + 1),
    )

    candidate = _round_to_step(candidate)

    while True:
        certificate = certificate_price_from_package(candidate)
        module_pool = candidate - certificate

        if module_pool >= MIN_COMPONENT * module_count:
            return candidate

        candidate += STEP


def calculate_pricing(package_price, module_count, is_free=False):
    module_count = max(0, int(module_count or 0))

    if is_free:
        return PricingPlan(
            package_price=Decimal("0"),
            certificate_price=FREE_CERTIFICATE_PRICE,
            module_prices=tuple(Decimal("0") for _ in range(module_count)),
            module_pool=Decimal("0"),
        )

    total = validate_package_price(package_price)
    certificate = certificate_price_from_package(total)
    module_pool = total - certificate

    if module_count == 0:
        return PricingPlan(
            package_price=total,
            certificate_price=certificate,
            module_prices=tuple(),
            module_pool=module_pool,
        )

    required = MIN_COMPONENT * module_count

    if module_pool < required:
        minimum = minimum_valid_package_price(module_count)
        raise PricingError(
            f"TSh {int(total):,} is too low for {module_count} paid modules. "
            f"With the 30% certificate / 70% learning model and a minimum "
            f"TSh {int(MIN_COMPONENT):,} per module, this course needs a "
            f"package price of at least TSh {int(minimum):,}."
        )

    if module_pool % STEP:
        raise PricingError(
            "The learning allocation cannot be distributed in TSh 500 increments."
        )

    total_units = int(module_pool / STEP)
    minimum_units = int(MIN_COMPONENT / STEP)

    base_units, remainder = divmod(total_units, module_count)

    if base_units < minimum_units:
        minimum = minimum_valid_package_price(module_count)
        raise PricingError(
            f"Course price is too low. Minimum valid package price is "
            f"TSh {int(minimum):,}."
        )

    prices = []
    for index in range(module_count):
        units = base_units + (1 if index < remainder else 0)
        prices.append(Decimal(units) * STEP)

    if sum(prices, Decimal("0")) != module_pool:
        raise PricingError("Internal pricing allocation mismatch.")

    if certificate + sum(prices, Decimal("0")) != total:
        raise PricingError("Package pricing does not balance to the course total.")

    return PricingPlan(
        package_price=total,
        certificate_price=certificate,
        module_prices=tuple(prices),
        module_pool=module_pool,
    )


def chargeable_modules(course):
    from .models import CourseModule

    return list(
        CourseModule.objects.filter(
            course=course,
            skip_assessment=False,
        ).order_by("order", "id")
    )


def preview_course_pricing(course):
    modules = chargeable_modules(course)

    return calculate_pricing(
        course.price,
        len(modules),
        is_free=course.is_free,
    )


def apply_course_pricing(course):
    from .models import CertificateTemplate, CourseModule

    all_modules = CourseModule.objects.filter(course=course)
    modules = chargeable_modules(course)

    if course.is_free:
        all_modules.update(price=Decimal("0"))

        CertificateTemplate.objects.filter(course=course).update(
            certificate_price=FREE_CERTIFICATE_PRICE
        )

        return calculate_pricing(
            0,
            len(modules),
            is_free=True,
        )

    plan = calculate_pricing(course.price, len(modules), is_free=False)

    # Overview / skip-assessment modules remain free.
    CourseModule.objects.filter(
        course=course,
        skip_assessment=True,
    ).update(price=Decimal("0"))

    for module, price in zip(modules, plan.module_prices):
        CourseModule.objects.filter(pk=module.pk).update(price=price)

    # Keep certificate-template UI in sync, although checkout uses the
    # centralized pricing engine as the authoritative source.
    CertificateTemplate.objects.filter(course=course).update(
        certificate_price=plan.certificate_price
    )

    return plan


def effective_certificate_price(course, template=None):
    """
    During rollout, AUTO_COURSE_PRICING_ENABLED controls whether the new
    package model is authoritative. This preserves old behavior until the
    production dry-run has been reviewed.
    """
    if getattr(settings, "AUTO_COURSE_PRICING_ENABLED", False):
        if course.is_free:
            return FREE_CERTIFICATE_PRICE

        return certificate_price_from_package(course.price)

    if template is not None and getattr(template, "certificate_price", None):
        return _money(template.certificate_price)

    return _money(getattr(settings, "CERTIFICATE_PRICE", 15000))


def full_course_payment_includes_certificate(user, course):
    if not getattr(settings, "AUTO_COURSE_PRICING_ENABLED", False):
        return False

    if not user or not getattr(user, "is_authenticated", False):
        return False

    if course.is_free:
        return False

    from .models import CoursePayment

    return CoursePayment.objects.filter(
        user=user,
        course=course,
        status="completed",
    ).exists()
