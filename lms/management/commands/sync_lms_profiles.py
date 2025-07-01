"""
Management command to sync LMS profiles for all users
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from lms.models import LMSProfile

class Command(BaseCommand):
    help = 'Creates LMS profiles for all users who do not have one'

    def handle(self, *args, **kwargs):
        users_without_profiles = []
        users = User.objects.all()
        
        self.stdout.write(f"Found {users.count()} users in the system")
        
        for user in users:
            if not hasattr(user, 'lms_profile'):
                users_without_profiles.append(user)
        
        self.stdout.write(f"Found {len(users_without_profiles)} users without LMS profiles")
        
        for user in users_without_profiles:
            # Determine the appropriate role
            role = 'student'
            if user.is_staff and user.is_superuser:
                role = 'admin'
            elif user.is_staff:
                role = 'instructor'
                
            # Create the profile
            LMSProfile.objects.create(user=user, role=role)
            self.stdout.write(f"Created {role} profile for user {user.username}")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created {len(users_without_profiles)} LMS profiles"))
