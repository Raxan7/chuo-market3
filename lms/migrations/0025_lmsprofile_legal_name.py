from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0024_alter_certificatetemplate_accent_color_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lmsprofile',
            name='legal_name',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Full legal name as it should appear on certificates.',
                max_length=255,
            ),
        ),
    ]
