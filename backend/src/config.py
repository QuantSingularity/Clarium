from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = (
        "postgresql+asyncpg://clarium:clarium_secret@localhost:5432/clarium"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    secret_key: str = "change-me-in-production"
    environment: str = "development"
    log_level: str = "INFO"
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10

    # OCR
    ocr_service_url: str = "mock"
    ocr_confidence_threshold: float = 0.80

    # KYC scoring thresholds
    kyc_score_threshold_verified: float = 0.75
    kyc_score_threshold_review: float = 0.50

    # AML
    aml_amount_threshold: float = 10_000
    aml_velocity_window_minutes: int = 60
    aml_velocity_max_transactions: int = 10
    aml_high_risk_score: float = 0.70

    # Webhook
    webhook_max_retries: int = 3
    webhook_retry_backoff_seconds: int = 30
    webhook_timeout_seconds: int = 10

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Rules
    rules_dir: str = "./rules/jurisdictions"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
