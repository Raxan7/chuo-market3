import logging
from django.core.management.base import BaseCommand
from django.utils.html import strip_tags
from core.models import Blog
import re
import html
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Comprehensive fix for blog posts with problematic HTML content that is displayed as text'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only identify problematic blogs without fixing them',
        )
        parser.add_argument(
            '--slug',
            type=str,
            help='Fix only a specific blog by slug',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all blogs, not just problematic ones',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create backups of blog content before making changes',
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Generate a detailed report of all changes',
        )
        parser.add_argument(
            '--recreate',
            action='store_true',
            help='Recreate blogs instead of fixing them (preserves images and metadata)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        specific_slug = options.get('slug')
        process_all = options.get('all', False)
        verbose = options.get('verbose', False)
        backup = options.get('backup', False)
        generate_report = options.get('report', False)
        recreate_blogs = options.get('recreate', False)
        
        # Prepare backup directory if needed
        backup_dir = None
        if backup:
            backup_dir = self._prepare_backup_dir()
            self.stdout.write(self.style.SUCCESS(f"Backup directory created: {backup_dir}"))
        
        # Initialize report data
        report_data = []
        
        if specific_slug:
            self.stdout.write(self.style.NOTICE(f"Processing only blog with slug: {specific_slug}"))
            blogs = Blog.objects.filter(slug=specific_slug)
        else:
            self.stdout.write(self.style.NOTICE("Scanning all blogs..."))
            blogs = Blog.objects.all()
        
        fixed_count = 0
        problematic_count = 0
        
        for blog in blogs:
            is_problematic = False
            
            # Skip blogs without content
            if not blog.content:
                if verbose:
                    self.stdout.write(f"Skipping blog {blog.id} - No content")
                continue
                
            # Check if blog content has problematic HTML display
            if self.is_problematic_content(blog.content) or process_all:
                problematic_count += 1
                
                if verbose:
                    self.stdout.write(self.style.WARNING(f"Found problematic blog: ID={blog.id}, Title={blog.title}, Slug={blog.slug}"))
                    self.stdout.write(f"Content preview: {blog.content[:100]}...")
                
                # Create backup if requested
                if backup:
                    self._backup_blog(blog, backup_dir)
                    if verbose:
                        self.stdout.write(f"Created backup for blog {blog.id}")
                
                # Skip fixing if dry run
                if dry_run:
                    # Add to report
                    if generate_report:
                        report_data.append({
                            'id': blog.id,
                            'title': blog.title,
                            'slug': blog.slug,
                            'problematic': True,
                            'fixed': False,
                            'action': 'identified',
                            'content_preview': blog.content[:100]
                        })
                    continue
                
                # If recreating blogs, use a more aggressive approach
                if recreate_blogs:
                    self._recreate_blog_content(blog, verbose)
                    fixed_count += 1
                    
                    if generate_report:
                        report_data.append({
                            'id': blog.id,
                            'title': blog.title,
                            'slug': blog.slug,
                            'problematic': True,
                            'fixed': True,
                            'action': 'recreated',
                            'content_preview': blog.content[:100]
                        })
                else:
                    # Fix the content
                    fixed_content = self.fix_content(blog.content)
                    
                    # Don't update if nothing changed
                    if fixed_content == blog.content:
                        if verbose:
                            self.stdout.write(self.style.WARNING(f"No changes needed for blog {blog.id}"))
                        
                        if generate_report:
                            report_data.append({
                                'id': blog.id,
                                'title': blog.title,
                                'slug': blog.slug,
                                'problematic': True,
                                'fixed': False,
                                'action': 'no_changes',
                                'content_preview': blog.content[:100]
                            })
                        continue
                    
                    # Store the original content for reference
                    blog.original_content = blog.content
                    
                    # Update the blog with fixed content
                    blog.content = fixed_content
                    blog.save(update_fields=['content'])
                    fixed_count += 1
                    
                    if generate_report:
                        report_data.append({
                            'id': blog.id,
                            'title': blog.title,
                            'slug': blog.slug,
                            'problematic': True,
                            'fixed': True,
                            'action': 'fixed',
                            'content_preview': fixed_content[:100]
                        })
                    
                    if verbose:
                        self.stdout.write(self.style.SUCCESS(f"Fixed blog {blog.id}"))
        
        # Generate report if requested
        if generate_report:
            report_file = self._generate_report(report_data)
            self.stdout.write(self.style.SUCCESS(f"Report generated at: {report_file}"))
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Found {problematic_count} problematic blogs (dry run, no changes made)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Fixed {fixed_count} out of {problematic_count} problematic blogs"))
    
    def is_problematic_content(self, content):
        """Identify if content has problematic HTML display issues"""
        # Check for braces wrapping HTML tags
        if content.startswith('{') and '<' in content[:100]:
            return True
        
        # Check for data attributes being visible
        if 'data-start=' in content or 'data-end=' in content:
            return True
            
        # Check for HTML tags as text
        if re.search(r'&lt;(p|div|blockquote|h[1-6])[\s\S]*?&gt;', content):
            return True
            
        # Check for specific problematic pattern seen in the example
        if '<blockquote data-start=' in content or '<p data-start=' in content:
            return True
        
        # Check for multiple occurrences of HTML tags
        if content.count('<p>') > 5 and content.count('<p') > content.count('</p>'):
            return True
            
        # Check for TinyMCE specific patterns that indicate corruption
        if '_mce_' in content or 'tinymce' in content.lower():
            return True
            
        return False
    
    def fix_content(self, content):
        """Fix problematic HTML content with multiple aggressive cleaning strategies"""
        import re
        import html
        
        # Strategy 1: Handle content wrapped in braces
        if content.startswith('{') and content.endswith('}'):
            content = content[1:-1].strip()
        
        # Strategy 2: Remove all data attributes
        content = re.sub(r'\s+data-[a-zA-Z0-9_-]+=["\'][^"\']*["\']', '', content)
        
        # Strategy 3: Remove problematic class attributes
        class_patterns = [
            r'\s+class=["\']_[^"\']*["\']',
            r'\s+class=["\'](?:_tableContainer_[^"\']*|_tableWrapper_[^"\']*|group\s+flex\s+w-fit\s+flex-col-reverse)["\']',
            r'\s+class=["\'][^"\']*flex[^"\']*["\']',
            r'\s+class=["\'][^"\']*mce[^"\']*["\']'
        ]
        
        for pattern in class_patterns:
            content = re.sub(pattern, '', content)
        
        # Strategy 4: Remove other problematic attributes
        other_attr_patterns = [
            r'\s+tabindex=["\'][^"\']*["\']',
            r'\s+data-col-size=["\'][^"\']*["\']',
            r'\s+data-mce-[a-zA-Z0-9_-]+=["\'][^"\']*["\']',
            r'\s+id=["\']_[^"\']*["\']'
        ]
        
        for pattern in other_attr_patterns:
            content = re.sub(pattern, '', content)
        
        # Strategy 5: Extract just the HTML elements for extreme cases
        if '<blockquote data-start=' in content or '<p data-start=' in content:
            html_pattern = r'(<(?:blockquote|p|div|h[1-6]|ul|ol|li|table|tr|td|th)[\s\S]*?</(?:blockquote|p|div|h[1-6]|ul|ol|li|table|tr|td|th)>)'
            html_matches = re.findall(html_pattern, content)
            
            if html_matches:
                # Join the extracted HTML elements
                content = ''.join(html_matches)
        
        # Strategy 6: Unescape HTML entities
        content = html.unescape(content)
        
        # Strategy 7: Fix nested tags that might have been broken
        content = re.sub(r'(<[^>]+>)\s*\1', r'\1', content)  # Remove doubled opening tags
        content = re.sub(r'(</[^>]+>)\s*\1', r'\1', content)  # Remove doubled closing tags
        
        # Strategy 8: Handle JSON-like escaped content
        if r'\\"' in content:
            content = content.replace(r'\\"', '"')
        if r'\\"' in content:
            content = content.replace(r'\\"', '"')
            
        # Strategy 9: Try to fix malformed tags
        content = re.sub(r'<([a-zA-Z0-9]+)([^>]*?)><\1>', r'<\1\2>', content)
        
        # Strategy 10: Fix image tags to ensure they're valid
        content = re.sub(r'<img([^>]*)>', r'<img\1 />', content)
        
        # Strategy 11: Special braces cleanup - remove outer braces enclosing HTML content
        braces_pattern = r'^\{(.*)\}$'
        braces_match = re.match(braces_pattern, content, re.DOTALL)
        if braces_match:
            inner_content = braces_match.group(1)
            if inner_content.strip().startswith('<') and inner_content.strip().endswith('>'):
                content = inner_content
        
        return content
    
    def _prepare_backup_dir(self):
        """Create a backup directory for blog content"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"blog_backups_{timestamp}"
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        return backup_dir
    
    def _backup_blog(self, blog, backup_dir):
        """Create a backup of a blog's content"""
        blog_data = {
            'id': blog.id,
            'title': blog.title,
            'content': blog.content,
            'slug': blog.slug,
            'created_at': blog.created_at.isoformat() if blog.created_at else None,
            'updated_at': blog.updated_at.isoformat() if hasattr(blog, 'updated_at') and blog.updated_at else None,
            'backup_time': datetime.now().isoformat()
        }
        
        # Save to backup file
        with open(os.path.join(backup_dir, f"blog_{blog.id}_{blog.slug}.json"), 'w') as f:
            json.dump(blog_data, f, indent=2)
    
    def _generate_report(self, report_data):
        """Generate a report of all changes made"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"blog_fix_report_{timestamp}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_blogs_processed': len(report_data),
            'problematic_blogs': sum(1 for item in report_data if item['problematic']),
            'fixed_blogs': sum(1 for item in report_data if item.get('fixed', False)),
            'details': report_data
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_file
    
    def _recreate_blog_content(self, blog, verbose=False):
        """
        Recreate blog content from scratch, preserving only essential HTML elements
        and ensuring all formatting is consistent.
        """
        content = blog.content
        
        # First try to extract all valid HTML blocks
        html_pattern = r'<(?:p|div|h[1-6]|ul|ol|li|blockquote|table|tr|td|th|img|a|strong|em|span|br)[^>]*>[\s\S]*?</(?:p|div|h[1-6]|ul|ol|li|blockquote|table|tr|td|th|a|strong|em|span)>|<(?:img|br)[^>]*/?>'
        
        html_blocks = re.findall(html_pattern, content)
        
        # If we found valid HTML blocks, use them
        if html_blocks:
            if verbose:
                self.stdout.write(f"Found {len(html_blocks)} valid HTML blocks to preserve")
            
            # Clean each block
            cleaned_blocks = []
            for block in html_blocks:
                # Remove problematic attributes
                clean_block = re.sub(r'\s+(?:data-[a-zA-Z0-9_-]+|class|style|id|tabindex|contenteditable)=["\'][^"\']*["\']', '', block)
                cleaned_blocks.append(clean_block)
            
            # Join the blocks back together
            new_content = ''.join(cleaned_blocks)
            
            # Make sure image tags are preserved
            if 'img src=' in content and not 'img src=' in new_content:
                # Extract and preserve image tags
                img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*/?>'
                img_tags = re.findall(img_pattern, content)
                
                for img_src in img_tags:
                    new_content += f'<p><img src="{img_src}" alt="Blog image" /></p>'
            
            # Update the blog with the recreated content
            blog.content = new_content
            blog.save(update_fields=['content'])
            
            return True
        else:
            # If no valid blocks found, use more aggressive approach
            # Remove all potential JSON or script-like wrappers
            if content.startswith('{'):
                content = content[1:].strip()
            if content.endswith('}'):
                content = content[:-1].strip()
            
            # Unescape any HTML entities
            content = html.unescape(content)
            
            # Try to extract paragraphs of text
            paragraphs = re.split(r'\n\s*\n|\r\n\s*\r\n', content)
            new_content = ''.join([f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()])
            
            # Preserve image tags if present
            img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*/?>'
            img_tags = re.findall(img_pattern, content)
            
            for img_src in img_tags:
                new_content += f'<p><img src="{img_src}" alt="Blog image" /></p>'
            
            # Update the blog with the recreated content
            blog.content = new_content
            blog.save(update_fields=['content'])
            
            if verbose:
                self.stdout.write(self.style.WARNING(f"Used aggressive recreation for blog {blog.id}"))
            
            return True
