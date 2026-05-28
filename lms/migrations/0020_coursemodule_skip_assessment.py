from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0019_certificatetemplate_alter_quiz_pass_mark_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursemodule',
            name='skip_assessment',
            field=models.BooleanField(
                default=False,
                help_text='Mark this module as an overview or introduction module without a quiz.',
                verbose_name='Skip Assessment',
            ),
        ),
    ]
