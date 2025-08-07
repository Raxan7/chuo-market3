from django.conf import settings

def seo_context(request):
    """
    Add common SEO variables to the context
    """
    site_name = "ChuoSmart"
    default_description = "College & university student marketplace in Tanzania. Buy, sell products, find talented students, and access educational resources."
    
    # Get domain from settings
    domain = getattr(settings, 'SITE_DOMAIN', 'chuosmart.com')
    
    # Handle canonical URLs
    path = request.path
    canonical_url = f"https://{domain}{path}"
    base_url = f"https://{domain}"
    
    return {
        'site_name': site_name,
        'default_meta_description': default_description,
        'canonical_url': canonical_url,
        'base_url': base_url
    }
