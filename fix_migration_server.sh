#!/bin/bash

# Activate the virtual environment
source /home/chuowlwe/virtualenv/repositories/chuo-market3/3.9/bin/activate

# Go to the project directory
cd /home/chuowlwe/repositories/chuo-market3

# Run the fix to mark the migration as applied
python - << EOF
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Commerce.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Create the table if it doesn't exist (should be rare)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS django_migrations (
        id integer PRIMARY KEY AUTO_INCREMENT,
        app varchar(255) NOT NULL,
        name varchar(255) NOT NULL,
        applied datetime NOT NULL
    );
    """)
    
    # Check if the migration has already been applied
    cursor.execute(
        "SELECT * FROM django_migrations WHERE app = 'django_apscheduler' AND name = '0004_auto_20200717_1043'"
    )
    if cursor.fetchone() is None:
        # Add the migration as if it was already applied
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
            ['django_apscheduler', '0004_auto_20200717_1043']
        )
        print("Successfully marked django_apscheduler migration 0004_auto_20200717_1043 as applied.")
    else:
        print("Migration django_apscheduler.0004_auto_20200717_1043 is already marked as applied.")
EOF

# Verify that the fix worked
echo "Checking if the migration was marked as applied:"
python manage.py showmigrations django_apscheduler

# Run the remaining migrations
echo "Running the remaining migrations:"
python manage.py migrate
