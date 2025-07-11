# Lazy Loading Implementation

This document outlines the lazy loading implementation and performance optimizations added to ChuoSmart to improve page load times and user experience.

## Implementation Overview

Lazy loading has been implemented across the platform with the following features:

1. **Native Browser Lazy Loading**
   - All non-critical images use the `loading="lazy"` attribute
   - Above-the-fold images (like the first banner) do not use lazy loading to ensure quick display

2. **WebP Image Support**
   - WebP images are served when available using the `<picture>` element with appropriate fallbacks
   - All product images are automatically converted to WebP for better performance

3. **Enhanced JavaScript Lazy Loading**
   - Using IntersectionObserver for better control over when images load
   - Preloading images before they enter the viewport (200px threshold)
   - Progressive enhancement that works with and without JavaScript

4. **Resource Hints**
   - DNS prefetching and preconnect for external domains
   - Preload for critical assets

## Template Tags

Two custom template tags are available for easy implementation of lazy loading:

### `optimized_img`
For simple image optimization:

```html
{% load image_tags %}
{% optimized_img src=image.url alt="Description" css_class="img-fluid" lazy=True %}
```

### `picture`
For WebP support with fallbacks:

```html
{% load image_tags %}
{% picture webp_src=product.image_webp.url if product.image_webp else None fallback_src=product.image.url alt=product.title %}
```

Or even better, using the `safe_url` filter:

```html
{% load image_tags %}
{% picture webp_src=product.image_webp|safe_url fallback_src=product.image.url alt=product.title %}
```

## Implementation Locations

Lazy loading has been implemented in the following templates:
- `home.html`: Product listings and banners
- `productdetail.html`: Product images
- `products_by_category.html`: Category product listings

## Performance Impact

The lazy loading implementation provides these performance benefits:
- Reduced initial page load size
- Faster First Contentful Paint (FCP)
- Improved Largest Contentful Paint (LCP)
- Lower bandwidth usage for mobile users
- Better Core Web Vitals scores

## Best Practices for Developers

When adding new images to templates:

1. Always include descriptive `alt` text for accessibility
2. Use the `picture` template tag when both WebP and original formats are available
3. Avoid lazy loading for critical above-the-fold images
4. Always specify width and height attributes to prevent layout shifts
5. Use `fetchpriority="high"` for the most important images

## Testing

The lazy loading implementation can be tested using:
- Chrome DevTools Network panel with throttling enabled
- Lighthouse performance audits
- WebPageTest.org for detailed waterfall analysis
