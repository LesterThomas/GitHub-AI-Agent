# GitHub AI Agent

An AI Agent built with LanGraph ReAct pattern that polls GitHub issues with the "AI Agent" label and automatically generates pull requests with relevant content.

## Features

- **LanGraph ReAct Agent**: Uses LanGraph's pre-built ReAct agent for intelligent issue processing
- **GitHub Integration**: Polls for issues with specific labels and creates pull requests
- **Configurable**: Environment-based configuration for easy deployment
- **UV Package Manager**: Modern Python package management with UV
- **Type Safety**: Full type hints and Pydantic-based configuration

## Architecture

The agent follows LanGraph best practices and consists of:

1. **Configuration Management** (`config.py`): Pydantic-based settings
2. **GitHub Client** (`github_client.py`): GitHub API integration
3. **LanGraph Agent** (`agent.py`): ReAct agent for issue processing
4. **Main Application** (`main.py`): Orchestration and polling logic

## Requirements

- Python 3.12+
- UV package manager
- GitHub API token
- OpenAI API key

## Installation

1. **Install UV** (if not already installed):
   ```bash
   pip install uv
   ```

2. **Clone and setup the project**:
   ```bash
   git clone https://github.com/LesterThomas/GitHub-AI-Agent.git
   cd GitHub-AI-Agent
   uv sync
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys and settings
   ```

## Configuration

Create a `.env` file with the following variables:

```env
# GitHub Settings
GITHUB_TOKEN=your_github_token_here
TARGET_OWNER=LesterThomas
TARGET_REPO=SAAA
ISSUE_LABEL=AI Agent

# OpenAI Settings
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Agent Settings
POLL_INTERVAL=300
MAX_ITERATIONS=10

# Logging
LOG_LEVEL=INFO
```

### Required API Keys

1. **GitHub Token**: Create a personal access token with `repo` permissions
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a new token with repository access

2. **OpenAI API Key**: Get your API key from OpenAI
   - Visit https://platform.openai.com/api-keys
   - Create a new API key

## Usage

### Single Run
Process all current issues once:
```bash
uv run python main.py
```

### Daemon Mode
Run continuously, polling for new issues:
```bash
uv run python main.py --daemon
```

### Using the installed script
After installation, you can also use:
```bash
uv run github-ai-agent          # Single run
uv run github-ai-agent --daemon # Daemon mode
```

## How It Works

1. **Polling**: The agent polls the specified GitHub repository for issues with the configured label
2. **Processing**: For each new issue, the LanGraph ReAct agent:
   - Analyzes the issue requirements
   - Generates appropriate content based on the issue description
   - Validates the generated content
3. **Pull Request Creation**: 
   - Creates a new branch for the response
   - Commits the generated content to a file
   - Opens a pull request with the solution
   - Comments on the original issue with the PR link

## Agent Workflow

The LanGraph ReAct agent follows this workflow:

```
Issue Detection → Requirements Analysis → Content Generation → Validation → PR Creation
```

Each step uses specialized tools:
- `analyze_issue_requirements`: Parses and understands issue requirements
- `create_file_content`: Generates content based on requirements
- `validate_content`: Ensures content quality before PR creation

## Development

### Running Tests
```bash
uv run pytest
```

### Code Formatting
```bash
uv run black .
uv run isort .
```

### Type Checking
```bash
uv run mypy github_ai_agent
```

## Project Structure

```
github-ai-agent/
├── github_ai_agent/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── github_client.py   # GitHub API client
│   ├── agent.py          # LanGraph ReAct agent
│   └── main.py           # Main application logic
├── tests/
│   ├── __init__.py
│   └── test_basic.py     # Basic tests
├── main.py               # Entry point
├── pyproject.toml        # Project configuration
├── .env.example          # Example environment file
└── README.md
```

## LanGraph Best Practices

This implementation follows LanGraph best practices:

1. **State Management**: Uses typed state with `TypedDict`
2. **Tool Integration**: Defines clear, focused tools for the agent
3. **Memory**: Uses `MemorySaver` for conversation persistence
4. **Error Handling**: Comprehensive error handling throughout
5. **Modularity**: Clean separation between GitHub client and agent logic

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify your GitHub token has the correct permissions
2. **Rate Limiting**: GitHub API has rate limits; the agent includes error handling for this
3. **OpenAI Errors**: Ensure your OpenAI API key is valid and has sufficient credits

### Logging

The agent provides comprehensive logging. Set `LOG_LEVEL=DEBUG` in your `.env` file for detailed logs.

## Target Repository

This agent is designed to monitor the [LesterThomas/SAAA](https://github.com/LesterThomas/SAAA) repository for issues labeled "AI Agent" and automatically generate helpful responses.