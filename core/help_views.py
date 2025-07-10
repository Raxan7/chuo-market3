from django.shortcuts import render
from core.help_center import CATEGORIES, FAQS, GUIDES, CONTACT_CHANNELS

def help_center(request):
    """Render the Help Center page with FAQs and support information"""
    
    context = {
        'categories': CATEGORIES,
        'faqs': FAQS,
        'guides': GUIDES,
        'contact_channels': CONTACT_CHANNELS
    }
    
    return render(request, 'app/help_center.html', context)
