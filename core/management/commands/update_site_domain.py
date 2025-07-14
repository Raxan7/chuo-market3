"""
Management command to update the site domain in the database.
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings

class Command(BaseCommand):
    help = 'Updates the site domain in the database to match settings.SITE_DOMAIN'

    def handle(self, *args, **options):
        try:
            site_domain = getattr(settings, 'SITE_DOMAIN', 'chuosmart.com')
            site = Site.objects.get(id=settings.SITE_ID)
            
            if site.domain != site_domain:
                old_domain = site.domain
                site.domain = site_domain
                site.name = 'ChuoSmart'
                site.save()
                self.stdout.write(self.style.SUCCESS(f'Successfully updated site domain from "{old_domain}" to "{site_domain}"'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Site domain is already set to "{site_domain}"'))
                
        except Site.DoesNotExist:
            Site.objects.create(id=settings.SITE_ID, domain=site_domain, name='ChuoSmart')
            self.stdout.write(self.style.SUCCESS(f'Created new site with domain "{site_domain}"'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating site domain: {e}'))
