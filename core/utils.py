"""
Utility functions for the Core app
"""

import re


def clean_phone_number(phone):
    """
    Clean and validate phone number to ensure it's properly formatted.
    Returns None if invalid, formatted phone number if valid.
    
    Args:
        phone (str): Phone number to clean
        
    Returns:
        str: Cleaned phone number or None if invalid
    """
    if not phone or phone.strip() == "":
        return None
    
    # Remove all non-digit characters except the + sign at the beginning
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    # If doesn't start with +, add the default Tanzania code
    if not cleaned.startswith('+'):
        if cleaned.startswith('0'):
            cleaned = '+255' + cleaned[1:]
        elif not re.match(r'^\d{9,15}$', cleaned):
            return None
        else:
            cleaned = '+' + cleaned
    
    # Validate the length (international format: country code + number)
    if not re.match(r'^\+\d{9,14}$', cleaned):
        return None
        
    return cleaned[:15]  # Ensure it doesn't exceed the max length
