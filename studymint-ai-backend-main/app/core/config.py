from functools import cached_property
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "StudyMint AI"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    DATABASE_URL: str = "postgresql+psycopg://studymint:studymint@localhost:55432/studymint"
    BACKEND_CORS_ORIGINS: str = "http://127.0.0.1:5173,http://localhost:5173"
    BACKEND_CORS_ORIGIN_REGEX: str = r"^https?://(localhost|127[.]0[.]0[.]1):[0-9]+$"
    BACKEND_PUBLIC_URL: str = "http://127.0.0.1:8000"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1"
    OPENAI_MEDIUM_MODEL: str = "gpt-4.1"
    OPENAI_FAST_MODEL: str = "gpt-4.1-mini"
    OPENAI_DOCUMENT_MODEL: str = "gpt-4.1-nano"
    OPENAI_GUARDRAIL_MODEL: str = "gpt-4.1-mini"
    OPENAI_GUARDRAIL_MAX_OUTPUT_TOKENS: int = 12000
    OPENAI_ENABLE_REASONING: bool = False
    OPENAI_REASONING_EFFORT: str = "low"
    OPENAI_TEXT_VERBOSITY: str = "medium"
    OPENAI_API_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_TIMEOUT_SECONDS: int = 180
    OPENAI_MAX_OUTPUT_TOKENS: int = 12000
    OPENAI_MAX_RETRIES: int = 3
    OPENAI_RETRY_BACKOFF_SECONDS: float = 2.0
    OPENAI_QUESTION_BATCH_SIZE: int = 25
    OPENAI_QUESTION_BATCH_ATTEMPTS: int = 1
    OPENAI_BLUEPRINT_MAX_OUTPUT_TOKENS: int = 5000
    OPENAI_QUESTION_BATCH_MAX_OUTPUT_TOKENS: int = 14000
    STUVIA_AGENT_DEFAULT_PROFILE_URL: str = "https://www.stuvia.com/user/casewritters"
    STUVIA_SCRAPE_TIMEOUT_SECONDS: int = 15
    STUVIA_SCRAPE_PAGE_LIMIT: int = 14
    STUVIA_AGENT_MAX_CONCURRENCY: int = 10
    STUVIA_AGENT_GENERATION_ATTEMPTS: int = 3
    STUVIA_AGENT_RECOVERY_CONCURRENCY: int = 1
    STUVIA_AGENT_RETRY_BACKOFF_SECONDS: float = 2.0
    STUVIA_AGENT_USE_LLM_RANKER: bool = False
    STUVIA_AGENT_FAST_BATCH_SIZE: int = 30
    N8N_STUVIA_WEBHOOK_URL: str = ""
    N8N_STUVIA_WEBHOOK_TOKEN: str = ""
    N8N_STUVIA_WEBHOOK_TIMEOUT_SECONDS: int = 45
    STUVIA_BROWSER_PUBLISHER_URL: str = ""
    PDF_EXPORT_BASE_URL: str = "/exports"
    PDF_EXPORT_DIR: str = "exports"
    FRONTEND_PUBLIC_URL: str = "http://127.0.0.1:5173"
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "info@marketing.ainexis.tech"
    SMTP_FROM_NAME: str = "StudyMint AI"
    SMTP_USE_SSL: bool = True
    SMTP_USE_STARTTLS: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @cached_property
    def export_dir_path(self) -> Path:
        path = Path(self.PDF_EXPORT_DIR)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parents[2] / path


settings = Settings()
