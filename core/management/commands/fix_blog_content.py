"""
Management command to fix blog content with problematic formatting.
"""
from django.core.management.base import BaseCommand
from core.models import Blog
from core.views import deep_clean_html_content
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fixes blog content with problematic formatting, removing unwanted data attributes and correcting braced content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Run without making any changes to the database',
        )
        parser.add_argument(
            '--blog-id',
            dest='blog_id',
            type=int,
            help='Fix a specific blog by ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        blog_id = options.get('blog_id')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in dry-run mode - no changes will be saved'))
        
        # Query the blogs to process
        if blog_id:
            blogs = Blog.objects.filter(pk=blog_id)
            if not blogs.exists():
                self.stderr.write(self.style.ERROR(f'Blog with ID {blog_id} not found'))
                return
        else:
            # Only process non-markdown blogs
            blogs = Blog.objects.filter(is_markdown=False)
        
        self.stdout.write(f'Found {blogs.count()} blogs to process')
        
        fixed_count = 0
        for blog in blogs:
            original_content = blog.content
            self.stdout.write(f'Processing blog: {blog.id} - {blog.title}')
            
            # Apply direct brace removal if content starts with { and contains HTML
            if original_content.startswith('{') and ('<' in original_content) and original_content.endswith('}'):
                self.stdout.write(self.style.WARNING(f'Blog {blog.id}: Found content wrapped in braces, will remove them'))
                # Simply remove the outer braces
                cleaned_content = original_content[1:-1].strip()
                
                # If we already fixed the issue by removing braces, we can skip further cleaning
                content_changed = True
            else:
                # Apply the normal cleaning function
                cleaned_content = deep_clean_html_content(original_content)
                content_changed = cleaned_content != original_content
            
            # Check if we made any changes
            if content_changed:
                if dry_run:
                    self.stdout.write(self.style.SUCCESS(f'Blog {blog.id}: Would fix (dry run)'))
                    self.stdout.write(f'Original starts with: {original_content[:100]}...')
                    self.stdout.write(f'Cleaned starts with: {cleaned_content[:100]}...')
                else:
                    blog.content = cleaned_content
                    blog.save(update_fields=['content'])
                    self.stdout.write(self.style.SUCCESS(f'Blog {blog.id}: Fixed and saved'))
                fixed_count += 1
            else:
                self.stdout.write(f'Blog {blog.id}: No changes needed')
        
        self.stdout.write(self.style.SUCCESS(f'Processed {blogs.count()} blogs, fixed {fixed_count}'))
