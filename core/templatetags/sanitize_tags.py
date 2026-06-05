"""
Template tags and filters for safe HTML/URL rendering.

These filters replace the dangerous ``|safe`` filter for user-authored
content.  All of them go through :mod:`core.utils.sanitize`, which uses
``bleach`` to strip disallowed tags and dangerous URL schemes.
"""
from django import template

from core.utils.sanitize import clean_html, safe_href, safe_src


register = template.Library()


@register.filter(name="sanitize")
def sanitize_filter(value):
    """Return ``value`` as safe HTML, sanitized with bleach.

    Use this in place of ``{{ value|safe }}`` for any user-authored rich
    text (blog posts, course content, job descriptions, etc.).
    """
    return clean_html(value)


@register.filter(name="safe_href")
def safe_href_filter(value):
    """Return ``value`` validated for use in an ``href`` attribute.

    Falls back to ``#`` for empty or dangerous values.
    """
    return safe_href(value)


@register.filter(name="safe_src")
def safe_src_filter(value):
    """Return ``value`` validated for use in a ``src`` attribute."""
    return safe_src(value)
