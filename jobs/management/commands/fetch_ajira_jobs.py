from django.core.management.base import BaseCommand
import logging
from jobs.api_integration import fetch_jobs_from_api

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetch jobs from Ajira Portal Tanzania'

    def handle(self, *args, **options):
        self.stdout.write('Starting to fetch jobs from Ajira Portal Tanzania...')
        try:
            saved_jobs, created, updated = fetch_jobs_from_api('ajira')
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed {len(saved_jobs)} jobs from Ajira Portal. '
                    f'Created: {created}, Updated: {updated}'
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching jobs from Ajira Portal: {e}'))
            logger.error(f'Error fetching jobs from Ajira Portal: {e}')
