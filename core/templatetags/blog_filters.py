from django import template
import re

register = template.Library()

@register.filter
def process_mixed_markdown(content):
    """
    Process content that might contain a mix of HTML and Markdown-style formatting.
    Converts **text** to <strong>text</strong> and *text* to <em>text</em> while preserving HTML.
    Also handles other common Markdown formatting rules and problematic content.
    """
    if not content:
        return content
        
    # Fix for content wrapped in curly braces (problematic editor output)
    if content.startswith('{') and content.endswith('}') and '<' in content[:100]:
        content = content[1:-1]  # Remove outer curly braces
        
    # Handle **bold** syntax (convert to <strong>)
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    
    # Handle *italic* syntax (convert to <em>)
    # Use negative lookbehind/lookahead to avoid matching inside **text**
    content = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<em>\1</em>', content)
    
    # Handle __bold__ alternate syntax
    content = re.sub(r'__(.*?)__', r'<strong>\1</strong>', content)
    
    # Handle _italic_ alternate syntax
    content = re.sub(r'(?<!_)_(?!_)(.*?)(?<!_)_(?!_)', r'<em>\1</em>', content)
    
    # Handle simple headers (# Header) - only if at beginning of line
    content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
    content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
    
    # Handle simple links [text](url)
    content = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', content)
    
    # Handle simple lists
    # Convert "- item" to list items (only at beginning of line)
    lines = content.split('\n')
    in_list = False
    result = []
    
    for line in lines:
        if line.strip().startswith('- '):
            if not in_list:
                result.append('<ul>')
                in_list = True
            item_content = line.strip()[2:]  # Remove the "- " prefix
            result.append(f'<li>{item_content}</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(line)
    
    if in_list:
        result.append('</ul>')
    
    content = '\n'.join(result)
    
    # Remove data attributes that might be visible as raw text
    content = re.sub(r'\s+data-[a-zA-Z0-9_-]+=["|\'][^"\']*["|\']', '', content)
    
    return content
