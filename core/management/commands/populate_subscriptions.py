from django.core.management.base import BaseCommand
from core.models import Subscription

class Command(BaseCommand):
    help = 'Populate the Subscription model with default data'

    def handle(self, *args, **kwargs):
        Subscription.populate_default_data()
        self.stdout.write(self.style.SUCCESS('Successfully populated Subscription model with default data'))
