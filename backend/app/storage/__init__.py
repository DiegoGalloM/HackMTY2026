from functools import lru_cache

from app.config import get_settings
from app.storage.base import ProfileStore
from app.storage.memory_store import MemoryProfileStore


@lru_cache
def get_store() -> ProfileStore:
    settings = get_settings()
    if settings.use_snowflake and settings.snowflake_account:
        from app.storage.snowflake_store import SnowflakeProfileStore

        return SnowflakeProfileStore(settings)
    return MemoryProfileStore()