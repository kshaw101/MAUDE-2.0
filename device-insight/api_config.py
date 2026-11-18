"""Credential formatting and safe error messages. Never log a secret or raw API error."""


def normalize_key(raw):
    value = (raw or '').strip()
    if value.startswith('OPENAI_API_KEY='):
        value = value.split('=', 1)[1].strip()
    if value.lower().startswith('bearer '):
        value = value[7:].strip()
    for left, right in [('"', '"'), ("'", "'"), ('“', '”'), ('‘', '’')]:
        if len(value) >= 2 and value.startswith(left) and value.endswith(right):
            value = value[1:-1].strip()
            break
    return value


def resolve_api_key(entered, configured):
    """An explicitly entered key always takes precedence over server configuration."""
    return normalize_key(entered) or normalize_key(configured)


def key_problem(value):
    if not value:
        return ''
    if any(c in value for c in ['*', '…']) or '...' in value:
        return 'This looks like a masked key. Paste the complete secret value, not the abbreviated version shown in the key list.'
    if any(c.isspace() for c in value):
        return 'The key contains spaces or line breaks. Paste only the complete API secret on one line.'
    if value.lower() in {'replace-with-your-api-key', 'your_actual_key_here', 'your_actual_key_goes_here'}:
        return 'That is the example placeholder. Enter an API secret from your OpenAI Platform account.'
    if not value.startswith('sk-'):
        return 'This field expects an OpenAI API secret starting with sk-. A ChatGPT password, key name, or website address will not work.'
    return ''


def public_api_error(exc):
    """Do not echo error.message: authentication errors may include credential fragments."""
    status = getattr(exc, 'status_code', None)
    if status == 401:
        return ('OpenAI rejected the supplied API key (401). Paste a valid, complete API secret '
                'in the password field and retry. No restart is needed for a pasted key. '
                'If it is still rejected, create a replacement key in OpenAI Platform.')
    if status == 429:
        body = getattr(exc, 'body', None)
        error = body.get('error', body) if isinstance(body, dict) else {}
        if isinstance(error, dict) and error.get('code') == 'insufficient_quota':
            return 'The API account has insufficient quota or credits (429). Check API billing in OpenAI Platform.'
        return 'OpenAI returned a quota or rate limit (429). Check API billing or wait and retry.'
    if status in (403, 404):
        return 'The API key or project cannot access the selected model (403/404). Check key permissions and model access.'
    if status is None:
        return 'Could not connect to OpenAI. Check the connection and retry.'
    return 'The API request failed. Check model access and retry. Your key and raw API error were not displayed.'
