from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MatchMind"
    DEBUG: bool = False
    SECRET_KEY: str = "changeme-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALLOWED_ORIGINS: str = "http://localhost:3000"  # comma-separated for multiple origins

    # Clerk auth
    CLERK_SECRET_KEY: str = ""
    CLERK_ISSUER: str = ""
    CLERK_JWKS_URL: str = ""
    CLERK_AUDIENCE: str = ""
    CLERK_JWT_TEMPLATE: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/matchmaking"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # LLM — set LLM_PROVIDER to: groq | openai | anthropic | gemini
    LLM_PROVIDER: str = "groq"

    # Groq (default)
    GROQ_API_KEY: str = ""
    GROQ_CHAT_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_EXTRACTION_MODEL: str = "llama-3.3-70b-versatile"

    OPENAI_API_KEY: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o"
    OPENAI_EXTRACTION_MODEL: str = "gpt-4o"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_CHAT_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_EXTRACTION_MODEL: str = "claude-3-5-sonnet-20241022"

    GEMINI_API_KEY: str = ""
    GEMINI_CHAT_MODEL: str = "gemini-1.5-pro"
    GEMINI_EXTRACTION_MODEL: str = "gemini-1.5-pro"

    # Embeddings
    # EMBEDDING_PROVIDER: huggingface | lmstudio | openai | none
    EMBEDDING_PROVIDER: str = "huggingface"
    
    HUGGINGFACE_API_KEY: str = ""
    HUGGINGFACE_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    LMSTUDIO_BASE_URL: str = "http://127.0.0.1:1234/v1"
    LMSTUDIO_EMBEDDING_MODEL: str = "text-embedding-bge-small-en-v1.5"

    EMBEDDING_MODEL: str = "text-embedding-bge-small-en-v1.5"  # used for openai fallback
    EMBEDDING_DIM: int = 384   # bge-small-en-v1.5 output dimension

    # SendGrid
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "mm0177@srmist.edu.in"
    EMAIL_FROM_NAME: str = "MatchMind"

    # Matching
    MIN_DAYS_FOR_MATCHING: int = 7
    MIN_PERSONA_CONFIDENCE: float = 0.5
    MIN_MATCH_SCORE: float = 0.60

    # Chat limits — how many user messages are allowed per day before the session closes
    MAX_EXCHANGES_PER_DAY: int = 12

    # Dev/testing — set DEV_MODE=false in production
    DEV_MODE: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
