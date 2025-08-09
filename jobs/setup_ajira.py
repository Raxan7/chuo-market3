#!/usr/bin/env python
"""
Setup script for Ajira Portal integration
This script creates an API configuration for the Ajira Portal in the database.
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Commerce.settings')
django.setup()

from jobs.models import ApiConfiguration

def setup_ajira_config():
    """Create or update the Ajira Portal API configuration"""
    # Check if configuration already exists
    try:
        config = ApiConfiguration.objects.get(name='ajira')
        print("Ajira Portal API configuration already exists.")
        
        # Make sure it's active
        if not config.is_active:
            config.is_active = True
            config.save()
            print("Activated the existing Ajira Portal API configuration.")
            
        return config
    except ApiConfiguration.DoesNotExist:
        # Create new configuration
        config = ApiConfiguration.objects.create(
            name='ajira',
            api_key='ajira-portal-key',  # Placeholder value
            api_secret='',
            additional_params={},
            is_active=True
        )
        print("Created new Ajira Portal API configuration.")
        return config

if __name__ == "__main__":
    print("Setting up Ajira Portal integration...")
    setup_ajira_config()
    print("Setup complete! You can now run 'python manage.py fetch_ajira_jobs' to test the integration.")
