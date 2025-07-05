"""
Custom template tags and filters for the LMS app
"""

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary by key
    """
    if not isinstance(key, (int, str)):
        key = key.id  # Allow object keys, using their ID
    return dictionary.get(key, {})
