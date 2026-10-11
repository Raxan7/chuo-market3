from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand
from django.db import transaction

from lms.models import (
    CertificatePayment,
    CourseEnrollment,
    CoursePayment,
    InstructorRevenue,
    ModulePayment,
)
from lms.revenue import (
    instructor_share_percent,
    recognize_payment_revenue,
    revenue_owner_for_course,
)


CENT = Decimal("0.01")


def split_amount(gross):
    percent = Decimal(str(instructor_share_percent()))
    instructor = (
        Decimal(gross) * percent / Decimal("100")
    ).quantize(CENT, rounding=ROUND_HALF_UP)

    return instructor, Decimal(gross) - instructor


class Command(BaseCommand):
    help = (
        "Reconcile completed course/module/certificate payments against the "
        "instructor revenue ledger. Dry-run by default."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--apply",
            action="store_true",
            help="Create missing ledger entries.",
        )
        group.add_argument(
            "--dry-run",
            action="store_true",
            help="Report only; this is the default.",
        )
        parser.add_argument(
            "--instructor",
            help="Optional instructor username or email.",
        )
        parser.add_argument(
            "--show-legacy",
            action="store_true",
            help="Print legacy approved enrollments with no completed payment.",
        )

    def handle(self, *args, **options):
        apply_changes = bool(options["apply"])
        instructor_filter = (options.get("instructor") or "").strip().lower()

        counters = defaultdict(int)
        money = defaultdict(lambda: Decimal("0"))
        by_instructor = defaultdict(
            lambda: {
                "payments": 0,
                "gross": Decimal("0"),
                "instructor": Decimal("0"),
                "platform": Decimal("0"),
                "missing": 0,
            }
        )
        discrepancies = []

        sources = (
            (
                "course",
                CoursePayment.objects.filter(status="completed").select_related(
                    "course", "user"
                ),
            ),
            (
                "module",
                ModulePayment.objects.filter(status="completed").select_related(
                    "module__course", "module", "user"
                ),
            ),
            (
                "certificate",
                CertificatePayment.objects.filter(status="completed").select_related(
                    "certificate__course", "certificate", "user"
                ),
            ),
        )

        for kind, queryset in sources:
            for payment in queryset.iterator():
                gross = Decimal(payment.amount or 0)

                if gross <= 0:
                    counters["non_positive"] += 1
                    continue

                if kind == "course":
                    course = payment.course
                    module = None
                    source_filter = {"course_payment": payment}

                    if course.is_free:
                        counters["free_course_payment"] += 1
                        continue

                elif kind == "module":
                    course = payment.module.course
                    module = payment.module
                    source_filter = {"module_payment": payment}

                    if course.is_free:
                        counters["free_module_payment"] += 1
                        continue

                else:
                    course = payment.certificate.course
                    module = None
                    source_filter = {"certificate_payment": payment}

                counters["eligible"] += 1

                existing = InstructorRevenue.objects.filter(
                    **source_filter
                ).select_related("instructor", "student", "course").first()

                owner = revenue_owner_for_course(course)

                if owner is None:
                    counters["missing_owner"] += 1
                    self.stderr.write(
                        f"MISSING OWNER: {kind} payment #{payment.pk}, "
                        f"course #{course.pk} {course.title}"
                    )
                    continue

                identity_values = {
                    (owner.user.username or "").lower(),
                    (owner.user.email or "").lower(),
                }

                if instructor_filter and instructor_filter not in identity_values:
                    continue

                instructor_amount, platform_amount = split_amount(gross)
                key = owner.user.username or owner.user.email or f"profile-{owner.pk}"

                summary = by_instructor[key]
                summary["payments"] += 1
                summary["gross"] += gross
                summary["instructor"] += instructor_amount
                summary["platform"] += platform_amount

                money["expected_gross"] += gross
                money["expected_instructor"] += instructor_amount
                money["expected_platform"] += platform_amount

                if existing:
                    counters["existing"] += 1

                    row_errors = []

                    if existing.course_id != course.pk:
                        row_errors.append("course mismatch")

                    if existing.student_id != payment.user_id:
                        row_errors.append("student mismatch")

                    if Decimal(existing.gross_amount) != gross:
                        row_errors.append("gross mismatch")

                    if (
                        Decimal(existing.instructor_amount)
                        + Decimal(existing.platform_amount)
                        != Decimal(existing.gross_amount)
                    ):
                        row_errors.append("split does not balance")

                    if existing.instructor_id != owner.pk:
                        row_errors.append("revenue owner mismatch")

                    expected_module_id = module.pk if module else None

                    if existing.module_id != expected_module_id:
                        row_errors.append("module mismatch")

                    if row_errors:
                        counters["discrepancies"] += 1
                        discrepancies.append(
                            (
                                kind,
                                payment.pk,
                                existing.pk,
                                ", ".join(row_errors),
                            )
                        )

                    continue

                counters["missing"] += 1
                summary["missing"] += 1

                if apply_changes:
                    with transaction.atomic():
                        row = recognize_payment_revenue(payment)

                    if row is None:
                        counters["creation_failed"] += 1
                        self.stderr.write(
                            self.style.ERROR(
                                f"FAILED: {kind} payment #{payment.pk}"
                            )
                        )
                    else:
                        counters["created"] += 1

        # Find legacy approved paid-course access that has no payment evidence.
        # We REPORT these only. Guessing historical revenue from enrollment
        # would be financially unsafe because historical prices may have changed.
        legacy = []

        enrollments = CourseEnrollment.objects.filter(
            payment_status="approved",
            course__is_free=False,
        ).select_related("student__user", "course")

        enrollment_field_names = {
            f.name for f in CourseEnrollment._meta.get_fields()
        }

        if "admin_granted_access" in enrollment_field_names:
            enrollments = enrollments.filter(admin_granted_access=False)

        for enrollment in enrollments.iterator():
            user = enrollment.student.user

            has_payment = CoursePayment.objects.filter(
                user=user,
                course=enrollment.course,
                status="completed",
            ).exists()

            if not has_payment:
                legacy.append(enrollment)
                counters["legacy_without_payment"] += 1

        mode = "APPLY" if apply_changes else "DRY_RUN"

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"MODE={mode}"))
        self.stdout.write(f"COMPLETED_ELIGIBLE={counters['eligible']}")
        self.stdout.write(f"LEDGER_EXISTING={counters['existing']}")
        self.stdout.write(f"LEDGER_MISSING={counters['missing']}")
        self.stdout.write(f"LEDGER_CREATED={counters['created']}")
        self.stdout.write(f"MISSING_REVENUE_OWNER={counters['missing_owner']}")
        self.stdout.write(f"DISCREPANCIES={counters['discrepancies']}")
        self.stdout.write(
            f"LEGACY_APPROVED_ENROLLMENTS_WITHOUT_PAYMENT="
            f"{counters['legacy_without_payment']}"
        )
        self.stdout.write(
            f"EXPECTED_GROSS_TZS={money['expected_gross']:.2f}"
        )
        self.stdout.write(
            f"EXPECTED_INSTRUCTOR_SHARE_TZS={money['expected_instructor']:.2f}"
        )
        self.stdout.write(
            f"EXPECTED_PLATFORM_SHARE_TZS={money['expected_platform']:.2f}"
        )

        self.stdout.write("")
        self.stdout.write("PER_INSTRUCTOR:")

        for key in sorted(by_instructor):
            row = by_instructor[key]
            self.stdout.write(
                f"  {key}: payments={row['payments']} "
                f"missing={row['missing']} "
                f"gross={row['gross']:.2f} "
                f"instructor={row['instructor']:.2f} "
                f"platform={row['platform']:.2f}"
            )

        if discrepancies:
            self.stderr.write("")
            self.stderr.write("LEDGER DISCREPANCIES:")

            for kind, payment_id, revenue_id, reason in discrepancies[:50]:
                self.stderr.write(
                    f"  {kind} payment #{payment_id} -> "
                    f"revenue #{revenue_id}: {reason}"
                )

        if legacy and options.get("show_legacy"):
            self.stderr.write("")
            self.stderr.write(
                "APPROVED PAID ENROLLMENTS WITHOUT COMPLETED PAYMENT:"
            )

            for enrollment in legacy[:50]:
                self.stderr.write(
                    f"  enrollment #{enrollment.pk} "
                    f"user={enrollment.student.user.username} "
                    f"course=#{enrollment.course_id} "
                    f"{enrollment.course.title}"
                )

        if not apply_changes:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Dry run only. No instructor revenue rows were created."
                )
            )
        elif counters["discrepancies"]:
            self.stderr.write(
                self.style.WARNING(
                    "Missing rows were created, but existing discrepancies "
                    "were NOT rewritten automatically."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Instructor revenue reconciliation completed."
                )
            )
