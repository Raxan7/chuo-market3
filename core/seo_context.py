from django.conf import settings
from django.templatetags.static import static

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

    # Structured data (built in Python so templates can use json_script filter)
    logo_url = f"{base_url}{static('app/images/logo.png')}"
    organization_json_ld = {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        'name': 'ChuoSmart',
        'url': base_url,
        'logo': logo_url,
        'description': (
            "Tanzania's first platform to combine online education and "
            "digital commerce into a single ecosystem"
        ),
        'foundingDate': '2024',
        'address': {
            '@type': 'PostalAddress',
            'addressLocality': 'Dodoma',
            'addressRegion': 'Dodoma',
            'addressCountry': 'Tanzania',
        },
        'contactPoint': {
            '@type': 'ContactPoint',
            'contactType': 'customer service',
            'email': 'support@chuosmart.com',
        },
        'sameAs': [
            'https://instagram.com/chuosmart',
            'https://linkedin.com/company/chuosmart',
            'https://twitter.com/chuosmart',
        ],
    }
    website_json_ld = {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'url': base_url,
        'name': 'ChuoSmart',
        'potentialAction': {
            '@type': 'SearchAction',
            'target': f"{base_url}/search/?q={{search_term}}",
            'query-input': 'required name=search_term',
        },
    }

    return {
        'site_name': site_name,
        'default_meta_description': default_description,
        'default_meta_keywords': default_keywords,
        'canonical_url': canonical_url,
        'base_url': base_url,
        'seo_should_index': True,
        'organization_json_ld': organization_json_ld,
        'website_json_ld': website_json_ld,
    }
