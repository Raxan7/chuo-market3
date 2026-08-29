from django.db import migrations, models
import django.utils.timezone
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0032_private_payment_proofs_and_newsletter_opt_in'),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsletterJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_type', models.CharField(choices=[('blog', 'Blog'), ('product', 'Product'), ('course', 'Course'), ('course_content', 'Course content'), ('job', 'Job'), ('material', 'Material')], max_length=30)),
                ('object_id', models.PositiveBigIntegerField()),
                ('related_ids', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('sent', 'Sent'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('max_attempts', models.PositiveSmallIntegerField(default=3)),
                ('run_after', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_error', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={'ordering': ('created_at',)},
        ),
        migrations.AddConstraint(
            model_name='newsletterjob',
            constraint=models.UniqueConstraint(fields=('job_type', 'object_id'), name='unique_newsletter_job_per_object'),
        ),
        migrations.CreateModel(
            name='NewsletterDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_email', models.EmailField(max_length=254)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('last_error', models.TextField(blank=True, default='')),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('job', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='core.newsletterjob')),
            ],
        ),
        migrations.AddConstraint(
            model_name='newsletterdelivery',
            constraint=models.UniqueConstraint(fields=('job', 'recipient_email'), name='unique_newsletter_job_recipient'),
        ),
    ]
