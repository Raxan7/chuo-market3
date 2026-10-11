from decimal import Decimal

from django.core.management.base import BaseCommand

from lms.models import Course
from lms.pricing import (
    PricingError,
    apply_course_pricing,
    calculate_pricing,
    chargeable_modules,
    normalize_package_price_for_modules,
)


class Command(BaseCommand):
    help = (
        "Preview or apply automatic course/module/certificate pricing. "
        "Invalid paid package prices are automatically increased to the "
        "smallest valid TSh 500 amount. Dry-run by default."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()

        group.add_argument(
            "--apply",
            action="store_true",
        )
        group.add_argument(
            "--dry-run",
            action="store_true",
        )

        parser.add_argument(
            "--course-id",
            type=int,
            help="Limit processing to one course.",
        )

    def handle(self, *args, **options):
        apply_changes = bool(options["apply"])

        queryset = Course.objects.all().order_by("id")

        if options.get("course_id"):
            queryset = queryset.filter(pk=options["course_id"])

        valid = 0
        invalid = 0
        changed = 0
        auto_increased = 0
        applied = 0

        for course in queryset.iterator():
            modules = chargeable_modules(course)
            current_price = Decimal(str(course.price or 0))

            try:
                if course.is_free:
                    target_price = Decimal("0")
                else:
                    target_price = normalize_package_price_for_modules(
                        current_price,
                        len(modules),
                    )

                plan = calculate_pricing(
                    target_price,
                    len(modules),
                    is_free=course.is_free,
                )

            except PricingError as exc:
                # This should now only happen for genuinely malformed data,
                # not simply because a package is too cheap.
                invalid += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"INVALID course #{course.pk} | "
                        f"{course.title} | {exc}"
                    )
                )
                continue

            valid += 1

            price_will_increase = (
                not course.is_free
                and target_price > current_price
            )

            if price_will_increase:
                auto_increased += 1

            current_module_prices = tuple(
                Decimal(str(module.price or 0))
                for module in modules
            )

            module_prices_change = (
                current_module_prices
                != tuple(plan.module_prices)
            )

            needs_change = (
                price_will_increase
                or module_prices_change
            )

            if needs_change:
                changed += 1

            if price_will_increase:
                price_text = (
                    f"AUTO-INCREASE "
                    f"{int(current_price):,} -> "
                    f"{int(target_price):,}"
                )
            else:
                price_text = f"package={int(target_price):,}"

            module_text = ", ".join(
                f"{int(price):,}"
                for price in plan.module_prices
            ) or "-"

            self.stdout.write(
                f"course=#{course.pk} "
                f"{'FREE' if course.is_free else 'PAID'} "
                f"{price_text} "
                f"certificate={int(plan.certificate_price):,} "
                f"paid_modules={len(plan.module_prices)} "
                f"module_prices=[{module_text}] "
                f"{'CHANGE' if needs_change else 'OK'}"
            )

            if apply_changes:
                apply_course_pricing(
                    course,
                    auto_raise=True,
                )
                applied += 1

        self.stdout.write("")
        self.stdout.write(f"VALID={valid}")
        self.stdout.write(f"INVALID={invalid}")
        self.stdout.write(
            f"AUTO_INCREASED_COURSE_PRICES={auto_increased}"
        )
        self.stdout.write(
            f"COURSES_WITH_PRICING_CHANGES={changed}"
        )
        self.stdout.write(f"APPLIED={applied}")

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run only. No prices were changed."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Automatic course pricing applied."
                )
            )
