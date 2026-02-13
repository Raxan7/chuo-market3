#!/usr/bin/env python
"""
Script to create and apply migrations for Blog model changes
"""
import os
import sys
import django
from django.conf import settings
from django.core.management import call_command

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Commerce.settings')
django.setup()

print("Creating migrations for core app...")
try:
    call_command('makemigrations', 'core', verbosity=2)
    print("\n✅ Migrations created successfully!")
except Exception as e:
    print(f"❌ Error creating migrations: {e}")
    sys.exit(1)

print("\nApplying migrations...")
try:
    call_command('migrate', 'core', verbosity=2)
    print("\n✅ Migrations applied successfully!")
except Exception as e:
    print(f"❌ Error applying migrations: {e}")
    sys.exit(1)

print("\n✅ Migration process completed!")
