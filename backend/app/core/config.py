"""
Application Configuration
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import secrets


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """

    # Application
    APP_NAME: str = "SecDash"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "secdash"
    POSTGRES_USER: str = "secdash_user"
    POSTGRES_PASSWORD: str = "changeme"
    DATABASE_URL: Optional[str] = None

    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v, values):
        if isinstance(v, str):
            return v
        return (
            f"postgresql://{values.get('POSTGRES_USER')}:"
            f"{values.get('POSTGRES_PASSWORD')}@"
            f"{values.get('POSTGRES_HOST')}:"
            f"{values.get('POSTGRES_PORT')}/"
            f"{values.get('POSTGRES_DB')}"
        )

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "changeme"
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    @validator("REDIS_URL", pre=True)
    def assemble_redis_connection(cls, v, values):
        if isinstance(v, str):
            return v
        return (
            f"redis://:{values.get('REDIS_PASSWORD')}@"
            f"{values.get('REDIS_HOST')}:"
            f"{values.get('REDIS_PORT')}/"
            f"{values.get('REDIS_DB')}"
        )

    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_ALWAYS_EAGER: bool = False

    @validator("CELERY_BROKER_URL", pre=True)
    def set_celery_broker(cls, v, values):
        return v or values.get("REDIS_URL")

    @validator("CELERY_RESULT_BACKEND", pre=True)
    def set_celery_backend(cls, v, values):
        return v or values.get("REDIS_URL")

    # GitHub
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: Optional[str] = None

    # GitLab
    GITLAB_TOKEN: Optional[str] = None
    GITLAB_URL: str = "https://gitlab.com"
    GITLAB_WEBHOOK_SECRET: Optional[str] = None

    # Ollama
    OLLAMA_HOST: str = "http://ollama:11434"
    OLLAMA_MODEL_SUMMARY: str = "llama3.2"
    OLLAMA_MODEL_CODE: str = "codellama"
    OLLAMA_MODEL_ADVANCED: str = "deepseek-coder"
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_ENABLED: bool = True

    # Notifications
    SLACK_WEBHOOK_URL: Optional[str] = None
    SLACK_ENABLED: bool = False

    DISCORD_WEBHOOK_URL: Optional[str] = None
    DISCORD_ENABLED: bool = False

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: str = "SecDash"
    EMAIL_ENABLED: bool = False

    # Scanner Configuration
    SEMGREP_RULES: str = "auto"
    TRIVY_SEVERITY: str = "HIGH,CRITICAL"
    SCAN_TIMEOUT: int = 3600
    MAX_PARALLEL_SCANS: int = 3

    # Storage
    TEMP_REPO_DIR: str = "/tmp/secdash_repos"
    SCAN_RESULTS_DIR: str = "/app/scan_results"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_ENABLED: bool = True

    # Monitoring
    PROMETHEUS_ENABLED: bool = False
    GRAFANA_ENABLED: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
