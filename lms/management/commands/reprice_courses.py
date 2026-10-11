from decimal import Decimal

from django.core.management.base import BaseCommand

from lms.models import Course
from lms.pricing import (
    PricingError,
    apply_course_pricing,
    chargeable_modules,
    preview_course_pricing,
)


class Command(BaseCommand):
    help = (
        "Preview or apply automatic certificate/module pricing. "
        "Dry-run by default."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--apply", action="store_true")
        group.add_argument("--dry-run", action="store_true")

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
        applied = 0

        for course in queryset.iterator():
            modules = chargeable_modules(course)

            try:
                plan = preview_course_pricing(course)
            except PricingError as exc:
                invalid += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"INVALID course #{course.pk} | {course.title} | {exc}"
                    )
                )
                continue

            valid += 1

            current = tuple(
                Decimal(str(module.price or 0))
                for module in modules
            )

            needs_change = current != tuple(plan.module_prices)

            if needs_change:
                changed += 1

            module_text = ", ".join(
                f"{int(price):,}"
                for price in plan.module_prices
            ) or "-"

            self.stdout.write(
                f"course=#{course.pk} "
                f"{'FREE' if course.is_free else 'PAID'} "
                f"package={int(plan.package_price):,} "
                f"certificate={int(plan.certificate_price):,} "
                f"paid_modules={len(plan.module_prices)} "
                f"module_prices=[{module_text}] "
                f"{'CHANGE' if needs_change else 'OK'}"
            )

            if apply_changes:
                apply_course_pricing(course)
                applied += 1

        self.stdout.write("")
        self.stdout.write(f"VALID={valid}")
        self.stdout.write(f"INVALID={invalid}")
        self.stdout.write(f"COURSES_WITH_MODULE_PRICE_CHANGES={changed}")
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
                    "Automatic course pricing applied to valid courses."
                )
            )
