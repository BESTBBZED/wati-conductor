"""Client factory for getting WATI client."""

from conductor.clients.mock import MockWATIClient
from conductor.clients.real import RealWATIClient
from conductor.config import settings


def get_wati_client():
    """Get WATI client based on configuration."""
    if settings.use_mock:
        return MockWATIClient()
    else:
        if not settings.wati_api_endpoint or not settings.wati_token:
            raise ValueError("WATI_API_ENDPOINT and WATI_TOKEN must be set when USE_MOCK=false")
        return RealWATIClient(settings.wati_api_endpoint, settings.wati_token)
