# Generated by Django 4.2.20 on 2025-07-08 10:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('lms', '0009_ensure_site_settings'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdExemptUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ad_exemption', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Ad Exempt User',
                'verbose_name_plural': 'Ad Exempt Users',
            },
        ),
    ]
