#!/bin/bash

# Activate the virtual environment
source /home/chuowlwe/virtualenv/repositories/chuo-market3/3.9/bin/activate

# Go to the project directory
cd /home/chuowlwe/repositories/chuo-market3

echo "===== STEP 1: Temporarily disable django_apscheduler in settings.py ====="
# You need to manually comment out django_apscheduler in INSTALLED_APPS
echo "Please manually comment out 'django_apscheduler' in INSTALLED_APPS in settings.py"
echo "Press Enter when done..."
read

echo "===== STEP 2: Fix database charset ====="
# Extract database credentials from environment
DB_NAME=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_NAME'))")
DB_USER=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_USER'))")
DB_PASSWORD=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_PASSWORD'))")
DB_HOST=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_HOST', 'localhost'))")

# Create SQL file to fix character set
cat > fix_charset.sql << EOF
-- Set the database default charset
ALTER DATABASE \`$DB_NAME\` CHARACTER SET utf8 COLLATE utf8_general_ci;

-- For existing tables that might cause issues with index lengths
ALTER TABLE django_apscheduler_djangojob CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;
ALTER TABLE django_apscheduler_djangojoblookup CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;
ALTER TABLE django_apscheduler_djangojobexecution CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;

-- If indexes are causing problems, drop and recreate them with limited length
-- First check if the index exists before trying to drop it
SET @exist := (SELECT COUNT(1) FROM INFORMATION_SCHEMA.STATISTICS WHERE table_schema = DATABASE() AND table_name = 'django_apscheduler_djangojoblookup' AND index_name = 'django_apscheduler_djangojoblookup_job_id_535f354f');
SET @sqlstmt := IF( @exist > 0, 'DROP INDEX django_apscheduler_djangojoblookup_job_id_535f354f ON django_apscheduler_djangojoblookup', 'SELECT ''Index does not exist''');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create indexes with limited length
CREATE INDEX django_apscheduler_djangojoblookup_job_id_535f354f ON django_apscheduler_djangojoblookup (job_id(250));
CREATE INDEX django_apscheduler_djangojoblookup_job_class_string_ea8ffeb8 ON django_apscheduler_djangojoblookup (job_class_string(250));
EOF

# Execute the SQL file
echo "Fixing database character set and indexes..."
mysql -u$DB_USER -p$DB_PASSWORD -h$DB_HOST $DB_NAME < fix_charset.sql 2>/dev/null || echo "Some SQL commands may have failed, but this is often normal if tables don't exist yet."

# Remove SQL file for security
rm fix_charset.sql

echo "===== STEP 3: Mark all django_apscheduler migrations as applied ====="
python - << EOF
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Commerce.settings')
django.setup()

from django.db import connection

# Helper function to mark a migration as applied
def mark_migration_as_applied(app_name, migration_name):
    with connection.cursor() as cursor:
        # Check if the migration has already been applied
        cursor.execute(
            "SELECT * FROM django_migrations WHERE app = %s AND name = %s",
            [app_name, migration_name]
        )
        if cursor.fetchone() is None:
            # Add the migration as if it was already applied
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
                [app_name, migration_name]
            )
            print(f"Successfully marked {app_name} migration {migration_name} as applied.")
        else:
            print(f"Migration {app_name}.{migration_name} is already marked as applied.")

# List of all django_apscheduler migrations
migrations_to_apply = [
    "0001_initial",
    "0002_auto_20180412_0758",
    "0003_auto_20200716_1632",
    "0004_auto_20200717_1043",
    "0005_migrate_name_to_id",
    "0006_remove_djangojob_name",
    "0007_auto_20200717_1404",
    "0008_remove_djangojobexecution_started",
    "0009_djangojobexecution_unique_job_executions"
]

for migration in migrations_to_apply:
    mark_migration_as_applied("django_apscheduler", migration)
EOF

echo "===== STEP 4: Merge conflicting migrations ====="
python manage.py makemigrations --merge --noinput

echo "===== STEP 5: Apply all remaining migrations ====="
python manage.py migrate

echo "===== STEP 6: Verify migrations status ====="
python manage.py showmigrations core
python manage.py showmigrations django_apscheduler

echo "===== STEP 7: Re-enable django_apscheduler ====="
echo "If everything is working correctly, you can uncomment django_apscheduler in INSTALLED_APPS"
echo "in settings.py if you need it. Otherwise, leave it commented out."
