# Generated by Django 4.2.20 on 2025-07-23 11:20

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('lms', '0010_add_ad_exempt_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('phone_number', models.CharField(max_length=20)),
                ('instructions', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='lms/payment_methods/')),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.AddField(
            model_name='courseenrollment',
            name='payment_approved_by',
            field=models.ForeignKey(blank=True, help_text='Admin who approved the payment', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_enrollments', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='courseenrollment',
            name='payment_approved_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='courseenrollment',
            name='payment_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='courseenrollment',
            name='payment_notes',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='courseenrollment',
            name='payment_proof',
            field=models.ImageField(blank=True, help_text='Upload proof of payment for premium courses', null=True, upload_to='lms/payment_proofs/'),
        ),
        migrations.AddField(
            model_name='courseenrollment',
            name='payment_status',
            field=models.CharField(choices=[('not_required', 'Not Required'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='not_required', help_text='Payment status for premium courses', max_length=20),
        ),
        migrations.AddField(
            model_name='courseenrollment',
            name='payment_method',
            field=models.ForeignKey(blank=True, help_text='Payment method used', null=True, on_delete=django.db.models.deletion.SET_NULL, to='lms.paymentmethod'),
        ),
    ]
