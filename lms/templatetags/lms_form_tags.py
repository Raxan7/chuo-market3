from django import template
from django.forms.widgets import Input

register = template.Library()

@register.filter(name='add_class')
def add_class(value, css_class):
    """Add a CSS class to a form field"""
    if hasattr(value, 'as_widget'):
        return value.as_widget(attrs={'class': css_class})
    else:
        # If value is not a form field, return it unchanged
        return value
