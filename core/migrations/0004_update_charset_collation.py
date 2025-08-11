from django.db import migrations

class Migration(migrations.Migration):
    """
    This is a replacement migration for charset/collation settings
    that maintains the migration history chain
    """
    
    dependencies = [
        ('core', '0003_fix_apscheduler_key_length'),
    ]

    operations = [
        # No-op operation
        migrations.RunSQL(
            sql="SELECT 1;",
            reverse_sql="SELECT 1;"
        ),
    ]
