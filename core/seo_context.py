def seo_context(request):
    """
    Add common SEO variables to the context
    """
    site_name = "ChuoSmart"
    default_description = "ChuoSmart - The smartest place to buy and sell college essentials, find talent, and access educational resources."
    
    return {
        'site_name': site_name,
        'default_meta_description': default_description,
        'canonical_url': request.build_absolute_uri(),
        'base_url': f"{request.scheme}://{request.get_host()}"
    }
