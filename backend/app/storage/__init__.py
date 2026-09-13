from functools import lru_cache

from app.config import get_settings
from app.storage.base import ProfileStore, UserStore
from app.storage.memory_store import MemoryProfileStore, MemoryUserStore


@lru_cache
def get_store() -> ProfileStore:
    settings = get_settings()
    if settings.use_snowflake and settings.snowflake_account:
        from app.storage.snowflake_store import SnowflakeProfileStore

        return SnowflakeProfileStore(settings)
    return MemoryProfileStore()


@lru_cache
def get_user_store() -> UserStore:
    # Mismo criterio que get_store(): si no hay cuenta de Snowflake configurada
    # se cae a memoria, así el equipo puede desarrollar y demostrar sin
    # credenciales (los usuarios se pierden al reiniciar, pero nada truena).
    settings = get_settings()
    if settings.use_snowflake and settings.snowflake_account:
        from app.storage.snowflake_store import SnowflakeUserStore

        return SnowflakeUserStore(settings)
    return MemoryUserStore()
