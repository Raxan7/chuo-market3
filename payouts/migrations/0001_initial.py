from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name='PayoutControl', fields=[('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False))]),
        migrations.CreateModel(name='PayoutTransfer', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('payout_request_id', models.PositiveBigIntegerField(db_index=True, unique=True)),
            ('amount_tzs', models.PositiveBigIntegerField()),
            ('channel', models.CharField(max_length=10)),
            ('recipient_encrypted', models.TextField()),
            ('recipient_fingerprint', models.CharField(max_length=64)),
            ('recipient_masked', models.CharField(max_length=220)),
            ('idempotency_key', models.CharField(max_length=30, unique=True)),
            ('status', models.CharField(choices=[(s, s) for s in ('ready','fee_check','sending','unknown','pending','completed','failed','reversed','cancelled')], default='ready', max_length=15)),
            ('authorized_by_id', models.PositiveBigIntegerField()),
            ('authorized_at', models.DateTimeField(auto_now_add=True)),
            ('attempted_at', models.DateTimeField(blank=True, null=True)),
            ('provider_reference', models.CharField(blank=True, max_length=120, null=True, unique=True)),
            ('fee_tzs', models.PositiveBigIntegerField(blank=True, null=True)),
            ('last_error_code', models.CharField(blank=True, default='', max_length=100)),
            ('updated_at', models.DateTimeField(auto_now=True)),
        ], options={'indexes': [models.Index(fields=['status', 'attempted_at'], name='payouts_pay_status_9caf91_idx')]}),
        migrations.CreateModel(name='PayoutAuditEvent', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('action', models.CharField(max_length=70)),
            ('actor_user_id', models.PositiveBigIntegerField(blank=True, null=True)),
            ('reference', models.CharField(blank=True, default='', max_length=120)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('transfer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='events', to='payouts.payouttransfer')),
        ]),
        migrations.CreateModel(name='PayoutWebhookReceipt', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('event_id', models.CharField(max_length=150, unique=True)),
            ('provider_reference', models.CharField(blank=True, default='', max_length=120)),
            ('event_type', models.CharField(max_length=60)),
            ('received_at', models.DateTimeField(auto_now_add=True)),
            ('processed', models.BooleanField(default=False)),
        ]),
    ]
