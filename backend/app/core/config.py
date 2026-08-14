import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "SLAYERS"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "sqlite:///./slayers.db"

    # Server
    PORT: int = 8000
    FRONTEND_URL: str = ""

    # AI provider: 'gemini', 'openai', 'heuristic', or 'auto'
    AI_PROVIDER: str = "auto"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Asset provider keys
    PEXELS_API_KEY: str = ""
    UNSPLASH_ACCESS_KEY: str = ""

    # Pipeline limits
    PROVIDER_TIMEOUT_SECONDS: float = 10.0
    MAX_PROVIDER_RESULTS: int = 4
    MAX_SEGMENTS: int = 50
    MAX_ASSETS_PER_REQUIREMENT: int = 6
    MAX_SOURCE_TEXT_LENGTH: int = 20000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
