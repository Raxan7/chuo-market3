from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from lms.models import CoursePayment, ModulePayment, CertificatePayment
from lms.revenue import recognize_payment_revenue, revenue_owner_for_course


class Command(BaseCommand):
    help = 'Preview or create instructor revenue entries for historical completed Snippe course/module/certificate payments.'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--dry-run', action='store_true')
        group.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        sources = [
            ('course', CoursePayment.objects.filter(status='completed').select_related('course', 'user')),
            ('module', ModulePayment.objects.filter(status='completed').select_related('module__course', 'user')),
            ('certificate', CertificatePayment.objects.filter(status='completed').select_related('certificate__course', 'user')),
        ]
        eligible = 0
        missing_owner = 0
        existing = 0
        created = 0

        for kind, queryset in sources:
            for payment in queryset.iterator():
                if kind == 'course':
                    course = payment.course
                    if course.is_free or payment.amount <= 0:
                        continue
                elif kind == 'module':
                    course = payment.module.course
                    if course.is_free or payment.amount <= 0:
                        continue
                else:
                    course = payment.certificate.course
                    # A free course can still have a paid certificate.
                    if payment.amount <= 0:
                        continue
                relation_exists = hasattr(payment, 'revenue_entry')
                if relation_exists:
                    existing += 1
                    continue
                owner = revenue_owner_for_course(course)
                if owner is None:
                    missing_owner += 1
                    self.stdout.write(self.style.WARNING(f'SKIP {kind} payment #{payment.pk}: course #{course.pk} has no revenue owner/instructor'))
                    continue
                eligible += 1
                if options['apply']:
                    with transaction.atomic():
                        if recognize_payment_revenue(payment):
                            created += 1

        self.stdout.write(f'Eligible historical payments: {eligible}')
        self.stdout.write(f'Already recorded: {existing}')
        self.stdout.write(f'Missing revenue owner: {missing_owner}')
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry run only: no revenue entries were created.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created {created} historical revenue entries.'))
