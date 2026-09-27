from hashlib import sha256
from urllib.parse import parse_qs, urlparse

from django import template

register = template.Library()

ADSTERRA_SMARTLINK_HOST = "www.profitableratecpmnetwork.com"
FORBIDDEN_ADSTERRA_SMARTLINK_NUMBERS = frozenset({2, 27, 33})
EXPECTED_ADSTERRA_SMARTLINK_COUNT = 47

# Smartlinks 2, 27 and 33 are intentionally absent from this approved pool.
ADSTERRA_SMARTLINKS = (
    {"number": 14, "url": "https://www.profitableratecpmnetwork.com/wgt39574?key=85a58831e5ef0853931fff406e1dfa8c"},
    {"number": 11, "url": "https://www.profitableratecpmnetwork.com/e4hjiidt6?key=8c5f8ee94d5268733bb643f329f5a6b8"},
    {"number": 6, "url": "https://www.profitableratecpmnetwork.com/haayebup3?key=fe1f795150cb5ca60e0524dc399ae61b"},
    {"number": 4, "url": "https://www.profitableratecpmnetwork.com/ap4cqrm6?key=d75c442ae0f59d9b0d7c9c3d1e7e0388"},
    {"number": 10, "url": "https://www.profitableratecpmnetwork.com/tkz5gnef?key=3382553661b9a9d658e6f39f192894c6"},
    {"number": 7, "url": "https://www.profitableratecpmnetwork.com/q2fzrhpqrc?key=72b2b04bfa0ef8a788fbfd9672244401"},
    {"number": 15, "url": "https://www.profitableratecpmnetwork.com/wd297g75w?key=dde685a077b96f8a4db7d26897833101"},
    {"number": 5, "url": "https://www.profitableratecpmnetwork.com/gt2zsyka7?key=c8877265b6a9dd41166fb195cb7bfd9d"},
    {"number": 17, "url": "https://www.profitableratecpmnetwork.com/fwwsu475?key=27e3dca44a6f64f966efea0e1dabdbb6"},
    {"number": 12, "url": "https://www.profitableratecpmnetwork.com/id9jk679?key=fbecc44e6837b131339a4b7cd0420a86"},
    {"number": 8, "url": "https://www.profitableratecpmnetwork.com/kq9p777p?key=483e1c7401bb4d74727ac28fc788b462"},
    {"number": 1, "url": "https://www.profitableratecpmnetwork.com/huniquwits?key=291a16ad800e75fbd50d7d9463b368d8"},
    {"number": 20, "url": "https://www.profitableratecpmnetwork.com/hfbka17sz9?key=c4984d9064a74175fd5318f4cdbac1bd"},
    {"number": 16, "url": "https://www.profitableratecpmnetwork.com/rr17qstm?key=2b2b5318a35a67f71ee930415524ecd9"},
    {"number": 13, "url": "https://www.profitableratecpmnetwork.com/ikw0j9cjm?key=7ab65989df348f4422af7d79cf98af37"},
    {"number": 25, "url": "https://www.profitableratecpmnetwork.com/zrx22zkaf?key=9fc31c1bfb7c6addb5a4795f4a8cbee0"},
    {"number": 29, "url": "https://www.profitableratecpmnetwork.com/kkcwpkfb?key=37a86f32916458ed452e574e51086283"},
    {"number": 30, "url": "https://www.profitableratecpmnetwork.com/iedcy3tvr?key=cf45e14d04fa60e422b8bbe18078ddff"},
    {"number": 28, "url": "https://www.profitableratecpmnetwork.com/jht9218zue?key=13d8568145e6855cc6f0ca95979c7c90"},
    {"number": 31, "url": "https://www.profitableratecpmnetwork.com/sm5j0k56v9?key=98fc44b8a0e7375981b790ac1e83516e"},
    {"number": 21, "url": "https://www.profitableratecpmnetwork.com/jf0isqj0?key=34f6acdf1a11006d15e1963d493f1758"},
    {"number": 23, "url": "https://www.profitableratecpmnetwork.com/t93nmvvwk?key=fe84c06cc64b9f09d4162121cf9d7bdb"},
    {"number": 24, "url": "https://www.profitableratecpmnetwork.com/v0h11y5va5?key=6b7d78a80b38beec9ad76519b346b771"},
    {"number": 32, "url": "https://www.profitableratecpmnetwork.com/w6j75210?key=63a7b0b4a042ef5b4c6a61fc65ecec6a"},
    {"number": 35, "url": "https://www.profitableratecpmnetwork.com/r1ieth9q?key=53327f2893cb33a944255cb83eac7f13"},
    {"number": 36, "url": "https://www.profitableratecpmnetwork.com/gaii99tr?key=9c3982f5824644c9c5090ac872246d7a"},
    {"number": 37, "url": "https://www.profitableratecpmnetwork.com/ivdcq07b?key=931bf0ed3d1f1990bf8b4951d3279800"},
    {"number": 39, "url": "https://www.profitableratecpmnetwork.com/cc8pfbr7?key=6c2aab23f30a7e12d1ec7e18129af1b3"},
    {"number": 38, "url": "https://www.profitableratecpmnetwork.com/cp1q5ssu?key=f66c721838c6d7324f065260a1f6421b"},
    {"number": 40, "url": "https://www.profitableratecpmnetwork.com/rdmw8yngr?key=43e10589b612a94737ee7ae473b3ab29"},
    {"number": 41, "url": "https://www.profitableratecpmnetwork.com/r1q9egk4?key=1f7458d652732015971b109fb110695d"},
    {"number": 42, "url": "https://www.profitableratecpmnetwork.com/xxvwbrkwf7?key=30b581430792a0c96437637cd3dfa380"},
    {"number": 43, "url": "https://www.profitableratecpmnetwork.com/rdjc0re2dm?key=fc30ad7327eb90386255eebf3f09e2de"},
    {"number": 44, "url": "https://www.profitableratecpmnetwork.com/yaaykcs93g?key=59830caf63a846f6099f1d33e07affd1"},
    {"number": 45, "url": "https://www.profitableratecpmnetwork.com/uuh7u84571?key=afd6856023e600c7ca1a835b8392caa1"},
    {"number": 19, "url": "https://www.profitableratecpmnetwork.com/x0dah1k4?key=46a17ba750056b6571b68a2477d87c7e"},
    {"number": 9, "url": "https://www.profitableratecpmnetwork.com/za2rd21i?key=4531286834d45f26d443af4c7023a163"},
    {"number": 22, "url": "https://www.profitableratecpmnetwork.com/cg7pm2azd?key=127ad6f621cc32a8f4dfc921c5ff3e9c"},
    {"number": 3, "url": "https://www.profitableratecpmnetwork.com/kwc3yfw0u?key=9a4745226e1e05e6678774ddd12e0296"},
    {"number": 18, "url": "https://www.profitableratecpmnetwork.com/vrap4x3bk?key=ce33b8ed6c3525af4c1048a7900abefd"},
    {"number": 34, "url": "https://www.profitableratecpmnetwork.com/b50bwpbg?key=58d0120393d8c2f346b6bd7f739520f5"},
    {"number": 26, "url": "https://www.profitableratecpmnetwork.com/g9pn3wpf2w?key=61c8e9f2c79ecbd839550059e46326d3"},
    {"number": 50, "url": "https://www.profitableratecpmnetwork.com/yp5mtt6q3?key=20163e7bd623eb1c1772175119779dad"},
    {"number": 48, "url": "https://www.profitableratecpmnetwork.com/yy39j2yk4s?key=9453cbc0600a16d928971721a472316a"},
    {"number": 49, "url": "https://www.profitableratecpmnetwork.com/iba1pvq1?key=3800aea6ba8adf23b5aaa0fb4f02db71"},
    {"number": 46, "url": "https://www.profitableratecpmnetwork.com/h0mui0g4?key=bfe89a1691816aaa4d4f11d902e56b17"},
    {"number": 47, "url": "https://www.profitableratecpmnetwork.com/iupec605?key=7f0d2e6fbeadf96836908833aca4918d"},
)


