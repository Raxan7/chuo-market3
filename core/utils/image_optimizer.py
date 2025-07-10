"""
Utilities for image processing and optimization.
Includes functions to convert images to modern formats and optimize them.
"""
import os
from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.utils.text import slugify
import time
import random

def optimize_image(image, quality=85, format="WEBP"):
    """
    Convert and optimize an image to WEBP or other modern formats.
    
    Args:
        image: The image file to optimize
        quality: Quality level for compression (1-100)
        format: Target format (WEBP, JPEG, etc.)
    
    Returns:
        ContentFile: The optimized image as a ContentFile
    """
    if not image:
        return None
    
    img = Image.open(image)
    
    # Auto-orient image based on EXIF data
    img = ImageOps.exif_transpose(img)
    
    # Determine optimal dimensions based on image size
    # Let's cap the max dimension to 1920px for large images
    max_dimension = 1920
    width, height = img.size
    
    if width > max_dimension or height > max_dimension:
        # Calculate the scaling factor
        scale = min(max_dimension / width, max_dimension / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Resize the image
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Convert to RGB if not already (some formats like PNG can have RGBA)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Save the optimized image
    output = BytesIO()
    img.save(output, format=format, quality=quality, optimize=True)
    output.seek(0)
    
    # Create a new filename with the target format extension
    original_name = os.path.splitext(os.path.basename(image.name))[0]
    new_name = f"{slugify(original_name)}.{format.lower()}"
    
    return ContentFile(output.getvalue(), name=new_name)

def generate_unique_filename(filename):
    """
    Generate a unique filename by adding timestamp and random number.
    Helps prevent cache issues when replacing images.
    
    Args:
        filename: The original filename
    
    Returns:
        str: A unique filename
    """
    base_name, ext = os.path.splitext(filename)
    timestamp = int(time.time())
    random_number = random.randint(1000, 9999)
    unique_name = f"{slugify(base_name)}_{timestamp}_{random_number}{ext}"
    return unique_name
