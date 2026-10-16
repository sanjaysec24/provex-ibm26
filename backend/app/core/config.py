from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROVEX_ENV: str = "development"
    PROVEX_HOST: str = "127.0.0.1"
    PROVEX_PORT: int = 8000
    PROVEX_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    PROVEX_DATA_ADAPTER: str = "synthetic"
    PROVEX_AUDIT_ALGORITHM: str = "SHA256"
    PROVEX_AUDIT_SALT: str = "local-audit-salt-offline-only"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.PROVEX_CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
