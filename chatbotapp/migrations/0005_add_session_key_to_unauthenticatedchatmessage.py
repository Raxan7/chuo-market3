from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('chatbotapp', '0004_unauthenticatedchatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='unauthenticatedchatmessage',
            name='session_key',
            field=models.CharField(max_length=40, null=True, blank=True),
        ),
    ]
