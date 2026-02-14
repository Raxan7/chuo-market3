# Generated migration for making CourseModule description nullable

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0015_course_content'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coursemodule',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
