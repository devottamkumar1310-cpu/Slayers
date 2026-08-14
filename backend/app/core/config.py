import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SLAYERS"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    DATABASE_URL: str = "sqlite:///./slayers.db"
    FRONTEND_URL: str = ""
    PORT: int = 8000
    
    # Provider keys
    AI_PROVIDER: str = "auto"  # 'gemini', 'openai', or 'heuristic'
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    PEXELS_API_KEY: str = ""
    UNSPLASH_ACCESS_KEY: str = ""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
