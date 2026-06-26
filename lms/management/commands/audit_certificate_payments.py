"""
Management command to audit and fix certificate payment records.

Usage:
    python manage.py audit_certificate_payments                   # audit only (read-only)
    python manage.py audit_certificate_payments --fix             # fix all inconsistencies found
    python manage.py audit_certificate_payments --user-id 3       # filter by user
    python manage.py audit_certificate_payments --cert-id CHUO-...  # filter by certificate
    python manage.py audit_certificate_payments --revert-completed  # revert all completed payments
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from lms.models import CertificatePayment, StudentCertificate, CourseEnrollment, LMSProfile


class Command(BaseCommand):
    help = 'Audit and optionally fix certificate payment records'

    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true', help='Apply fixes')
        parser.add_argument('--user-id', type=int, help='Filter by user ID')
        parser.add_argument('--cert-id', type=str, help='Filter by certificate ID')
        parser.add_argument('--revert-completed', type=str, metavar='CERT_ID',
                            help='Revert a specific completed certificate (use with --fix)')
        parser.add_argument('--all', action='store_true',
                            help='Show all payment records (default: only anomalies)')

    def handle(self, *args, **options):
        fix = options['fix']
        user_id = options['user_id']
        cert_id = options['cert_id']
        revert_cert = options.get('revert_completed')
        show_all = options['all']

        qs = CertificatePayment.objects.select_related('user', 'certificate').order_by('-created_at')

        if user_id:
            qs = qs.filter(user_id=user_id)
        if cert_id:
            qs = qs.filter(certificate__certificate_id=cert_id)

        if revert_cert and fix:
            self._revert_completed(revert_cert)
            return

        self.stdout.write(self.style.NOTICE('=== Certificate Payment Audit ==='))
        self.stdout.write(f'Total records: {qs.count()}')

        # --- Find anomalies ---
        anomalies = []
        for payment in qs:
            issues = []

            # Completed but no Snippe reference
            if payment.status == 'completed' and not payment.snippe_reference:
                issues.append('completed but missing snippe_reference')

            # Cancelled or expired but has a snippe_reference starting with SN (should be ok)
            if payment.status == 'pending' and payment.created_at < timezone.now() - timezone.timedelta(hours=2):
                issues.append('pending for >2 hours (likely orphaned)')

            # Multiple completed payments for same (certificate, user)
            if payment.status == 'completed':
                dupes = CertificatePayment.objects.filter(
                    certificate=payment.certificate,
                    user=payment.user,
                    status='completed',
                ).exclude(id=payment.id).count()
                if dupes:
                    issues.append(f'duplicate completed ({dupes} others exist)')

            if issues or show_all:
                anomalies.append((payment, issues))

        if anomalies:
            self.stdout.write(f'\nRecords checked: {len(anomalies)}')
            self.stdout.write(f'{"ID":>6} {"User":>12} {"Cert":>24} {"Status":>12} {"Ref":>20} {"Issues"}')
            self.stdout.write('-' * 100)
            for payment, issues in anomalies:
                label = ', '.join(issues) if issues else '(OK)'
                if issues:
                    label = self.style.WARNING(label)
                self.stdout.write(
                    f'{payment.id:>6} {payment.user_id:>12} '
                    f'{payment.certificate.certificate_id:>24} '
                    f'{payment.status:>12} {payment.snippe_reference:>20} '
                    f'{label}'
                )

            # Summary
            anomaly_count = sum(1 for _, issues in anomalies if issues)
            if anomaly_count:
                self.stdout.write(
                    self.style.WARNING(f'\n** {anomaly_count} anomaly/ies found.')
                )
            else:
                self.stdout.write(self.style.SUCCESS('\nOK. No anomalies found.'))
        else:
            self.stdout.write(self.style.SUCCESS('\nOK. No records found.'))

    def _revert_completed(self, cert_id):
        """Revert a completed payment and revoke download access."""
        try:
            cert = StudentCertificate.objects.get(certificate_id=cert_id)
        except StudentCertificate.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Certificate not found: {cert_id}'))
            return

        payments = CertificatePayment.objects.filter(
            certificate=cert, status='completed'
        )
        if not payments.exists():
            self.stdout.write(self.style.ERROR(f'No completed payments for {cert_id}'))
            return

        for payment in payments:
            old_status = payment.status
            payment.status = 'cancelled'
            payment.save(update_fields=['status', 'updated_at'])
            self.stdout.write(
                self.style.WARNING(
                    f'Reverted payment #{payment.id}: {old_status} -> cancelled '
                    f'(user={payment.user_id}, ref={payment.snippe_reference})'
                )
            )

        self.stdout.write(self.style.SUCCESS(f'\nOK. All completed payments for {cert_id} reverted to cancelled.'))
        self.stdout.write(
            'The user will no longer be able to download this certificate '
            'until a new successful payment is recorded.'
        )
