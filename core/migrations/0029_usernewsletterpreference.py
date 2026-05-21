from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_newsletter_preferences(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserNewsletterPreference = apps.get_model('core', 'UserNewsletterPreference')

    for user in User.objects.all().iterator():
        UserNewsletterPreference.objects.get_or_create(user_id=user.id, defaults={'newsletter': True})


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_accountdeletionrequest'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserNewsletterPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('newsletter', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='newsletter_preference', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(seed_newsletter_preferences, migrations.RunPython.noop),
    ]