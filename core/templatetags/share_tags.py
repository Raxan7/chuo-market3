"""Public-content sharing links shared by courses, products and articles.

Always derive the destination from a local path supplied by a Django URL tag.
No client-submitted URL or query parameters are used in social share links.
"""
from urllib.parse import urlencode, urlsplit

from django import template

register = template.Library()


@register.inclusion_tag('app/components/social_share.html', takes_context=True)
def share_buttons(context, title, public_path=None, compact=False):
    """Render reusable, URL-encoded share actions for a public page.

    ``public_path`` should come from ``{% url ... %}`` and is optional on a
    detail page. Strip query/fragment strings to avoid leaking session links.
    """
    request = context.get('request')
    path = str(public_path or (request.path if request else '/') or '/')
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith('/') or parsed.path.startswith('//'):
        # A page must never turn user-controlled external URLs into share targets.
        path = request.path if request else '/'
        parsed = urlsplit(path)
    path = parsed.path

    # seo_context supplies the site's fixed public domain, matching og:url.
    base_url = str(context.get('base_url') or '').rstrip('/')
    base = urlsplit(base_url)
    if base.scheme not in ('https', 'http') or not base.netloc:
        base_url = request.build_absolute_uri('/')[:-1] if request else ''
    url = f'{base_url}{path}'
    title = str(title or 'ChuoSmart')

    return {
        'share_title': title,
        'share_url': url,
        'share_compact': compact,
        'share_whatsapp': 'https://wa.me/?' + urlencode({'text': f'{title} {url}'}),
        'share_facebook': 'https://www.facebook.com/sharer/sharer.php?' + urlencode({'u': url}),
        'share_x': 'https://twitter.com/intent/tweet?' + urlencode({'text': title, 'url': url}),
        'share_linkedin': 'https://www.linkedin.com/sharing/share-offsite/?' + urlencode({'url': url}),
        'share_email': 'mailto:?' + urlencode({'subject': title, 'body': f'{title}\n{url}'}),
    }
