from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


def repair_unambiguous_revenue_owners(apps, schema_editor):
    """Fill only missing ownership when a course has exactly one instructor."""
    Course = apps.get_model('lms', 'Course')
    through = Course.instructors.through

    for course in Course.objects.filter(revenue_owner__isnull=True).iterator():
        links = list(
            through.objects.filter(course_id=course.pk)
            .order_by('lmsprofile_id')
            .values_list('lmsprofile_id', flat=True)[:2]
        )
        if len(links) == 1:
            course.revenue_owner_id = links[0]
            course.save(update_fields=['revenue_owner'])


class Migration(migrations.Migration):
    dependencies = [('lms', '0043_instructor_revenue_and_payouts')]

    operations = [
        migrations.RemoveConstraint(
            model_name='instructorrevenue',
            name='instructor_revenue_exactly_one_source',
        ),
        migrations.AddField(
            model_name='instructorrevenue',
            name='certificate_payment',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='revenue_entry',
                to='lms.certificatepayment',
            ),
        ),
        migrations.AddConstraint(
            model_name='instructorrevenue',
            constraint=models.CheckConstraint(
                check=(
                    Q(course_payment__isnull=False, module_payment__isnull=True, certificate_payment__isnull=True)
                    | Q(course_payment__isnull=True, module_payment__isnull=False, certificate_payment__isnull=True)
                    | Q(course_payment__isnull=True, module_payment__isnull=True, certificate_payment__isnull=False)
                ),
                name='instructor_revenue_exactly_one_source',
            ),
        ),
        migrations.RunPython(repair_unambiguous_revenue_owners, migrations.RunPython.noop),
    ]
