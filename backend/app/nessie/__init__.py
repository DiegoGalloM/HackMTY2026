from functools import lru_cache

from app.config import get_settings
from app.nessie.base import NessieClient
from app.nessie.mock_client import MockNessieClient
from app.nessie.real_client import RealNessieClient


@lru_cache
def get_nessie_client() -> NessieClient:
    settings = get_settings()
    if settings.use_mock_nessie or not settings.nessie_api_key:
        return MockNessieClient()
    return RealNessieClient(base_url=settings.nessie_base_url, api_key=settings.nessie_api_key)
