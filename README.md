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

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | *required* | GitHub personal access token with repo permissions |
| `TARGET_OWNER` | `LesterThomas` | Owner of the target repository where files are created |
| `TARGET_REPO` | `SAAA` | Name of the target repository for file creation |
| `ISSUE_LABEL` | `AI Agent` | Label to filter issues for processing |
| `OPENAI_API_KEY` | *required* | OpenAI API key for LLM access |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use (gpt-4, gpt-4o-mini, etc.) |
| `POLL_INTERVAL` | `300` | Polling interval in seconds (5 minutes) |
| `MAX_ITERATIONS` | `20` | Maximum ReAct agent iterations |
| `RECURSION_LIMIT` | `50` | Maximum LanGraph recursion limit |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Agent Configuration

The agent can be configured for different scenarios:

```python
# High-frequency polling for development
POLL_INTERVAL=60  # 1 minute

# Production stability settings
MAX_ITERATIONS=20
RECURSION_LIMIT=50

# Debug mode with verbose logging
LOG_LEVEL=DEBUG
```

### API Key Setup

#### GitHub Token
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `repo` permissions
3. Add to `.env` as `GITHUB_TOKEN=your_token_here`

#### OpenAI API Key
1. Visit https://platform.openai.com/api-keys
2. Create a new API key
3. Add to `.env` as `OPENAI_API_KEY=your_key_here`

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

## Example Usage Patterns

### Issue Examples

The agent can process various types of file creation requests:

#### 1. Simple File Creation
**Issue**: "Create a new file TEST.md and write in it 'this is a test'"

**Agent Response**:
```json
[{
  "filename": "TEST.md",
  "file_content": "this is a test"
}]
```

#### 2. Multiple Files
**Issue**: "Create README.md with project info and setup.py with basic configuration"

**Agent Response**:
```json
[
  {
    "filename": "README.md",
    "file_content": "# Project\n\nProject information here..."
  },
  {
    "filename": "setup.py", 
    "file_content": "from setuptools import setup\n\nsetup(...)..."
  }
]
```

#### 3. Structured Content
**Issue**: "Create a file describing Cardiff with sections about history, attractions, and demographics"

**Agent Response**: Creates a well-structured markdown file with appropriate sections and content.

### Workflow Example

1. **Create Issue**: Add issue with "AI Agent" label in source repository
2. **Agent Detection**: Agent polls and detects new issue within 5 minutes
3. **Branch Creation**: Immediately creates `ai-agent/issue-123` in SAAA repository
4. **Processing**: ReAct agent analyzes and creates file specification
5. **File Creation**: Commits requested files to the existing branch
6. **PR Creation**: Opens pull request with metadata and links
7. **Issue Update**: Comments on original issue with PR link

## How It Works

The agent operates across two repositories:

1. **Source Repository**: Where issues are created and monitored
2. **Target Repository**: SAAA repository where files are created and PRs are made

### Processing Flow

1. **Issue Detection**: Continuously polls the source repository for issues labeled "AI Agent"
2. **Branch Creation**: Immediately creates a feature branch in the SAAA repository
3. **Content Analysis**: The LanGraph ReAct agent analyzes the issue using the system prompt
4. **File Specification**: Agent uses the `create_files_from_request` tool to specify files
5. **File Creation**: Commits the specified files to the pre-created feature branch
6. **Pull Request**: Opens a PR in SAAA repository linking back to the original issue
7. **Issue Update**: Comments on the original issue with the PR link

### Agent State Management

The agent maintains state using LanGraph's `AgentState`:

```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]  # Conversation history
    issue_data: Dict[str, Any]                            # Issue metadata
    generated_content: Optional[str]                      # Generated content
    branch_name: Optional[str]                            # Feature branch name
    pr_created: bool                                      # PR creation status
```

### Logging and Monitoring

The agent provides comprehensive logging with:
- **Color-coded output** for different action types (Agent, LLM, Tool, Error)
- **State tracking** at each step of the workflow
- **Tool usage logging** with input/output capture
- **Error handling** with detailed error messages and recovery strategies

## Agent Design and Workflow

### System Architecture

The agent uses LanGraph's ReAct (Reasoning and Acting) pattern with the following components:

1. **LanGraph ReAct Agent**: Pre-built agent that combines reasoning with tool usage
2. **Single Tool Design**: Focused on file creation using one specialized tool
3. **State Management**: Typed state management with conversation persistence
4. **Enhanced Logging**: Comprehensive logging with color-coded output for debugging

### System Prompt

