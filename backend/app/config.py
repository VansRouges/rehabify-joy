from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/joy"
    database_public_url: str = ""
    redis_url: str = "redis://localhost:6379/0"

    app_env: str = "development"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    session_ttl_seconds: int = 86400
    max_history_turns: int = 15

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_database_url(self) -> str:
        """Use public Railway URL locally; internal hostname only works inside Railway."""
        if self.database_public_url and (
            self.app_env == "development" or ".railway.internal" in self.database_url
        ):
            return self.database_public_url
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
