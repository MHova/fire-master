from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://firemaster:firemaster@localhost:5432/firemaster"
    DATABASE_URL_SYNC: str = "postgresql://firemaster:firemaster@localhost:5432/firemaster"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60
    AUTH_USERNAME: str = "admin"
    AUTH_PASSWORD_HASH: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Anthropic (AI Advisor)
    ANTHROPIC_API_KEY: str = ""

    # Monarch
    MONARCH_SESSION_FILE: str = ".monarch_session"

    # App
    APP_ENV: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
