"""
Utilities for image optimization and processing
"""
import os
from PIL import Image
from io import BytesIO
import sys
from django.core.files.uploadedfile import InMemoryUploadedFile

def convert_to_webp(image_field):
    """
    Convert an uploaded image to WebP format for better performance
    
    Args:
        image_field: The uploaded image field from a form
        
    Returns:
        InMemoryUploadedFile: The processed WebP image
    """
    if not image_field:
        return None
        
    # Open the uploaded image
    img = Image.open(image_field)
    
    # Create output buffer for the WebP image
    output = BytesIO()
    
    # Convert to RGB if needed (WebP doesn't support RGBA in some cases)
    if img.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
        img = background
    
    # Save as WebP with high quality but still better compression than JPEG
    img.save(output, format='WEBP', quality=85, optimize=True)
    
    # Get the original filename and create a new one with .webp extension
    original_name = os.path.splitext(image_field.name)[0]
    output_filename = f"{original_name}.webp"
    
    # Create a new Django file object
    webp_image = InMemoryUploadedFile(
        output,
        'ImageField',
        output_filename,
        'image/webp',
        sys.getsizeof(output),
        None
    )
    
    return webp_image

def optimize_image(image_field, max_size=(1200, 1200), quality=85, format=None):
    """
    Optimize an uploaded image by resizing and compressing
    
    Args:
        image_field: The uploaded image field from a form
        max_size: The maximum dimensions (width, height) the image should have
        quality: The quality of the output image (1-100)
        format: The format to save the image as (e.g. "WEBP"). If None, uses original format.
        
    Returns:
        InMemoryUploadedFile: The optimized image
    """
    if not image_field:
        return None
        
    # Open the uploaded image
    img = Image.open(image_field)
    
    # Calculate new dimensions while maintaining aspect ratio
    width, height = img.size
    if width > max_size[0] or height > max_size[1]:
        # Calculate the ratio
        ratio = min(max_size[0] / width, max_size[1] / height)
        new_size = (int(width * ratio), int(height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    
    # Create output buffer
    output = BytesIO()
    
    # Determine format
    save_format = None
    
    if format:
        # Use the specified format
        save_format = format
        if save_format.upper() in ['JPEG', 'JPG']:
            img = img.convert('RGB')  # Remove alpha channel for JPEG
        elif save_format.upper() == 'WEBP':
            # WebP can handle transparency
            pass
    else:
        # Use format based on file extension if no format specified
        file_ext = os.path.splitext(image_field.name)[1].lower()
        
        if file_ext in ['.jpg', '.jpeg']:
            save_format = 'JPEG'
            img = img.convert('RGB')  # Remove alpha channel if present
        elif file_ext == '.png':
            save_format = 'PNG'
        elif file_ext == '.gif':
            save_format = 'GIF'
        elif file_ext == '.webp':
            save_format = 'WEBP'
        else:
            # Default to JPEG for unknown formats
            save_format = 'JPEG'
            img = img.convert('RGB')
    
    # Save the image in the determined format
    if save_format in ['JPEG', 'WEBP']:
        img.save(output, format=save_format, quality=quality, optimize=True)
    else:
        img.save(output, format=save_format, optimize=True)
    
    # Create a new Django file object
    output_name = image_field.name
    
    # Update file extension if format is specified
    if format:
        base_name = os.path.splitext(output_name)[0]
        ext = format.lower()
        if ext == 'jpeg':
            ext = 'jpg'
        output_name = f"{base_name}.{ext}"
    
    # Determine the appropriate content_type based on the format or filename
    # ImageFieldFile might not have content_type, so we need to determine it from the file extension or specified format
    content_type = None
    
    # First try to determine from the specified format parameter
    if format:
        if format.upper() == 'WEBP':
            content_type = 'image/webp'
        elif format.upper() in ['JPEG', 'JPG']:
            content_type = 'image/jpeg'
        elif format.upper() == 'PNG':
            content_type = 'image/png'
        elif format.upper() == 'GIF':
            content_type = 'image/gif'
    
    # If format wasn't specified or recognized, use the file extension
    if not content_type:
        file_ext = os.path.splitext(image_field.name)[1].lower()
        if file_ext in ['.jpg', '.jpeg']:
            content_type = 'image/jpeg'
        elif file_ext == '.png':
            content_type = 'image/png'
        elif file_ext == '.gif':
            content_type = 'image/gif'
        elif file_ext == '.webp':
            content_type = 'image/webp'
        else:
            # Default to jpeg if we can't determine
            content_type = 'image/jpeg'
    
    # Try to get content_type attribute if available (for uploaded files)
    if hasattr(image_field, 'content_type') and image_field.content_type:
        # Only use it if we haven't specified a different format
        if not format:
            content_type = image_field.content_type
    
    optimized_image = InMemoryUploadedFile(
        output,
        'ImageField',
        output_name,
        content_type,
        sys.getsizeof(output),
        None
    )
    
    return optimized_image
