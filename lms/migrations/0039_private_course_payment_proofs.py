import core.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0038_alter_sitesettings_show_list_ads'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseenrollment',
            name='payment_proof',
            field=models.ImageField(
                blank=True,
                help_text='Upload proof of payment for premium courses',
                null=True,
                storage=core.storage.private_payment_storage,
                upload_to='lms/payment_proofs/',
            ),
        ),
    ]
