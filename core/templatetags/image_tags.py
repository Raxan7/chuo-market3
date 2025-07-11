"""
Template tags for image optimization and accessibility.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def optimized_img(src, alt, css_class='', lazy=True, width=None, height=None, style=None):
    """
    Create an optimized image tag with proper alt attributes and lazy loading.
    
    Usage: {% optimized_img src="path/to/image.jpg" alt="Descriptive text" css_class="img-fluid" %}
    
    Args:
        src: The image source URL
        alt: Descriptive alt text for accessibility (required)
        css_class: CSS classes to apply to the image
        lazy: Whether to use lazy loading (default: True)
        width: Optional width attribute 
        height: Optional height attribute
        style: Optional inline CSS styles
    
    Returns:
        str: HTML for an optimized image tag
    """
    # Ensure alt text is provided
    if not alt:
        alt = "Image on ChuoSmart"
    
    # Build attributes
    attrs = {
        'src': src,
        'alt': alt,
        'class': css_class,
    }
    
    # Add width and height if provided (important for preventing layout shifts)
    if width:
        attrs['width'] = width
    if height:
        attrs['height'] = height
        
    # Add inline styles if provided
    if style:
        attrs['style'] = style
        
    # Add lazy loading if enabled
    if lazy:
        attrs['loading'] = 'lazy'
        # Add decoding attribute for better performance
        attrs['decoding'] = 'async'
        
    # Add fetchpriority if this is a high-priority image (not lazy loaded)
    else:
        attrs['fetchpriority'] = 'high'
    
    # Build the HTML tag
    attrs_str = ' '.join([f'{k}="{v}"' for k, v in attrs.items() if v])
    html = f'<img {attrs_str}>'
    
    return mark_safe(html)
    
@register.simple_tag
def picture(webp_src=None, fallback_src=None, alt='', css_class='', lazy=True, width=None, height=None, style=None):
    """
    Create a <picture> element with WebP support and fallback to original format.
    
    Usage: {% picture webp_src=product.image_webp.url fallback_src=product.image.url alt="Product Image" %}
    Note: Now safely handles cases where image_webp field has no file or is None
    
    Args:
        webp_src: The WebP image source URL (can be None)
        fallback_src: The fallback image source URL (required)
        alt: Descriptive alt text for accessibility
        css_class: CSS classes to apply to the image
        lazy: Whether to use lazy loading (default: True)
        width: Optional width attribute
        height: Optional height attribute
        style: Optional inline CSS styles
    
    Returns:
        str: HTML for a picture element with WebP support
    """
    if not alt:
        alt = "Image on ChuoSmart"
    
    # Build image attributes
    img_attrs = {
        'src': fallback_src,
        'alt': alt,
        'class': css_class,
    }
    
    # Add dimensions if provided (important for preventing layout shifts)
    if width:
        img_attrs['width'] = width
    if height:
        img_attrs['height'] = height
    
    # Add inline styles if provided
    if style:
        img_attrs['style'] = style
    
    # Add lazy loading if enabled
    if lazy:
        img_attrs['loading'] = 'lazy'
        img_attrs['decoding'] = 'async'
    else:
        img_attrs['fetchpriority'] = 'high'
    
    # Build the image attributes string
    img_attrs_str = ' '.join([f'{k}="{v}"' for k, v in img_attrs.items() if v])
    
    # If we have a WebP version, use <picture> element
    # The webp_src can be None in cases where the ImageField has no file
    # or when template passes product.image_webp.url but image_webp is None/empty
    if webp_src:
        html = f'''
        <picture>
            <source srcset="{webp_src}" type="image/webp">
            <img {img_attrs_str}>
        </picture>
        '''
    else:
        html = f'<img {img_attrs_str}>'
    
    return mark_safe(html)

@register.filter
def ensure_alt(html, default_alt="ChuoSmart image"):
    """
    Ensure all img tags in the given HTML have alt attributes.
    
    Usage: {{ content_with_images|ensure_alt:"Product image" }}
    
    Args:
        html: HTML string containing img tags
        default_alt: Default alt text to use if none is present
    
    Returns:
        str: HTML with all img tags having alt attributes
    """
    import re
    
    # Find all img tags without alt attributes
    pattern = r'<img([^>]*?)(?:alt=(["\'])([^\2]*?)\2)?([^>]*?)>'
    
    def replace_img(match):
        attrs_before = match.group(1) or ''
        alt_quote = match.group(2)
        alt_text = match.group(3)
        attrs_after = match.group(4) or ''
        
        # If no alt attribute was found
        if not alt_quote:
            # Add default alt attribute
            return f'<img{attrs_before} alt="{default_alt}"{attrs_after}>'
        # If empty alt attribute was found
        elif not alt_text:
            # Replace with default alt
            return f'<img{attrs_before} alt="{default_alt}"{attrs_after}>'
        # Alt attribute exists and has content
        else:
            return match.group(0)
    
    # Replace all matches
    result = re.sub(pattern, replace_img, html)
    return mark_safe(result)

@register.filter
def safe_url(image_field):
    """
    Safely get the URL from an image field, returning None if the field is empty or has no file.
    
    Usage: {{ product.image_webp|safe_url }}
    
    Args:
        image_field: A Django ImageField object
        
    Returns:
        str or None: The URL of the image if available, otherwise None
    """
    if image_field is None:
        return None
        
    # Check if it's a valid image field with a file
    try:
        if hasattr(image_field, 'url') and image_field.name:
            return image_field.url
    except (ValueError, AttributeError, Exception) as e:
        # Log error if needed, but don't crash
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Error getting URL from image field: {e}")
        
    return None
