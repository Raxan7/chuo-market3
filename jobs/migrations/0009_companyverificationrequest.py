# Generated for ChuoSmart employer verification workflow.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import jobs.storage


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('jobs', '0008_alter_jobcourserecommendation_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyVerificationRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_certificate', models.FileField(storage=jobs.storage.private_verification_storage, upload_to='jobs/verifications/business/', verbose_name='Business Registration Certificate')),
                ('tin_certificate', models.FileField(blank=True, null=True, storage=jobs.storage.private_verification_storage, upload_to='jobs/verifications/tin/', verbose_name='TIN Certificate')),
                ('verification_notes', models.TextField(blank=True, verbose_name='Applicant Notes')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20, verbose_name='Status')),
                ('admin_notes', models.TextField(blank=True, verbose_name='Reviewer Notes')),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='verification_requests', to='jobs.company')),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='company_verification_requests', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_company_verification_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-requested_at']},
        ),
    ]