The agent uses this system prompt to guide its behavior:

```
You are an AI agent that processes GitHub issues to create the exact files requested.

Your task is simple:
1. Analyze the GitHub issue to identify what files need to be created and their content
2. Use create_files_from_request with a JSON array of file objects to create the files
3. Respond with a summary of what was created

For an issue like "Create a new file TEST.md and write in it 'this is a test'":
- Call create_files_from_request with: [{"filename": "TEST.md", "file_content": "this is a test"}]

For multiple files, include all in one call:
- [{"filename": "file1.md", "file_content": "content1"}, {"filename": "file2.txt", "file_content": "content2"}]

Be direct and focused. Use only the create_files_from_request tool with properly formatted JSON.

Available tools:
- create_files_from_request: Takes JSON array of file objects with filename and file_content properties

Target repository: {target_owner}/{target_repo}
```

### Tool Description

The agent has access to one specialized tool:

#### `create_files_from_request`

**Purpose**: Create files from a JSON array of file objects

**Input Format**:
```json
[
  {
    "filename": "test.md", 
    "file_content": "# Test File\n\nThis is a test file content."
  },
  {
    "filename": "readme.txt",
    "file_content": "This is a readme file."
  }
]
```

**Output**: JSON object with prepared files ready for GitHub creation
```json
{
  "success": true,
  "files": [
    {
      "filename": "test.md",
      "content": "# Test File\n\nThis is a test file content.",
      "path": "test.md",
      "message": "Create test.md as requested"
    }
  ],
  "count": 1
}
```

**Description**: "Create files from a JSON array of file objects. Each object must have 'filename' and 'file_content' properties. Returns a JSON object with the prepared files ready for GitHub creation."

### Complete Workflow

The agent follows this detailed workflow from GitHub issue polling to PR creation:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   1. POLLING    │ -> │  2. ISSUE FETCH  │ -> │ 3. BRANCH       │
│                 │    │                  │    │    CREATION     │
│ • Poll GitHub   │    │ • Get issue data │    │                 │
│   repository    │    │ • Extract title  │    │ • Create        │
│ • Filter by     │    │ • Extract body   │    │   feature       │
│   "AI Agent"    │    │ • Get metadata   │    │   branch        │
│   label         │    │                  │    │ • ai-agent/     │
│                 │    │                  │    │   issue-{num}   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         |                       |                       |
         v                       v                       v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ 4. AGENT SETUP  │ -> │ 5. REACT AGENT   │ -> │ 6. TOOL         │
│                 │    │                  │    │    EXECUTION    │
│ • Create system │    │ • LLM reasoning  │    │                 │
│   message       │    │ • Plan actions   │    │ • Execute       │
│ • Create human  │    │ • Generate tool  │    │   create_files_ │
│   message       │    │   calls          │    │   from_request  │
│ • Set up state  │    │                  │    │ • Validate JSON │
│                 │    │                  │    │ • Return results│
└─────────────────┘    └──────────────────┘    └─────────────────┘
         |                       |                       |
         v                       v                       v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ 7. PARSE RESULT │ -> │ 8. FILE CREATION │ -> │ 9. PULL REQUEST │
│                 │    │                  │    │                 │
│ • Extract files │    │ • Create files   │    │ • Create PR     │
│   from tool     │    │   in SAAA repo   │    │   in SAAA repo  │
│   output        │    │ • Commit to      │    │ • Link to issue │
│ • Prepare for   │    │   existing       │    │ • Add metadata  │
│   GitHub API    │    │   branch         │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         |                       |                       |
         v                       v                       v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ 10. ISSUE       │ -> │ 11. LOGGING &    │ -> │ 12. COMPLETION  │
│     COMMENT     │    │     TRACKING     │    │                 │
│                 │    │                  │    │ • Mark issue    │
│ • Add comment   │    │ • Color-coded    │    │   as processed  │
│   with PR link  │    │   console logs   │    │ • Return        │
│ • Close or      │    │ • State tracking │    │   success       │
│   reference     │    │ • Error handling │    │   status        │
│   issue         │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Detailed Step Breakdown

#### 1-3. Polling, Issue Detection & Branch Creation
- **Frequency**: Every 5 minutes (configurable via `POLL_INTERVAL`)
- **Filter**: Issues with "AI Agent" label in the configured repository
- **State**: Tracks processed issues to avoid duplication
- **Early Branch**: Creates feature branch immediately upon issue detection

