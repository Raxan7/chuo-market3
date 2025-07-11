#!/usr/bin/env python

"""
Script to populate slug fields for existing Blog entries
Run this script after applying migrations that added the slug field
"""

import os
import sys
import django

# Set up Django environment
# Get the absolute path of the script's directory and add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up two levels: from core/scripts to the project root
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Commerce.settings')
django.setup()

# Now import models
from core.models import Blog
from django.utils.text import slugify

def populate_slugs():
    blogs = Blog.objects.filter(slug__isnull=True)
    print(f"Found {blogs.count()} blogs with empty slugs")
    
    for blog in blogs:
        # Create base slug from title
        base_slug = slugify(blog.title)
        
        # Make sure slug is unique
        slug = base_slug
        counter = 1
        while Blog.objects.filter(slug=slug).exclude(id=blog.id).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Update the slug
        blog.slug = slug
        blog.save(update_fields=['slug'])
        print(f"Updated blog {blog.id}: '{blog.title}' with slug '{slug}'")

if __name__ == "__main__":
    print("Starting slug population for Blog model...")
    populate_slugs()
    print("Finished populating slugs!")
