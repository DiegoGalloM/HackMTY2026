"""
Configuración centralizada. Todo lo que cambia entre tu laptop, la de tu
compañero, y el servidor de demo debería vivir aquí — nunca hardcodeado en
el resto del código.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    nessie_api_key: str = ""
    nessie_base_url: str = "http://api.nessieisreal.com"
    use_mock_nessie: bool = True

    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    use_snowflake: bool = False
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_warehouse: str = ""
    snowflake_database: str = ""
    snowflake_schema: str = ""
    snowflake_role: str = ""

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    # lru_cache = se lee el .env una sola vez, no en cada request.
    return Settings()
