from django.core.management.base import BaseCommand
import os
from pywebpush import webpush, WebPushException
from py_vapid import Vapid

class Command(BaseCommand):
    help = 'Generate VAPID keys for Web Push notifications'

    def handle(self, *args, **options):
        # Generate VAPID keys
        vapid = Vapid()
        vapid.generate_keys()
        
        # Get the keys
        private_key = vapid.private_key.decode('utf-8')
        public_key = vapid.public_key.decode('utf-8')
        
        # Print the keys
        self.stdout.write(self.style.SUCCESS('VAPID keys generated successfully:'))
        self.stdout.write(self.style.SUCCESS(f'VAPID_PUBLIC_KEY = "{public_key}"'))
        self.stdout.write(self.style.SUCCESS(f'VAPID_PRIVATE_KEY = "{private_key}"'))
        self.stdout.write(self.style.SUCCESS('\nAdd these keys to your settings.py file in the WEBPUSH_SETTINGS dictionary.'))
