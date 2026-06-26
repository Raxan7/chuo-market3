from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0030_certificate_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='certificatepayment',
            name='webhook_event_id',
            field=models.CharField(blank=True, default='', help_text='Snippe webhook event ID (idempotency key)', max_length=100),
        ),
        migrations.AddField(
            model_name='certificatepayment',
            name='failure_reason',
            field=models.TextField(blank=True, default='', help_text="Failure reason from Snippe (e.g. 'Payment expired.')"),
        ),
    ]
