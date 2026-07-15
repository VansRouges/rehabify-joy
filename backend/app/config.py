from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/joy"
    database_public_url: str = ""
    redis_url: str = "redis://localhost:6379/0"

    # Accept our names and Railway's native bucket variable names
    bucket_name: str = Field(
        default="",
        validation_alias=AliasChoices("BUCKET_NAME", "BUCKET", "AWS_S3_BUCKET_NAME"),
    )
    bucket_access_key: str = Field(
        default="",
        validation_alias=AliasChoices("BUCKET_ACCESS_KEY", "ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID"),
    )
    bucket_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("BUCKET_SECRET_KEY", "SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY"),
    )
    bucket_endpoint: str = Field(
        default="",
        validation_alias=AliasChoices("BUCKET_ENDPOINT", "ENDPOINT", "AWS_ENDPOINT_URL"),
    )
    bucket_region: str = Field(
        default="auto",
        validation_alias=AliasChoices("BUCKET_REGION", "REGION", "AWS_DEFAULT_REGION"),
    )

    app_env: str = "development"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    sync_db_on_startup: bool = False

    session_ttl_seconds: int = 86400
    max_history_turns: int = 15
    max_voice_seconds: int = 60

    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_business_account_id: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_graph_api_version: str = "v25.0"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_database_url(self) -> str:
        """Local dev uses the public Railway proxy; production uses the internal URL."""
        if self.app_env == "development" and self.database_public_url:
            return self.database_public_url
        return self.database_url

    @property
    def whatsapp_configured(self) -> bool:
        return bool(
            self.whatsapp_access_token
            and self.whatsapp_phone_number_id
            and self.whatsapp_verify_token
        )

    @property
    def bucket_configured(self) -> bool:
        return bool(
            self.bucket_name
            and self.bucket_access_key
            and self.bucket_secret_key
            and self.bucket_endpoint
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
