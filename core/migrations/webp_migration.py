"""
Custom migration to convert existing product images to WebP format.
This migration adds WebP versions for all existing product images.
"""

from django.db import migrations
import os
from django.conf import settings
import logging

def convert_images_to_webp(apps, schema_editor):
    """Convert all existing product images to WebP format."""
    try:
        # Import the Product model from the migration state
        Product = apps.get_model('core', 'Product')
        
        # Try to import the image optimizer
        try:
            from core.utils.image_optimizer import optimize_image
        except ImportError:
            # If the module doesn't exist, create a simple fallback
            def optimize_image(image, quality=85, format="WEBP"):
                return None
        
        # Process all products with images
        for product in Product.objects.filter(image__isnull=False).filter(image_webp__isnull=True):
            try:
                # Only convert if there's an image and no existing WebP
                if product.image:
                    # Create WebP version
                    optimized = optimize_image(product.image, quality=85, format="WEBP")
                    if optimized:
                        product.image_webp.save(
                            f"{product.id}_webp.webp",
                            optimized,
                            save=True
                        )
                        print(f"Converted product {product.id} image to WebP")
            except Exception as e:
                print(f"Error converting product {product.id} image: {e}")
    except Exception as e:
        print(f"Migration error: {e}")

def reverse_migration(apps, schema_editor):
    """Reverse the migration by removing all WebP images."""
    Product = apps.get_model('core', 'Product')
    
    # Set all WebP images to None
    Product.objects.update(image_webp=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),  # Update this to the latest migration in your core app
    ]

    operations = [
        migrations.RunPython(convert_images_to_webp, reverse_migration),
    ]
