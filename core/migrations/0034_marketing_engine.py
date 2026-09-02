from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0033_newsletterjob'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketingCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Internal campaign name.', max_length=180)),
                ('kind', models.CharField(choices=[('announcement', 'Announcement'), ('product', 'Product'), ('service', 'Service'), ('course', 'Course'), ('career', 'Career / jobs'), ('promotion', 'Promotion'), ('reengagement', 'Re-engagement')], default='announcement', max_length=20)),
                ('audience', models.CharField(choices=[('all_opted_in', 'All opted-in contacts'), ('registered_users', 'Registered users who opted in'), ('website_subscribers', 'Website newsletter subscribers')], default='all_opted_in', max_length=30)),
                ('subject', models.CharField(max_length=255)),
                ('preheader', models.CharField(blank=True, default='', max_length=255)),
                ('headline', models.CharField(max_length=255)),
                ('body', models.TextField(help_text='Main marketing message. Plain text is rendered safely with paragraphs.')),
                ('hero_image_url', models.URLField(blank=True, default='', help_text='Optional HTTPS image URL for the campaign hero.')),
                ('cta_text', models.CharField(blank=True, default='', max_length=80)),
                ('cta_url', models.URLField(blank=True, default='')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('scheduled', 'Scheduled'), ('queued', 'Queued'), ('sending', 'Sending'), ('paused', 'Paused'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('scheduled_for', models.DateTimeField(blank=True, null=True)),
                ('minimum_gap_hours', models.PositiveSmallIntegerField(default=24, help_text='Frequency cap. Set 0 only for genuinely urgent campaigns.')),
                ('max_attempts', models.PositiveSmallIntegerField(default=5)),
                ('total_recipients', models.PositiveIntegerField(default=0)),
                ('sent_count', models.PositiveIntegerField(default=0)),
                ('failed_count', models.PositiveIntegerField(default=0)),
                ('skipped_count', models.PositiveIntegerField(default=0)),
                ('last_test_sent_at', models.DateTimeField(blank=True, null=True)),
                ('prepared_at', models.DateTimeField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marketing_campaigns_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='MarketingSuppression',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('reason', models.CharField(choices=[('unsubscribed', 'Unsubscribed'), ('bounce', 'Hard bounce'), ('complaint', 'Spam complaint'), ('manual', 'Manual suppression')], default='unsubscribed', max_length=20)),
                ('source', models.CharField(blank=True, default='', max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ('email',)},
        ),
        migrations.CreateModel(
            name='MarketingDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_email', models.EmailField(max_length=254)),
                ('recipient_name', models.CharField(blank=True, default='', max_length=180)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sending', 'Sending'), ('sent', 'Sent'), ('failed', 'Failed'), ('skipped', 'Skipped'), ('suppressed', 'Suppressed')], default='pending', max_length=20)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('max_attempts', models.PositiveSmallIntegerField(default=5)),
                ('run_after', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_error', models.TextField(blank=True, default='')),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='core.marketingcampaign')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='marketing_deliveries', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('created_at',)},
        ),
        migrations.AddConstraint(
            model_name='marketingdelivery',
            constraint=models.UniqueConstraint(fields=('campaign', 'recipient_email'), name='unique_marketing_campaign_recipient'),
        ),
        migrations.AddIndex(
            model_name='marketingdelivery',
            index=models.Index(fields=['status', 'run_after'], name='marketing_queue_idx'),
        ),
        migrations.AddIndex(
            model_name='marketingdelivery',
            index=models.Index(fields=['recipient_email', 'sent_at'], name='marketing_email_sent_idx'),
        ),
    ]
