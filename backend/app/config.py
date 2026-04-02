from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/clipbandit"
    database_sync_url: str = "postgresql://postgres:postgres@localhost:5432/clipbandit"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "clipbandit"

    # Redis + Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Auth
    nextauth_secret: str = "changeme"
    nextauth_url: str = "http://localhost:3001"
    admin_email: str = "admin@clipbandit.com"
    admin_password: str = "changeme123"

    # JWT
    jwt_secret_key: str = "changeme-jwt-secret-key-32-chars-min"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # Cloudflare R2
    r2_account_id: str = "placeholder"
    r2_access_key_id: str = "placeholder"
    r2_secret_access_key: str = "placeholder"
    r2_bucket_name: str = "clipbandit"
    r2_endpoint_url: str = "https://placeholder.r2.cloudflarestorage.com"
    r2_public_url: str = "placeholder"

    # Anthropic
    anthropic_api_key: str = "placeholder"

    # App
    environment: str = "development"
    log_level: str = "INFO"
    max_upload_size_mb: int = 5000
    max_concurrent_jobs: int = 2

    # Transcription
    whisper_model_size: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_download_root: str = "/tmp/whisper-models"
    whisper_num_workers: int = 2
    whisper_beam_size: int = 1
    whisper_best_of: int = 1
    whisper_condition_on_previous_text: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