def _validate_smartlinks():
    numbers = [link["number"] for link in ADSTERRA_SMARTLINKS]
    if len(ADSTERRA_SMARTLINKS) != EXPECTED_ADSTERRA_SMARTLINK_COUNT:
        raise ValueError("Adsterra Smartlink pool must contain exactly 47 approved links.")
    if len(numbers) != len(set(numbers)):
        raise ValueError("Adsterra Smartlink numbers must be unique.")
    forbidden = FORBIDDEN_ADSTERRA_SMARTLINK_NUMBERS.intersection(numbers)
    if forbidden:
        raise ValueError(f"Forbidden Adsterra Smartlinks configured: {sorted(forbidden)}")
    for link in ADSTERRA_SMARTLINKS:
        parsed = urlparse(link["url"])
        if parsed.scheme != "https" or parsed.hostname != ADSTERRA_SMARTLINK_HOST:
            raise ValueError(f"Invalid Adsterra Smartlink URL: {link['url']}")
        key_values = parse_qs(parsed.query).get("key", [])
        if len(key_values) != 1 or not key_values[0]:
            raise ValueError(f"Adsterra Smartlink is missing its key: {link['url']}")

_validate_smartlinks()


def select_adsterra_smartlink(path="", occurrence=0):
    """Return a stable approved Smartlink for this page and ad occurrence."""
    try:
        occurrence = max(0, int(occurrence))
    except (TypeError, ValueError):
        occurrence = 0
    digest = sha256(str(path or "").encode("utf-8")).digest()
    offset = int.from_bytes(digest[:4], "big") % len(ADSTERRA_SMARTLINKS)
    return ADSTERRA_SMARTLINKS[(offset + occurrence) % len(ADSTERRA_SMARTLINKS)]


@register.simple_tag(takes_context=True)
def adsterra_smartlink(context, occurrence=0):
    request = context.get("request")
    path = request.get_full_path() if request is not None else ""
    return select_adsterra_smartlink(path=path, occurrence=occurrence)
