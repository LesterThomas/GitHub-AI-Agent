"""Configuration management for the GitHub AI Agent."""

import os
from typing import Optional, Dict, Any

import yaml
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
    github_app_id: Optional[str] = Field(
        default=None,
        description="GitHub App ID for authentication",
    )
    github_app_private_key_file: Optional[str] = Field(
        default=None,
        description="Path to GitHub App private key file",
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


def load_prompts() -> Dict[str, Any]:
    """Load prompts from YAML configuration file."""
    # Get the directory containing this config.py file
    config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompts_file = os.path.join(config_dir, "prompts.yaml")

    try:
        with open(prompts_file, "r", encoding="utf-8") as f:
            prompts = yaml.safe_load(f)
        return prompts
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompts configuration file not found: {prompts_file}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in prompts configuration: {e}")


def get_system_prompt(target_owner: str, target_repo: str) -> str:
    """Get the system prompt with target repository information."""
    prompts = load_prompts()
    return prompts["system_prompt"].format(
        target_owner=target_owner, target_repo=target_repo
    )


def get_human_message_template(
    target_owner: str,
    target_repo: str,
    issue_number: int,
    issue_title: str,
    issue_description: str,
) -> str:
    """Get the human message template with issue information."""
    prompts = load_prompts()
    return prompts["human_message_template"].format(
        target_owner=target_owner,
        target_repo=target_repo,
        issue_number=issue_number,
        issue_title=issue_title,
        issue_description=issue_description,
    )


def get_tool_description(tool_name: str) -> str:
    """Get the description for a specific tool."""
    prompts = load_prompts()
    tool_descriptions = prompts.get("tool_descriptions", {})
    return tool_descriptions.get(tool_name, f"Tool: {tool_name}")
