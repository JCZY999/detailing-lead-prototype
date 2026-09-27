"""Public configuration for the separately hosted AI Growth Engine backend."""
import os
from uuid import UUID
from urllib.parse import urlsplit


def widget_config():
    api_url = os.getenv('AI_GROWTH_ENGINE_API_URL', '').strip().rstrip('/')
    business_id = os.getenv('AI_GROWTH_ENGINE_BUSINESS_ID', '').strip()
    try:
        url = urlsplit(api_url)
        UUID(business_id)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            return {'enabled': False}
        # Reading port validates malformed values without exposing configuration.
        _ = url.port
    except (ValueError, TypeError):
        return {'enabled': False}
    return {'enabled': True, 'api_url': api_url, 'business_id': business_id}
