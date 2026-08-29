from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0039_private_course_payment_proofs'),
    ]

    operations = [
        migrations.CreateModel(
            name='SnippeWebhookEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_id', models.CharField(max_length=160, unique=True)),
                ('event_type', models.CharField(blank=True, default='', max_length=100)),
                ('payment_type', models.CharField(blank=True, default='', max_length=50)),
                ('provider_reference', models.CharField(blank=True, default='', max_length=100)),
                ('payload_hash', models.CharField(max_length=64)),
                ('status', models.CharField(choices=[('processing', 'Processing'), ('processed', 'Processed'), ('rejected', 'Rejected'), ('ignored', 'Ignored'), ('failed', 'Failed')], default='processing', max_length=20)),
                ('error', models.TextField(blank=True, default='')),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Snippe Webhook Event',
                'verbose_name_plural': 'Snippe Webhook Events',
                'ordering': ['-received_at'],
            },
        ),
    ]
