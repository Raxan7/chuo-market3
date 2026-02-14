# Generated migration for adding course content field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0014_course_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='summary',
            field=models.TextField(blank=True, null=True, help_text='Brief summary of the course'),
        ),
        migrations.AddField(
            model_name='course',
            name='content',
            field=models.TextField(blank=True, null=True, help_text='Detailed course description and content'),
        ),
    ]
