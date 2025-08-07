from django.db import migrations

class Migration(migrations.Migration):
    """
    This migration sets the correct character set and collation for all tables
    to prevent "Specified key was too long" errors.
    """
    
    dependencies = [
        ('core', '0003_fix_apscheduler_key_length'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER DATABASE CHARACTER SET utf8 COLLATE utf8_general_ci;
            """,
            reverse_sql="""
            -- No reverse SQL needed
            """
        ),
    ]
