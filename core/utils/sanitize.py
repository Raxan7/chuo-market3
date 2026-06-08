"""
HTML sanitization and safe URL utilities.

Centralized place to clean user-supplied HTML and validate URLs before they
reach templates. Use these helpers instead of Django's ``mark_safe`` and
``{{ var|safe }}`` which disable auto-escaping and create XSS opportunities.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from django.utils.html import escape, strip_tags
from django.utils.safestring import mark_safe

try:
    import bleach
except ImportError:
    bleach = None


# Bleach allowlists ---------------------------------------------------------

# Tags typically authored in rich-text editors (TinyMCE, etc.) for blog posts,
# course descriptions, job postings, and similar content.
ALLOWED_TAGS = [
    "a", "abbr", "b", "blockquote", "br", "code", "del", "div", "dd", "dl",
    "dt", "em", "figure", "figcaption", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "ins", "kbd", "li", "mark", "ol", "p", "pre", "q",
    "s", "small", "span", "strong", "sub", "sup", "table", "tbody", "td",
    "tfoot", "th", "thead", "tr", "u", "ul",
]

# Attributes allowed per tag.  Only safe URL-scheme attributes are accepted.
ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "title", "lang", "dir"],
    "a": ["href", "name", "target", "rel", "class", "id", "title"],
    "img": ["src", "alt", "width", "height", "class", "id", "loading", "decoding"],
    "table": ["class", "id"],
    "th": ["scope", "colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel"]


# URL schemes we will ever follow from a user-supplied href.  Anything else
# (e.g. ``javascript:``, ``data:``, ``vbscript:``) is stripped to ``#``.
SAFE_URL_SCHEMES = frozenset({"http", "https", "mailto", "tel", ""})


def _normalize_url(value: str) -> str:
    """Return a sanitized version of ``value`` for use in ``href`` / ``src``.

    - Empty / whitespace strings collapse to ``#`` so a malicious value cannot
      become a clickable target.
    - Schemes outside :data:`SAFE_URL_SCHEMES` are rejected.
    - Returns ``#`` for any non-conforming value so the link is still visible
      but does not execute or navigate.
    """
    if value is None:
        return "#"
    value = str(value).strip()
    if not value:
        return "#"

    # Disallow control characters and whitespace inside the value
    if any(ord(c) < 0x20 for c in value):
        return "#"

    parsed = urlparse(value)
    scheme = (parsed.scheme or "").lower()

    # A leading "javascript" / "data" / "vbscript" scheme (or any other
    # dangerous scheme) is the classic XSS vector; refuse it outright.
    if scheme and scheme not in SAFE_URL_SCHEMES:
        return "#"

    # For relative URLs, the parsed scheme is ""; that's fine.
    return value


def clean_html(value) -> str:
    """Return ``value`` as safe, bleach-sanitized HTML.

    Use this anywhere a rich-text field needs to be rendered.  The output is
    already marked safe for the template engine so callers do not need to
    re-apply ``|safe``.
    """
    if not value:
        return ""
    if not isinstance(value, str):
        value = str(value)

    if bleach is not None:
        cleaned = bleach.clean(
            value,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True,
            strip_comments=True,
        )
        cleaned = bleach.linkify(
            cleaned,
            callbacks=[_normalize_hrefs],
            skip_tags=["pre", "code"],
        )
        return mark_safe(cleaned)

    return mark_safe(strip_tags(value))


def _normalize_hrefs(attrs, new=False):
    """bleach callback to scrub href / src values after bleach has accepted them."""
    normalized = dict(attrs)
    if "href" in normalized:
        href_value = normalized["href"]
        normalized["href"] = (
            "#" if _looks_dangerous(href_value)
            else _normalize_url(href_value)
        )
    if "src" in normalized:
        src_value = normalized["src"]
        normalized["src"] = (
            "#" if _looks_dangerous(src_value)
            else _normalize_url(src_value)
        )
    # Force external links to open safely
    if normalized.get("href", "").startswith(("http://", "https://")):
        normalized["target"] = "_blank"
        normalized["rel"] = "noopener noreferrer nofollow"
    return normalized


_DANGEROUS = re.compile(r"^(?:javascript|vbscript|data|file):", re.IGNORECASE)


def _looks_dangerous(value: str) -> bool:
    return bool(_DANGEROUS.match(value.strip()))


def safe_href(value) -> str:
    """Return a value safe for use in an ``href`` attribute.

    Empty / dangerous values become ``#``.  Useful for plain strings that the
    template previously put straight into ``href="{{ var }}"``.
    """
    return _normalize_url(value)


def safe_src(value) -> str:
    """Return a value safe for use in a ``src`` attribute."""
    return _normalize_url(value)
