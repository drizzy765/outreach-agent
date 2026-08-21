from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(default="postgresql+asyncpg://outreach_user:outreach_password@localhost:5432/outreach_crm")
    database_sync_url: str = Field(default="postgresql://outreach_user:outreach_password@localhost:5432/outreach_crm")

    # LLM Settings
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    default_llm_provider: str = "openai"
    default_model: str = "gpt-4o"

    # Telegram Bot
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # SMTP / Outbound Email
    outbound_secondary_domain: str = "yourname-labs.com"
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    daily_email_limit: int = 25

    # IMAP / Incoming Monitoring
    imap_host: Optional[str] = None
    imap_port: int = 993
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None

    # Negotiation Guardrails
    minimum_acceptable_rate_hourly: float = 150.0
    minimum_acceptable_fixed_project: float = 5000.0
    max_discount_percentage: float = 10.0
    milestone_terms: str = "50% upfront deposit, 50% upon milestone completion and deployment"

settings = Settings()