#### 4-6. Agent Initialization, Reasoning & Tool Execution
- **LLM Model**: GPT-4 (configurable via `OPENAI_MODEL`)
- **ReAct Pattern**: Uses LanGraph's built-in ReAct agent
- **Reasoning**: Analyzes issue requirements and plans file creation
- **Single Tool**: `create_files_from_request` for focused file creation
- **JSON Validation**: Ensures proper format for file specifications

#### 7-9. File Operations & Pull Request Creation
- **Target Repository**: SAAA repository (separate from issue source)
- **Branch Strategy**: Uses pre-created feature branch `ai-agent/issue-{number}`
- **File Creation**: Direct API calls to GitHub for file commits
- **PR Creation**: Automated pull request with detailed metadata
- **Error Handling**: Comprehensive error handling with fallbacks

#### 10-12. Issue Management & Completion
- **Issue Linking**: Comments on original issue with PR link
- **Status Tracking**: Maintains processed issue list
- **Logging**: Comprehensive state logging for debugging and monitoring

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
GitHub-AI-Agent/
├── github_ai_agent/           # Main package
│   ├── __init__.py
│   ├── agent.py              # LanGraph ReAct agent implementation
│   ├── config.py             # Pydantic settings management
│   ├── github_client.py      # GitHub API integration
│   └── main.py               # Application orchestration
├── tests/                    # Test suite
│   ├── __init__.py
│   └── test_basic.py
├── main.py                   # CLI entry point
├── pyproject.toml            # Project configuration & dependencies
├── uv.lock                   # Dependency lock file
├── .env.example              # Environment template
├── README.md                 # This file
└── LICENSE                   # Apache 2.0 license
```

### Key Files

- **`agent.py`**: Contains the `GitHubIssueAgent` class with ReAct implementation
- **`github_client.py`**: Handles all GitHub API operations (issues, PRs, files)
- **`config.py`**: Pydantic-based configuration with environment variable loading
- **`main.py`**: Application entry point with daemon and single-run modes

## LanGraph Implementation Details

This implementation follows LanGraph best practices:

### 1. **ReAct Agent Pattern**
- Uses LanGraph's pre-built `create_react_agent` for reasoning and acting
- Single-tool design for focused file creation capabilities
- Memory persistence with `MemorySaver` for conversation context

### 2. **State Management**
```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    issue_data: Dict[str, Any]
    generated_content: Optional[str]
    branch_name: Optional[str]
    pr_created: bool
```

### 3. **Tool Definition**
The agent uses a single, focused tool:
```python
Tool(
    name="create_files_from_request",
    description="Create files from a JSON array of file objects...",
    func=create_files_from_request,
)
```

### 4. **Error Handling & Streaming**
- Comprehensive error handling with fallback strategies
- Stream execution with multiple modes: `["values", "updates", "debug"]`
- State logging at each execution step

### 5. **LLM Integration**
- Custom `LoggingLLM` wrapper for enhanced request/response logging
- Configurable models (default: GPT-4)
- Temperature set to 0.1 for consistent outputs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Debugging and Monitoring

### Log Output Format

The agent provides color-coded logging for easy monitoring:

- **🔵 AGENT**: Agent actions and state changes
- **🟢 LLM**: LLM requests and responses  
- **🟣 TOOL**: Tool executions with input/output
- **🔴 ERROR**: Error conditions and exceptions
- **🟡 WARNING**: Warning messages
- **🟦 INFO**: General information

### Debug Mode

Enable debug logging for detailed execution tracking:

```bash
# Set in .env file
LOG_LEVEL=DEBUG

# Run with enhanced logging
uv run python main.py
```

Debug mode provides:
- Complete message history
- State transitions at each step
- Tool execution details
- LLM token usage
- GitHub API call logs

### Monitoring Checklist

For production deployment, monitor:

1. **Issue Processing Rate**: Number of issues processed per hour
2. **Error Rates**: Failed processing attempts and their causes
3. **API Limits**: GitHub and OpenAI API usage and rate limits
4. **Branch Creation**: Successful feature branch creation in target repo
5. **PR Success**: Pull request creation and merge rates

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Authentication errors | Invalid GitHub token | Regenerate token with repo permissions |
| Rate limiting | Too frequent API calls | Increase `POLL_INTERVAL` |
| OpenAI errors | Invalid API key or quota | Check API key and billing |
| Branch creation failed | Permission issues | Ensure token has write access to target repo |
| File creation failed | Path or content issues | Check file paths and content format |

## Target Repository

This agent is designed to monitor the [LesterThomas/SAAA](https://github.com/LesterThomas/SAAA) repository for issues labeled "AI Agent" and automatically generate helpful responses.