# Generated by Django 4.2.20 on 2025-07-06 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0003_contentaccess'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='is_free',
            field=models.BooleanField(default=True, help_text='Whether this course is free or paid'),
        ),
    ]
