from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0017_alter_course_content_alter_course_summary'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='show_list_ads',
            field=models.BooleanField(
                default=True,
                help_text='When enabled, ads are inserted into product, course, blog, and talent list pages.',
                verbose_name='Show List Ads',
            ),
        ),
    ]
