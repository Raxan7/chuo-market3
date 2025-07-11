import logging
from django.core.management.base import BaseCommand
from core.models import Blog

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up all blog content and apply formatting fixes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(self.style.NOTICE("Starting blog content cleanup..."))
        
        blogs = Blog.objects.all()
        count = 0
        
        for blog in blogs:
            original_content = blog.content
            
            # Apply the clean_html_content method
            cleaned_content = blog.clean_html_content()
            
            if cleaned_content != original_content:
                count += 1
                if not dry_run:
                    blog.content = cleaned_content
                    blog.save(update_fields=['content'])
                    self.stdout.write(f"Cleaned blog: {blog.title} (ID: {blog.id})")
                else:
                    self.stdout.write(f"Would clean blog: {blog.title} (ID: {blog.id})")
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Found {count} blogs that need cleaning (dry run, no changes made)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully cleaned {count} blogs"))
