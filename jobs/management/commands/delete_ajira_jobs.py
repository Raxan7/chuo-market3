from django.core.management.base import BaseCommand
from jobs.models import Job

class Command(BaseCommand):
    help = 'Delete all jobs fetched from Ajira Portal Tanzania (source = "ajira")'

    def handle(self, *args, **options):
        ajira_jobs = Job.objects.filter(source='ajira')
        count = ajira_jobs.count()
        if count == 0:
            self.stdout.write(self.style.WARNING('No jobs found with source = "ajira".'))
            return
        ajira_jobs.delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} jobs from Ajira Portal.'))
