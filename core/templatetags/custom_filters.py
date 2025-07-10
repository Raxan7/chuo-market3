from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    return value.as_widget(attrs={'class': arg})

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary by key.
    
    Usage: 
    {{ dictionary|get_item:key }}
    
    Example for Help Center:
    {{ faqs|get_item:category.id }}
    """
    return dictionary.get(key, [])