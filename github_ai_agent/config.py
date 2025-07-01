"""Configuration management for the GitHub AI Agent."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # GitHub settings
    github_token: str = Field(..., description="GitHub API token")
    target_owner: str = Field(
        default="LesterThomas", description="Target repository owner"
    )
    target_repo: str = Field(default="SAAA", description="Target repository name")
    issue_label: str = Field(default="AI Agent", description="Label to filter issues")

    # OpenAI settings
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model to use")

    # Agent settings
    poll_interval: int = Field(default=300, description="Polling interval in seconds")
    max_iterations: int = Field(default=10, description="Maximum agent iterations")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
