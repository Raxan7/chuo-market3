# Generated migration for adding course content field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0014_course_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='content',
            field=models.TextField(blank=True, default='', help_text='Detailed course description and content'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='course',
            name='summary',
            field=models.TextField(blank=True, default='', help_text='Brief summary of the course'),
            preserve_default=False,
        ),
    ]
