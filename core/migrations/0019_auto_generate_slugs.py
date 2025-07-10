from django.db import migrations
from django.utils.text import slugify

def create_slugs_for_existing_products(apps, schema_editor):
    """
    Create slugs for existing products
    """
    Product = apps.get_model('core', 'Product')
    for product in Product.objects.all():
        if not product.slug:
            original_slug = slugify(product.title)
            unique_slug = original_slug
            num = 1
            
            # Make sure the slug is unique
            while Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{original_slug}-{num}"
                num += 1
                
            product.slug = unique_slug
            product.save()

def reverse_slug_creation(apps, schema_editor):
    """
    Reverse operation - no need to do anything here
    """
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_product_slug'),
    ]

    operations = [
        migrations.RunPython(create_slugs_for_existing_products, reverse_slug_creation),
    ]
