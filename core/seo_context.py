from django.conf import settings

def seo_context(request):
    """
    Add common SEO variables to the context
    """
    site_name = "ChuoSmart"
    default_description = "View free and paid courses for students in Tanzania. Buy and sell in the student marketplace and discover jobs and internships."
    default_keywords = (
        "view course, students free, free view course, view course weeks, course weeks kozi, "
        "online courses tanzania, student marketplace, jobs tanzania"
    )
    
    # Get domain from settings
    domain = getattr(settings, 'SITE_DOMAIN', 'chuosmart.com')
    
    # Handle canonical URLs
    path = request.path
    canonical_url = f"https://{domain}{path}"
    base_url = f"https://{domain}"
    
    return {
        'site_name': site_name,
        'default_meta_description': default_description,
        'default_meta_keywords': default_keywords,
        'canonical_url': canonical_url,
        'base_url': base_url,
        'seo_should_index': True,
    }
