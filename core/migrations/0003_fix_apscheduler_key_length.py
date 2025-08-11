from django.db import migrations, models

# This is a replacement migration for the removed apscheduler functionality
# It preserves the migration history chain

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_blog'),
    ]

    operations = [
        # No-op operation
        migrations.RunSQL(
            sql="SELECT 1;",
            reverse_sql="SELECT 1;"
        ),
    ]
