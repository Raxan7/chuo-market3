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

def optimize_image(image_field, max_size=(1200, 1200), quality=85):
    """
    Optimize an uploaded image by resizing and compressing
    
    Args:
        image_field: The uploaded image field from a form
        max_size: The maximum dimensions (width, height) the image should have
        quality: The quality of the output image (1-100)
        
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
    file_ext = os.path.splitext(image_field.name)[1].lower()
    
    if file_ext in ['.jpg', '.jpeg']:
        img = img.convert('RGB')  # Remove alpha channel if present
        img.save(output, format='JPEG', quality=quality, optimize=True)
    elif file_ext == '.png':
        img.save(output, format='PNG', optimize=True)
    elif file_ext == '.gif':
        img.save(output, format='GIF', optimize=True)
    elif file_ext == '.webp':
        img.save(output, format='WEBP', quality=quality, optimize=True)
    else:
        # Default to JPEG for unknown formats
        img = img.convert('RGB')
        img.save(output, format='JPEG', quality=quality, optimize=True)
    
    # Create a new Django file object
    optimized_image = InMemoryUploadedFile(
        output,
        'ImageField',
        image_field.name,
        image_field.content_type,
        sys.getsizeof(output),
        None
    )
    
    return optimized_image
