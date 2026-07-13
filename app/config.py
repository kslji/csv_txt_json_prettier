from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FMT_", extra="ignore")

    app_name: str = "Format Prettify API"
    version: str = "1.0.0"
    environment: str = "production"

    cors_origins: str = "*"
    rate_limit: str = "60/minute"
    max_input_mb: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
