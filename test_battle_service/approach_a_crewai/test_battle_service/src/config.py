"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """JWT Auth Microservice settings.

    JWT_SECRET has no default — the application will crash at startup
    if the environment variable is not set, preventing accidental
    deployment with an insecure key.
    """

    JWT_SECRET: str  # Required — no default; crashes if unset
    DATABASE_URL: str = "sqlite+aiosqlite:///data.db"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
