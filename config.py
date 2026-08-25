from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(default="postgresql+asyncpg://outreach_user:outreach_password@localhost:5432/outreach_crm")
    database_sync_url: str = Field(default="postgresql://outreach_user:outreach_password@localhost:5432/outreach_crm")

    # Free-Tier & Multi-Model LLM Providers
    openrouter_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434/v1"
    custom_llm_base_url: Optional[str] = None
    custom_llm_api_key: Optional[str] = None

    # Legacy / Commercial Keys (Optional fallbacks)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Routing preferences
    default_llm_provider: str = "groq"
    default_free_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    default_groq_model: str = "llama-3.1-8b-instant"
    default_nvidia_model: str = "meta/llama-3.3-70b-instruct"
    default_gemini_model: str = "gemini-1.5-flash"

    # Sender Profile (AI/ML Engineer)
    sender_name: str = "Timilehin Agoro"
    sender_title: str = "AI / ML Engineer"
    sender_resume_url: Optional[str] = "https://linkedin.com/in/timilehin-agoro"
    sender_portfolio_url: Optional[str] = "https://github.com/drizzy765"

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

    # Invoicing & Webhooks
    invoicing_webhook_url: Optional[str] = None

    # Background Scheduler
    scheduler_discovery_interval_hours: int = 24
    scheduler_inbox_interval_minutes: int = 15
    scheduler_followup_days_threshold: int = 3

settings = Settings()


