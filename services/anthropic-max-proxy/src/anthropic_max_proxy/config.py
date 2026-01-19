"""Configuration for Anthropic MAX proxy."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Proxy configuration loaded from environment."""

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8100, description="Server bind port")

    # Anthropic OAuth settings (public client ID from opencode)
    anthropic_client_id: str = Field(
        default="9d1c250a-e61b-44d9-88ed-5944d1962f5e",
        description="Anthropic OAuth client ID",
    )
    anthropic_oauth_url: str = Field(
        default="https://claude.ai/oauth/authorize",
        description="Anthropic OAuth authorization URL",
    )
    anthropic_token_url: str = Field(
        default="https://console.anthropic.com/v1/oauth/token",
        description="Anthropic OAuth token exchange URL",
    )
    anthropic_api_url: str = Field(
        default="https://api.anthropic.com/v1",
        description="Anthropic API base URL",
    )

    # Token storage
    token_file: Path = Field(
        default=Path.home() / ".config" / "anthropic-max-proxy" / "tokens.json",
        description="Path to store OAuth tokens",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    model_config = {"env_prefix": "ANTHROPIC_PROXY_"}


settings = Settings()
