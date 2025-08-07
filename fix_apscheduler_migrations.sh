#!/bin/bash

# Activate the virtual environment
source /home/chuowlwe/virtualenv/repositories/chuo-market3/3.9/bin/activate

# Go to the project directory
cd /home/chuowlwe/repositories/chuo-market3

# Apply the remaining django_apscheduler migrations one by one
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

# Let's mark all remaining django_apscheduler migrations as applied
migrations_to_apply = [
    "0005_migrate_name_to_id",
    "0006_remove_djangojob_name",
    "0007_auto_20200717_1404",
    "0008_remove_djangojobexecution_started",
    "0009_djangojobexecution_unique_job_executions"
]

for migration in migrations_to_apply:
    mark_migration_as_applied("django_apscheduler", migration)
EOF

# Show the migration status for django_apscheduler
echo "Checking django_apscheduler migrations status:"
python manage.py showmigrations django_apscheduler

# Run the merge migration
echo "Running migration merge..."
python manage.py makemigrations --merge --noinput

# Apply all remaining migrations
echo "Applying all migrations..."
python manage.py migrate
