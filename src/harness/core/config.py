from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class HarnessSettings(BaseSettings):
    """Central configuration for Regulated Agent Harness."""

    environment: str = Field(default="development", description="Deployment environment")
    primary_model: str = Field(default="azure/gpt-4o", description="Primary model name for LiteLLM")
    fallback_models: list[str] = Field(
        default_factory=lambda: ["bedrock/anthropic.claude-3-5-sonnet"],
        description="Fallback models for failover",
    )
    max_retries: int = Field(default=3, ge=1, description="Max model retries on transient errors")
    backoff_factor: float = Field(
        default=1.5, ge=0.01, description="Exponential backoff base factor"
    )
    request_timeout: float = Field(
        default=60.0, ge=1.0, description="Model request timeout in seconds"
    )

    # Checkpointer & Persistence
    checkpointer_type: str = Field(
        default="sqlite", description="Checkpointer type: sqlite or postgres"
    )
    database_url: str = Field(
        default="sqlite+aiosqlite:///./.harness_checkpoints.db",
        description="Database connection URL",
    )

    # Observability & Langfuse
    langfuse_host: str = Field(default="http://localhost:3000", description="Langfuse host URL")
    langfuse_public_key: str | None = Field(default=None, description="Langfuse public key")
    langfuse_secret_key: str | None = Field(default=None, description="Langfuse secret key")

    # Guardrails & Budgets
    max_session_cost_usd: float = Field(
        default=0.50, ge=0.01, description="Maximum session cost in USD"
    )
    max_iterations: int = Field(default=10, ge=1, description="Maximum loop iterations per session")
    redact_pii: bool = Field(default=True, description="Enable automatic PII/PHI redaction")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = HarnessSettings()
