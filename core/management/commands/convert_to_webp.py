"""
Management command to convert existing images to WebP format.
Handles both product images and blog thumbnails.

Features:
- Convert product images to WebP format
- Convert blog thumbnails to WebP format
- Scan for missing image files
- Report detailed conversion statistics
- Fix database references for missing files (with --sync option)
"""
import traceback
import sys
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Q
from core.models import Product, Blog
from core.image_utils import optimize_image

class Command(BaseCommand):
    help = 'Convert existing images to WebP format and manage image consistency'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['products', 'blogs', 'all'],
            default='all',
            help='Specify which type of images to convert: products, blogs, or all'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force conversion even if WebP versions already exist'
        )
        
        parser.add_argument(
            '--scan-only',
            action='store_true',
            help='Only scan for issues without making changes'
        )
        
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Update database when files are missing (clears missing file references)'
        )
        
        parser.add_argument(
            '--quality',
            type=int,
            default=85,
            help='WebP quality level (1-100, default: 85)'
        )

    def handle(self, *args, **options):
        image_type = options['type']
        force = options['force']
        scan_only = options['scan_only']
        sync = options['sync']
        quality = options['quality']
        
        # Initialize counters for statistics
        total_success = 0
        total_errors = 0
        total_missing = 0
        total_synced = 0
        
        operation_mode = "Scanning" if scan_only else "Converting"
        self.stdout.write(self.style.NOTICE(f'Starting {operation_mode} images with the following options:'))
        self.stdout.write(f'  - Type: {image_type}')
        self.stdout.write(f'  - Force: {force}')
        self.stdout.write(f'  - Scan only: {scan_only}')
        self.stdout.write(f'  - Sync DB: {sync}')
        self.stdout.write(f'  - WebP quality: {quality}')
        
        # Process product images
        if image_type in ['products', 'all']:
            product_success, product_errors, product_missing, product_synced = self.convert_product_images(
                force=force, 
                scan_only=scan_only, 
                sync=sync, 
                quality=quality
            )
            total_success += product_success
            total_errors += product_errors
            total_missing += product_missing
            total_synced += product_synced
        
        # Process blog thumbnails
        if image_type in ['blogs', 'all']:
            blog_success, blog_errors, blog_missing, blog_synced = self.convert_blog_thumbnails(
                force=force, 
                scan_only=scan_only, 
                sync=sync, 
                quality=quality
            )
            total_success += blog_success
            total_errors += blog_errors
            total_missing += blog_missing
            total_synced += blog_synced
            
        # Output overall summary
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write(self.style.SUCCESS(f'OVERALL SUMMARY:'))
        
        if scan_only:
            self.stdout.write(self.style.SUCCESS(
                f'Scan completed: {total_success} images valid, {total_missing} missing, {total_errors} errors'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Conversion completed: {total_success} images successfully converted, {total_errors} failed'
            ))
            
        if sync:
            self.stdout.write(self.style.SUCCESS(f'Database sync: {total_synced} references updated'))
            
    def convert_product_images(self, force=False, scan_only=False, sync=False, quality=85, success_count=0, error_count=0):
        operation = "Scanning" if scan_only else "Converting"
        self.stdout.write(self.style.MIGRATE_HEADING(f'Starting {operation} of product images...'))
        
        # Initialize counters
        missing_count = 0
        synced_count = 0
        
        # Build query based on force parameter
        query = Product.objects.filter(image__isnull=False)
        if not force and not scan_only:
            query = query.filter(image_webp__isnull=True)
            
        products = query
        self.stdout.write(f'Found {products.count()} products to process')
        
        if products.count() == 0:
            self.stdout.write(self.style.WARNING(f'No products found with images that need {operation.lower()}'))
            return success_count, error_count, missing_count, synced_count
        
        # Process all products with images
        for i, product in enumerate(products):
            self.stdout.write(f'Processing product {i+1}/{products.count()}: ID={product.id} - {product.title[:30]}...')
            
            try:
                # Check if image exists
                if not product.image:
                    self.stdout.write(self.style.WARNING(f"Product {product.id} has no image field"))
                    continue
                    
                # Check if image file exists
                file_exists = True
                image_path = ""
                try:
                    image_path = product.image.path
                    if not os.path.exists(image_path):
                        file_exists = False
                        missing_count += 1
                        self.stdout.write(self.style.ERROR(f"✗ Image file does not exist at path: {image_path}"))
                    else:
                        self.stdout.write(f"Image path: {image_path}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Cannot access image path for product {product.id}: {e}"))
                    file_exists = False
                    missing_count += 1
                
                # Handle missing file case
                if not file_exists:
                    if sync:
                        # Clear the image reference in database
                        self.stdout.write(self.style.WARNING(f"Syncing database: clearing image reference for product {product.id}"))
                        product.image = None
                        if product.image_webp:
                            product.image_webp = None
                        product.save()
                        synced_count += 1
                    continue
                
                # If scan only, mark as success and continue
                if scan_only:
                    self.stdout.write(self.style.SUCCESS(f"✓ Image for product {product.id} exists and is valid"))
                    success_count += 1
                    continue
                
                # Create WebP version if not in scan-only mode
                self.stdout.write(f"Converting image for product {product.id}...")
                optimized = optimize_image(product.image, quality=quality, format="WEBP")
                
                if optimized:
                    self.stdout.write(f"Optimized image created, saving to WebP...")
                    webp_name = f"{product.id}_webp.webp"
                    product.image_webp.save(
                        webp_name,
                        optimized,
                        save=True
                    )
                    self.stdout.write(self.style.SUCCESS(f"✓ Converted product {product.id} image to WebP as {webp_name}"))
                    success_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Optimizer returned None for product {product.id}"))
                    error_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error processing product {product.id} image: {e}"))
                self.stdout.write(traceback.format_exc())
                error_count += 1
        
        # Output summary for this section
        if scan_only:
            self.stdout.write(self.style.SUCCESS(
                f'Product scan completed: {success_count} valid, {missing_count} missing, {error_count} errors'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Product conversion completed: {success_count} successful, {error_count} failed'
            ))
            
        if sync and synced_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Database sync: {synced_count} product references updated'))
        
        return success_count, error_count, missing_count, synced_count
        
    def convert_blog_thumbnails(self, force=False, scan_only=False, sync=False, quality=85, success_count=0, error_count=0):
        operation = "Scanning" if scan_only else "Converting"
        self.stdout.write(self.style.MIGRATE_HEADING(f'Starting {operation} of blog thumbnails...'))
        
        # Initialize counters
        missing_count = 0
        synced_count = 0
        
        # Build query based on force parameter
        query = Blog.objects.filter(thumbnail__isnull=False)
        if not force and not scan_only:
            query = query.filter(thumbnail_webp__isnull=True)
            
        blogs = query
        self.stdout.write(f'Found {blogs.count()} blog thumbnails to process')
        
        if blogs.count() == 0:
            self.stdout.write(self.style.WARNING(f'No blogs found with thumbnails that need {operation.lower()}'))
            return success_count, error_count, missing_count, synced_count
        
        # Process all blogs with thumbnails
        for i, blog in enumerate(blogs):
            self.stdout.write(f'Processing blog {i+1}/{blogs.count()}: ID={blog.id} - {blog.title[:30]}...')
            
            try:
                # Check if thumbnail exists
                if not blog.thumbnail:
                    self.stdout.write(self.style.WARNING(f"Blog {blog.id} has no thumbnail field"))
                    continue
                    
                # Check if thumbnail file exists
                file_exists = True
                image_path = ""
                try:
                    image_path = blog.thumbnail.path
                    if not os.path.exists(image_path):
                        file_exists = False
                        missing_count += 1
                        self.stdout.write(self.style.ERROR(f"✗ Thumbnail file does not exist at path: {image_path}"))
                    else:
                        self.stdout.write(f"Thumbnail path: {image_path}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Cannot access thumbnail path for blog {blog.id}: {e}"))
                    file_exists = False
                    missing_count += 1
                
                # Handle missing file case
                if not file_exists:
                    if sync:
                        # Clear the thumbnail reference in database
                        self.stdout.write(self.style.WARNING(f"Syncing database: clearing thumbnail reference for blog {blog.id}"))
                        blog.thumbnail = None
                        if blog.thumbnail_webp:
                            blog.thumbnail_webp = None
                        blog.save()
                        synced_count += 1
                    continue
                
                # If scan only, mark as success and continue
                if scan_only:
                    self.stdout.write(self.style.SUCCESS(f"✓ Thumbnail for blog {blog.id} exists and is valid"))
                    success_count += 1
                    continue
                
                # Create WebP version if not in scan-only mode
                self.stdout.write(f"Converting thumbnail for blog {blog.id}...")
                optimized = optimize_image(blog.thumbnail, quality=quality, format="WEBP")
                
                if optimized:
                    self.stdout.write(f"Optimized thumbnail created, saving to WebP...")
                    webp_name = f"{blog.id}_webp.webp"
                    blog.thumbnail_webp.save(
                        webp_name,
                        optimized,
                        save=True
                    )
                    self.stdout.write(self.style.SUCCESS(f"✓ Converted blog {blog.id} thumbnail to WebP as {webp_name}"))
                    success_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Optimizer returned None for blog {blog.id}"))
                    error_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error processing blog {blog.id} thumbnail: {e}"))
                self.stdout.write(traceback.format_exc())
                error_count += 1
        
        # Output summary for this section
        if scan_only:
            self.stdout.write(self.style.SUCCESS(
                f'Blog thumbnail scan completed: {success_count} valid, {missing_count} missing, {error_count} errors'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Blog thumbnail conversion completed: {success_count} successful, {error_count} failed'
            ))
            
        if sync and synced_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Database sync: {synced_count} blog references updated'))
        
        return success_count, error_count, missing_count, synced_count
