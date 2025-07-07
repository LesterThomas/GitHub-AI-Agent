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
    github_token: Optional[str] = Field(
        default=None,
        description="GitHub API token for human user (used by reset script)",
    )
    github_ai_agent_token: Optional[str] = Field(
        default=None,
        description="GitHub personal access token for AI Agent persona",
    )
    target_owner: str = Field(
        default="LesterThomas", description="Target repository owner"
    )
    target_repo: str = Field(default="SAAA", description="Target repository name")
    issue_assignee: str = Field(
        default="Test-AI-Agent",
        description="GitHub username to filter issues by assignee",
    )

    # OpenAI settings
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")

    # Agent settings
    poll_interval: int = Field(default=300, description="Polling interval in seconds")
    max_iterations: int = Field(default=20, description="Maximum agent iterations")
    recursion_limit: int = Field(
        default=50, description="Maximum recursion limit for LangGraph agent"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
