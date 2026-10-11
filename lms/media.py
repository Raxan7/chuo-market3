from urllib.parse import parse_qs, quote, urlparse

from django.core.exceptions import ValidationError


YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}

SOUNDCLOUD_HOSTS = {
    "soundcloud.com",
    "www.soundcloud.com",
    "m.soundcloud.com",
    "on.soundcloud.com",
}


def _parsed_http_url(value):
    value = (value or "").strip()

    if not value:
        return None

    parsed = urlparse(value)

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValidationError(
            "Only secure http/https media links are allowed."
        )

    if not parsed.hostname:
        raise ValidationError("Invalid media URL.")

    return parsed


def youtube_video_id(value):
    parsed = _parsed_http_url(value)

    if not parsed:
        return None

    host = parsed.hostname.lower()

    if host not in YOUTUBE_HOSTS:
        return None

    candidate = ""

    if host.endswith("youtu.be"):
        candidate = parsed.path.strip("/").split("/")[0]

    elif parsed.path == "/watch":
        candidate = (parse_qs(parsed.query).get("v") or [""])[0]

    else:
        parts = [p for p in parsed.path.split("/") if p]

        if parts and parts[0] in {"embed", "shorts", "live"}:
            candidate = parts[1] if len(parts) > 1 else ""

    candidate = candidate.strip()

    if len(candidate) != 11:
        return None

    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789_-"
    )

    if any(char not in allowed for char in candidate):
        return None

    return candidate


def youtube_embed_url(value):
    video_id = youtube_video_id(value)

    if not video_id:
        raise ValidationError(
            "Video lessons currently support YouTube links only. "
            "Upload the video as Unlisted on YouTube and paste its URL."
        )

    return (
        f"https://www.youtube-nocookie.com/embed/{video_id}"
        "?rel=0&modestbranding=1"
    )


def is_soundcloud_url(value):
    try:
        parsed = _parsed_http_url(value)
    except ValidationError:
        return False

    return bool(
        parsed
        and parsed.hostname
        and parsed.hostname.lower() in SOUNDCLOUD_HOSTS
    )


def soundcloud_embed_url(value):
    if not value:
        return ""

    parsed = _parsed_http_url(value)

    if not parsed or parsed.hostname.lower() not in SOUNDCLOUD_HOSTS:
        return ""

    original = value.strip()

    return (
        "https://w.soundcloud.com/player/"
        f"?url={quote(original, safe='')}"
        "&auto_play=false"
        "&hide_related=true"
        "&show_comments=false"
        "&show_user=true"
        "&show_reposts=false"
        "&visual=false"
    )


def normalize_course_content_media(
    instance,
    content_type,
    video_url=None,
    external_link=None,
):
    if content_type == "video":
        instance.video_url = youtube_embed_url(video_url)

    elif content_type == "link":
        # URLField already validates syntax, but enforce browser-safe schemes.
        if external_link:
            _parsed_http_url(external_link)
            instance.external_link = external_link.strip()

    return instance
