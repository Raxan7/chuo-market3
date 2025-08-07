from django.core.management.base import BaseCommand
from jobs.api_integration import fetch_all_jobs
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch jobs from all configured APIs'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting job fetch from APIs...'))
        
        try:
            saved_jobs, created, updated = fetch_all_jobs()
            
            self.stdout.write(self.style.SUCCESS(
                f'Completed job fetch. Total jobs: {len(saved_jobs)}, '
                f'Created: {created}, Updated: {updated}'
            ))
        except Exception as e:
            logger.error(f"Error fetching jobs: {e}")
            self.stdout.write(self.style.ERROR(f'Error fetching jobs: {e}'))
