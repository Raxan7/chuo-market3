# Template Tags for Image Handling

This directory contains template tags for optimized image handling on ChuoSmart.

## Available Tags and Filters

### `optimized_img` Tag
Creates an optimized image tag with proper alt attributes and lazy loading.

```django
{% load image_tags %}
{% optimized_img src=image.url alt="Description" css_class="img-fluid" lazy=True %}
```

### `picture` Tag
Creates a `<picture>` element with WebP support and fallback to original format.

**Safe usage with the safe_url filter:**
```django
{% load image_tags %}
{% picture webp_src=product.image_webp|safe_url fallback_src=product.image.url alt=product.title %}
```

### `safe_url` Filter
Safely gets the URL from an image field, returning None if the field is empty or has no file.

```django
{{ product.image_webp|safe_url }}
```

This filter helps prevent ValueError exceptions when accessing `.url` on an empty ImageField.

### `ensure_alt` Filter
Ensures all img tags in the given HTML have alt attributes.

```django
{{ content_with_images|ensure_alt:"Product image" }}
```

## Error Prevention

The `safe_url` filter was implemented to prevent ValueError exceptions when accessing `.url` on an ImageField that doesn't have an associated file. This can happen in several scenarios:

1. When the WebP conversion fails during product/blog creation
2. When the WebP file is deleted from the server but the database record remains
3. When running the convert_to_webp management command with --scan-only option

## Best Practices

Always use the `safe_url` filter when passing ImageField URLs to template tags:

```django
{% picture webp_src=product.image_webp|safe_url fallback_src=product.image.url alt=product.title %}
```

Instead of:

```django
{% picture webp_src=product.image_webp.url fallback_src=product.image.url alt=product.title %}
```

This ensures your templates will gracefully handle cases where the WebP image doesn't exist.
