from functools import lru_cache
from typing import Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # Fallback for Pydantic v1
    from pydantic import BaseSettings, Extra  # type: ignore
    SettingsConfigDict = None  # type: ignore


class Settings(BaseSettings):
    PROJECT_NAME: str = "document-intelligence-service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database & Cache
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/document_intelligence"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    JWT_SECRET: str = "supersecretjwtkey_replace_with_strong_random_secret_in_prod_32chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # OCR / LLM Configuration
    OCR_API_KEY: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "openai"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            case_sensitive=True,
        )
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = Extra.ignore
            case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
