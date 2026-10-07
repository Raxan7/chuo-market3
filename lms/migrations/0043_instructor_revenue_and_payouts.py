from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


def assign_existing_revenue_owners(apps, schema_editor):
    Course = apps.get_model('lms', 'Course')
    through = Course.instructors.through
    # M2M through field names are course_id and lmsprofile_id in this project.
    for course in Course.objects.filter(revenue_owner__isnull=True).iterator():
        link = through.objects.filter(course_id=course.pk).order_by('lmsprofile_id').first()
        if link:
            course.revenue_owner_id = link.lmsprofile_id
            course.save(update_fields=['revenue_owner'])


class Migration(migrations.Migration):
    dependencies = [('lms', '0042_certificate_watermark_opacity')]

    operations = [
        migrations.AddField(
            model_name='course', name='revenue_owner',
            field=models.ForeignKey(blank=True, help_text='Instructor who receives the instructor revenue share for this course.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='courses_revenue_owned', to='lms.lmsprofile'),
        ),
        migrations.CreateModel(
            name='PayoutProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payout_method', models.CharField(choices=[('mobile_money', 'Mobile Money'), ('bank', 'Bank Account')], max_length=20)),
                ('account_name', models.CharField(max_length=150)),
                ('phone_number', models.CharField(blank=True, default='', max_length=40)),
                ('mobile_network', models.CharField(blank=True, default='', max_length=80)),
                ('bank_name', models.CharField(blank=True, default='', max_length=120)),
                ('bank_account_number', models.CharField(blank=True, default='', max_length=80)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('instructor', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payout_profile', to='lms.lmsprofile')),
            ],
            options={'verbose_name': 'Instructor Payout Profile', 'verbose_name_plural': 'Instructor Payout Profiles'},
        ),
        migrations.CreateModel(
            name='PayoutRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('payout_method', models.CharField(choices=[('mobile_money', 'Mobile Money'), ('bank', 'Bank Account')], max_length=20)),
                ('payout_details_snapshot', models.TextField(help_text='Masked payout details for normal display.')),
                ('payout_details_private', models.TextField(help_text='Full payout details. Restrict to authorized admins.')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('paid', 'Paid'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('admin_note', models.TextField(blank=True, default='')),
                ('instructor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payout_requests', to='lms.lmsprofile')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_instructor_payouts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Instructor Payout Request', 'verbose_name_plural': 'Instructor Payout Requests', 'ordering': ['-requested_at']},
        ),
        migrations.CreateModel(
            name='InstructorRevenue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gross_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('instructor_share_percent', models.DecimalField(decimal_places=2, max_digits=5)),
                ('instructor_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('platform_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('earned_at', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='revenue_entries', to='lms.course')),
                ('course_payment', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='revenue_entry', to='lms.coursepayment')),
                ('instructor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='revenue_entries', to='lms.lmsprofile')),
                ('module', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='revenue_entries', to='lms.coursemodule')),
                ('module_payment', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='revenue_entry', to='lms.modulepayment')),
                ('payout_request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='revenue_entries', to='lms.payoutrequest')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='instructor_revenue_purchases', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Instructor Revenue Entry', 'verbose_name_plural': 'Instructor Revenue Entries', 'ordering': ['-earned_at']},
        ),
        migrations.AddConstraint(
            model_name='instructorrevenue',
            constraint=models.CheckConstraint(check=(Q(('course_payment__isnull', False), ('module_payment__isnull', True)) | Q(('course_payment__isnull', True), ('module_payment__isnull', False))), name='instructor_revenue_exactly_one_source'),
        ),
        migrations.RunPython(assign_existing_revenue_owners, migrations.RunPython.noop),
    ]
