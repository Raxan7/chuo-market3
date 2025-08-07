#!/bin/bash

# This script fixes the django-apscheduler migration issue
# by marking the problematic migration as already applied

# Activate the virtual environment if needed
# source /path/to/your/virtualenv/bin/activate

# Set the Django settings module
export DJANGO_SETTINGS_MODULE=Commerce.settings

# Run the fix migration script
python -c "
import django
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    # Check if the migration has already been applied
    cursor.execute(
        \"SELECT * FROM django_migrations WHERE app = 'django_apscheduler' AND name = '0004_auto_20200717_1043'\"
    )
    if cursor.fetchone() is None:
        # Add the migration as if it was already applied
        cursor.execute(
            \"INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())\",
            ['django_apscheduler', '0004_auto_20200717_1043']
        )
        print(\"Successfully marked django_apscheduler migration 0004_auto_20200717_1043 as applied.\")
    else:
        print(\"Migration django_apscheduler.0004_auto_20200717_1043 is already marked as applied.\")
"

# Run additional migrations
python manage.py migrate
