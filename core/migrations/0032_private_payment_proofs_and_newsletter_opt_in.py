import core.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_newslettertestsend_newslettersendlog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptionpayment',
            name='payment_proof',
            field=models.ImageField(storage=core.storage.private_payment_storage, upload_to='payment_proofs/'),
        ),
        migrations.AlterField(
            model_name='usernewsletterpreference',
            name='newsletter',
            field=models.BooleanField(default=False),
        ),
    ]
