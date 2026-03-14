"""
DiaIntel — Application Configuration
Loads environment variables and provides typed settings via Pydantic.
"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://diaintel:diaintel_pass@postgres:5432/diaintel"
    POSTGRES_USER: str = "diaintel"
    POSTGRES_PASSWORD: str = "diaintel_pass"
    POSTGRES_DB: str = "diaintel"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_CACHE_TTL: int = 300

    # Models
    MODEL_CACHE_DIR: str = "/models"
    BIOBERT_MODEL: str = "dmis-lab/biobert-base-cased-v1.2"
    DISTILBERT_MODEL: str = "distilbert-base-uncased"
    ROBERTA_MODEL: str = "cardiffnlp/twitter-roberta-base-sentiment"
    BART_MODEL: str = "facebook/bart-large-mnli"

    # Data
    PUSHSHIFT_DATA_DIR: str = "/app/data/raw"

    # App
    APP_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173"

    # Processing
    BATCH_SIZE: int = 1000
    MIN_POST_LENGTH: int = 20

    class Config:
        env_file = ".env.example"
        case_sensitive = True


# Singleton settings instance
settings = Settings()
