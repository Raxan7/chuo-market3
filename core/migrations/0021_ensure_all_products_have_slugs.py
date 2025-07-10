from django.db import migrations
from django.utils.text import slugify

def ensure_all_products_have_slugs(apps, schema_editor):
    """
    Double-check that all products have proper slugs
    """
    Product = apps.get_model('core', 'Product')
    for product in Product.objects.all():
        if not product.slug:
            # Create base slug from title
            base_slug = slugify(product.title)
            slug = base_slug
            counter = 1
            
            # Ensure slug is unique
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            product.slug = slug
            product.save()
            print(f"Generated slug '{slug}' for product ID {product.id}: {product.title}")

def reverse_operation(apps, schema_editor):
    """
    No need to do anything in reverse
    """
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0020_product_created_at_product_updated_at'),  # This is the correct dependency
    ]

    operations = [
        migrations.RunPython(ensure_all_products_have_slugs, reverse_operation),
    ]
