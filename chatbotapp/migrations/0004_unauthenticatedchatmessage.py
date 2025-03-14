from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('chatbotapp', '0003_chatmessage_session_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnauthenticatedChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_message', models.TextField()),
                ('bot_response', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
