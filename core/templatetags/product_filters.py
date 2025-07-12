from django import template
import re

register = template.Library()

@register.filter
def process_product_description(content):
    """
    Process product descriptions that might contain problematic formatting.
    Handles HTML content wrapped in curly braces and other common formatting issues.
    """
    if not content:
        return content
        
    # Fix for content wrapped in curly braces (problematic editor output)
    if content.startswith('{') and content.endswith('}'):
        content = content[1:-1]  # Remove outer curly braces
    
    # Fix for HTML tags displayed as text (&lt;p&gt; etc.)
    content = content.replace('&lt;', '<')
    content = content.replace('&gt;', '>')
    content = content.replace('&amp;lt;', '<')
    content = content.replace('&amp;gt;', '>')
    
    # Fix HTML entity escaping
    content = content.replace('&amp;', '&')
    
    # Handle **bold** syntax (convert to <strong>)
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    
    # Handle *italic* syntax (convert to <em>)
    content = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<em>\1</em>', content)
    
    # Handle simple headers (# Header) - only if at beginning of line
    content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
    content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    
    # Fix malformed HTML tags that might be visibly displayed
    # This regex finds patterns like <p> text </p> where the tags might be displayed as text
    content = re.sub(r'&lt;(\w+)&gt;(.*?)&lt;/\1&gt;', r'<\1>\2</\1>', content)
    
    return content
