from django import template
import random
from core.ads import AD_URLS

register = template.Library()

@register.simple_tag
def get_random_ad():
    """Return a random ad URL from the ad list"""
    return random.choice(AD_URLS)

@register.simple_tag
def get_all_ads_json():
    """Return all ads as a JSON string for JavaScript"""
    import json
    return json.dumps(AD_URLS)
