from django.db import migrations, models

# This is a custom migration to fix the "Specified key was too long" error with django_apscheduler
# It modifies the indexes on the JobLookup table to use a shorter max_length

class Migration(migrations.Migration):
    dependencies = [
        ('django_apscheduler', '0003_auto_20200716_1632'),
    ]

    operations = [
        # Remove the problematic migration by replacing django_apscheduler.0004_auto_20200717_1043
        migrations.RunSQL(
            sql="""
            -- First, ensure that the JobLookup table exists
            CREATE TABLE IF NOT EXISTS `django_apscheduler_djangojoblookup` (
                `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
                `job_id` varchar(255) NOT NULL,
                `job_class_string` varchar(255) NOT NULL,
                `next_run_time` datetime(6) NULL
            );
            
            -- Add indexes with limited length for MySQL compatibility
            CREATE INDEX IF NOT EXISTS `django_apscheduler_djangojoblookup_job_id_535f354f` 
            ON `django_apscheduler_djangojoblookup` (`job_id`(250));
            
            CREATE INDEX IF NOT EXISTS `django_apscheduler_djangojoblookup_job_class_string_ea8ffeb8` 
            ON `django_apscheduler_djangojoblookup` (`job_class_string`(250));
            """,
            reverse_sql="DROP TABLE IF EXISTS `django_apscheduler_djangojoblookup`;"
        ),
    ]
