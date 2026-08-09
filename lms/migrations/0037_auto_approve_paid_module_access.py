from datetime import datetime

from django.db import migrations


def auto_approve_paid_module_access(apps, schema_editor):
    """Grant module access automatically for requests backed by a completed payment.

    Module access is now granted as soon as the Snippe payment is completed, so
    any pending requests created before that behaviour shipped (all of which have
    a completed payment behind them) are approved here. This mirrors what
    ModuleAccessRequest.approve() does at runtime, but inline so historical models
    are used (the method does not exist in older code).
    """
    ModuleAccessRequest = apps.get_model('lms', 'ModuleAccessRequest')
    ModuleAccessGrant = apps.get_model('lms', 'ModuleAccessGrant')
    CourseEnrollment = apps.get_model('lms', 'CourseEnrollment')
    now = datetime.now()

    pending = ModuleAccessRequest.objects.select_related(
        'student', 'module', 'module__course', 'payment',
    ).filter(status='pending')

    count = 0
    for request_obj in pending:
        if request_obj.payment is None or request_obj.payment.status != 'completed':
            continue

        grant, _ = ModuleAccessGrant.objects.get_or_create(
            student=request_obj.student,
            module=request_obj.module,
            defaults={
                'active': True,
                'notes': 'Auto-granted after successful payment.',
                'granted_by': None,
            },
        )
        if not grant.active:
            grant.active = True
            grant.save(update_fields=['active'])

        CourseEnrollment.objects.get_or_create(
            student=request_obj.student,
            course=request_obj.module.course,
            defaults={
                'payment_status': 'pending',
                'payment_notes': 'Auto-enrolled because module access was granted after payment.',
            },
        )

        request_obj.status = 'approved'
        request_obj.approved_at = now
        request_obj.save(update_fields=['status', 'approved_at', 'updated_at'])
        count += 1

    if count:
        print(f"Auto-approved {count} paid module access request(s).")


def reverse_noop(apps, schema_editor):
    """No reverse — grants already issued stay in place."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0036_coursemodule_price_modulepayment_moduleaccessrequest'),
    ]

    operations = [
        migrations.RunPython(auto_approve_paid_module_access, reverse_noop),
    ]
