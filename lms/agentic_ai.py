"""Small synchronous client for the external agentic AI gateway."""

import json
from urllib import error, request

from django.conf import settings


class AgenticAIError(RuntimeError):
    def __init__(self, message, *, status_code=None, response_body=''):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    @property
    def rate_limited(self):
        text = f"{self} {self.response_body}".lower()
        return self.status_code == 429 or 'rate limit' in text or 'quota' in text or 'resource_exhausted' in text


def gateway_configured():
    return bool(
        getattr(settings, 'AGENTIC_AI_BASE_URL', '')
        and getattr(settings, 'AGENTIC_AI_API_KEY', '')
    )


def chat_completion(messages, *, route='structured', temperature=0.0, max_tokens=4000, response_format=None):
    base_url = getattr(settings, 'AGENTIC_AI_BASE_URL', '').rstrip('/')
    api_key = getattr(settings, 'AGENTIC_AI_API_KEY', '')
    timeout = float(getattr(settings, 'AGENTIC_AI_TIMEOUT_SECONDS', 240))

    if not base_url or not api_key:
        raise AgenticAIError('AGENTIC_AI_BASE_URL and AGENTIC_AI_API_KEY must both be configured')

    payload = {
        'messages': messages,
        'route': route,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'cache': False,
    }
    if response_format:
        payload['response_format'] = response_format

    # Match the working supervisory integration, whose base URL already ends in /v1,
    # while still accepting a service-root URL for backwards compatibility.
    endpoint = (
        f"{base_url}/chat/completions"
        if base_url.endswith('/v1')
        else f"{base_url}/v1/chat/completions"
    )

    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': api_key,
        },
        method='POST',
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode('utf-8')
    except error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace') if exc.fp else ''
        raise AgenticAIError(
            f'Agentic AI gateway returned HTTP {exc.code}',
            status_code=exc.code,
            response_body=body[:1000],
        ) from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise AgenticAIError(f'Agentic AI gateway network error: {exc}') from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AgenticAIError('Agentic AI gateway returned invalid JSON', response_body=raw[:1000]) from exc

    try:
        content = data['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError) as exc:
        raise AgenticAIError(
            'Agentic AI gateway response did not contain choices[0].message.content',
            response_body=raw[:1000],
        ) from exc

    # Some OpenAI-compatible providers can return content parts instead of one string.
    if isinstance(content, list):
        chunks = []
        for part in content:
            if isinstance(part, dict):
                chunks.append(str(part.get('text') or part.get('content') or ''))
            else:
                chunks.append(str(part))
        content = ''.join(chunks)

    return str(content), data.get('gateway_meta') or {}
