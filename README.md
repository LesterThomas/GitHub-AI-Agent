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
| `GITHUB_TOKEN` | *optional* | GitHub personal access token for human user (used by reset script) |
| `GITHUB_AI_AGENT_TOKEN` | *required* | GitHub personal access token for AI Agent persona |
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

#### GitHub Tokens

The application uses two separate GitHub tokens:

**AI Agent Token (Required)**
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `repo` permissions for the AI Agent persona
3. Add to `.env` as `GITHUB_AI_AGENT_TOKEN=your_ai_agent_token_here`

**Human User Token (Optional)**
1. Generate a separate token for human user operations (reset script)
2. Add to `.env` as `GITHUB_TOKEN=your_human_token_here`

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
4. **File Creation**: Agent uses the `create_files_from_request` tool to create files directly in GitHub
5. **Commit & Branch**: Files are committed directly to the pre-created feature branch
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

The agent uses a comprehensive system prompt that is now configured in the `prompts.yaml` file for easy maintenance and updates. The system prompt guides the agent's behavior and includes:

- **Role Definition**: AI agent for processing GitHub issues and managing repository files
- **Capabilities**: Reading repository structure, file contents, creating and editing files
- **Available Tools**: Detailed descriptions of list_files_in_repo, read_file_from_repo, create_file_in_repo, and edit_file_in_repo
- **Workflow Examples**: Step-by-step guidance for different types of tasks
- **Analysis Instructions**: Guidelines for determining work needed and best practices

**Configuration Management**: 
All prompts (system prompt, human message templates, and tool descriptions) are now stored in `prompts.yaml` for:
- Easy updates without code changes
- Better separation of configuration from code
- Centralized prompt management
- Version control of prompt changes

The system prompt automatically includes the target repository information (`{target_owner}/{target_repo}`) when loaded.

### Tool Description

The agent has access to four specialized tools for comprehensive file management:

#### `create_files_from_request`

**Purpose**: Create files directly in GitHub repository from a JSON array of file objects

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

**Output**: JSON status report of the file creation operation
```json
{
  "success": true,
  "files_created": ["test.md", "readme.txt"],
  "files_count": 2,
  "errors": null
}
```

#### `list_files_in_repo`

**Purpose**: Browse repository structure by listing files and directories

**Usage**: `list_files_in_repo(path="", branch="main")`
- `path`: Directory path to list (empty string for root)
- `branch`: Branch name (defaults to 'main')

**Output**: JSON with repository contents
```json
{
  "success": true,
  "path": "",
  "contents": [
    {"name": "README.md", "type": "file", "size": 2048},
    {"name": "src", "type": "dir", "size": null}
  ]
}
```

#### `read_file_from_repo`

**Purpose**: Read the content of specific files from the repository

**Usage**: `read_file_from_repo(file_path, branch="main")`
- `file_path`: Path to the file in the repository
- `branch`: Branch name (defaults to 'main')

**Output**: JSON with file content
```json
{
  "success": true,
  "file_path": "README.md",
  "content": "# Project\n\nDescription here...",
  "length": 156
}
```

#### `edit_file_in_repo`

**Purpose**: Edit existing files or create new ones with custom commit messages

**Usage**: `edit_file_in_repo(file_path, file_content, commit_message="", branch="")`
- `file_path`: Path to the file in the repository
- `file_content`: New content for the file
- `commit_message`: Optional commit message
- `branch`: Branch name (defaults to current working branch)

**Output**: JSON status report
```json
{
  "success": true,
  "file_path": "config.json",
  "commit_message": "Update configuration",
  "content_length": 245
}
```

These tools enable the agent to:
- **Explore** repository structure before making changes
- **Read** existing files to understand current codebase
- **Create** new files with specified content
- **Edit** existing files with proper version control

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
│ 6. TOOL         │ -> │ 7. STATUS CHECK  │ -> │ 8. PULL REQUEST │
│    EXECUTION    │    │                  │    │                 │
│                 │    │ • Check tool     │    │ • Create PR     │
│ • Execute       │    │   results        │    │   in SAAA repo  │
│   create_files_ │    │ • Verify files   │    │ • Link to issue │
│   from_request  │    │   created        │    │ • Add metadata  │
│ • Create files  │    │ • Fallback if    │    │                 │
│   directly in   │    │   needed         │    │                 │
│   GitHub        │    │                  │    │                 │
│ • Return status │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         |                       |                       |
         v                       v                       v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ 9. ISSUE        │ -> │ 10. LOGGING &    │ -> │ 11. COMPLETION  │
│    COMMENT      │    │     TRACKING     │    │                 │
│                 │    │                  │    │ • Mark issue    |
│ • Add comment   │    │ • Color-coded    │    │   as processed  |
│   with PR link  │    │   console logs   │    │ • Return        |
│ • Close or      │    │ • State tracking │    │   success       |
│   reference     │    │ • Error handling │    │   status        |
│   issue         │    │                  │    │                 |
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Detailed Step Breakdown

#### 1-3. Polling, Issue Detection & Branch Creation
- **Frequency**: Every 5 minutes (configurable via `POLL_INTERVAL`)
- **Filter**: Issues with "AI Agent" label in the configured repository
- **State**: Tracks processed issues to avoid duplication
- **Early Branch**: Creates feature branch immediately upon issue detection

#### 4-6. Agent Initialization, Reasoning & Tool Execution
- **LLM Model**: GPT-4o-mini (configurable via `OPENAI_MODEL`)
- **ReAct Pattern**: Uses LanGraph's built-in ReAct agent with MemorySaver checkpointing
- **Reasoning**: Analyzes issue requirements and plans file operations
- **Multiple Tools**: 5 comprehensive tools for repository management:
  - `create_file_in_repo`: Create new files in the target repository
  - `edit_file_in_repo`: Modify existing files
  - `read_file_from_repo`: Read file contents for context
  - `list_files_in_repo`: Explore repository structure
  - `delete_file_from_repo`: Remove files when needed
- **Direct Creation**: Files are created immediately in GitHub with proper commit messages

#### 7-8. Status Check & Pull Request Creation
- **Target Repository**: SAAA repository (separate from issue source)
- **Branch Strategy**: Uses pre-created feature branch `ai-agent/issue-{number}`
- **File Creation**: Tool creates files directly via GitHub API with proper commit messages
- **PR Creation**: Automated pull request with detailed metadata
- **Error Handling**: Comprehensive error handling with fallbacks

#### 9-11. Issue Management & Completion
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
│   │                         # - GitHubIssueAgent class (1,152 lines)
│   │                         # - AgentState and IssueProcessingResult data classes
│   │                         # - 5 repository management tools
│   │                         # - Comprehensive error handling and logging
│   ├── config.py             # Pydantic settings management (120 lines)
│   │                         # - Environment-based configuration
│   │                         # - YAML prompt loading and templating
│   │                         # - Type-safe settings validation
│   ├── github_client.py      # GitHub API integration (1,000+ lines)
│   │                         # - Multi-authentication support (tokens, GitHub App)
│   │                         # - Full CRUD operations for repositories
│   │                         # - Advanced PR and issue management
│   ├── logging_utils.py      # Enhanced logging utilities (247 lines)
│   │                         # - ANSI color coding for different log types
│   │                         # - Structured logging for debugging
│   │                         # - Pretty JSON formatting
│   └── main.py               # Application orchestration (500+ lines)
│                             # - GitHubAIAgentApp class
│                             # - Polling and issue detection logic
│                             # - Daemon and single-run modes
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── test_basic.py         # Basic functionality tests
│   ├── test_pr_comments.py   # PR comment processing tests
│   └── test_prompt_config.py # Configuration and prompt tests
├── main.py                   # CLI entry point
├── prompts.yaml              # YAML configuration for all prompts
├── pyproject.toml            # Project configuration & dependencies
├── uv.lock                   # Dependency lock file
├── .env.example              # Environment template
├── README.md                 # This file
└── LICENSE                   # Apache 2.0 license
```

### Key Files

- **`agent.py`**: Contains the `GitHubIssueAgent` class with comprehensive ReAct implementation
  - Well-documented classes: `AgentState`, `IssueProcessingResult`, `GitHubIssueAgent`
  - Comprehensive tool management with 5 repository operation tools
  - Robust error handling and state management
  - Streaming execution support with fallback to invoke mode
- **`github_client.py`**: Handles all GitHub API operations (issues, PRs, files, authentication)
  - Supports multiple authentication methods (Personal tokens, GitHub App)
  - Comprehensive CRUD operations for repository management
  - Advanced features like PR comment monitoring and issue processing state tracking
- **`config.py`**: Pydantic-based configuration with environment variable loading
  - Type-safe settings management with validation
  - YAML-based prompt configuration system
  - Template rendering for system and human messages
- **`main.py`**: Application entry point with daemon and single-run modes
  - Comprehensive polling and issue detection logic
  - Color-coded logging and monitoring
  - PR follow-up comment processing
- **`logging_utils.py`**: Enhanced logging utilities with color support
  - ANSI color codes for different log types
  - Structured logging for agent actions, LLM interactions, and tool usage
  - Pretty JSON formatting and timestamps
- **`prompts.yaml`**: 
  - System, HumanMessage and tool prompts in an easy to read YAML configuration file.

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
The agent uses five comprehensive tools for repository management:

```python
# Repository exploration tools
Tool(name="list_files_in_repo", description="List files and directories...")
Tool(name="read_file_from_repo", description="Read file contents...")

# File management tools  
Tool(name="create_file_in_repo", description="Create new files...")
Tool(name="edit_file_in_repo", description="Modify existing files...")
Tool(name="delete_file_in_repo", description="Remove files...")
```

Each tool includes:
- **Pydantic input validation** with structured schemas
- **Comprehensive error handling** with JSON responses
- **Contextual commit messages** tied to issue numbers
- **Branch-aware operations** with proper state management

### 4. **Error Handling & Streaming**
- Comprehensive error handling with fallback strategies
- Stream execution with multiple modes: `["values", "updates", "debug"]`
- State logging at each execution step

### 5. **LLM Integration**
- Custom OpenAI integration with enhanced request/response logging
- Configurable models (default: GPT-4o-mini for cost efficiency)
- Temperature set to 0.1 for consistent, predictable outputs
- Comprehensive message handling for different LangChain message types

## Code Quality and Best Practices

### Documentation Standards
- **Comprehensive Docstrings**: All classes and methods follow Google/Sphinx documentation style
- **Type Annotations**: Complete type hints throughout the codebase using modern Python typing
- **Module Documentation**: Each module includes detailed purpose and usage information
- **Inline Comments**: Strategic commenting for complex logic and business rules

### Architecture Patterns
- **Separation of Concerns**: Clean module boundaries with specific responsibilities
- **Configuration Management**: Centralized settings using Pydantic with environment variable support
- **Error Handling**: Robust exception handling with comprehensive logging
- **State Management**: Immutable state patterns using TypedDict and LangGraph reducers

### Code Organization
- **Import Structure**: Well-organized imports following PEP 8 guidelines
- **Class Design**: Single responsibility principle with clear inheritance patterns
- **Method Structure**: Logical grouping with clear public/private interfaces
- **Data Classes**: Proper use of dataclasses and TypedDict for structured data

### Testing and Quality Assurance
- **Test Coverage**: Basic test suite with mock-based unit tests
- **Development Tools**: Black, isort, mypy configured for code quality
- **Type Safety**: MyPy configuration for strict type checking
- **Modern Python**: Requires Python 3.12+ with modern language features

## Python Best Practices Implementation

### Type Safety and Modern Python Features
- **Python 3.12+ Requirements**: Leverages modern language features and improved performance
- **Comprehensive Type Hints**: All functions, methods, and variables include proper type annotations
- **TypedDict Usage**: Structured data definitions for LangGraph state management
- **Dataclasses**: Clean data containers with automatic method generation
- **Optional/Union Types**: Explicit handling of nullable values and type unions

### Error Handling and Robustness
- **Exception Hierarchy**: Proper exception handling with specific error types
- **Try-Catch Blocks**: Strategic exception handling around external API calls
- **Fallback Mechanisms**: Graceful degradation when primary operations fail
- **Logging Integration**: Comprehensive error logging with context and stack traces
- **Validation**: Input validation using Pydantic schemas and custom validators

### Configuration and Environment Management
- **Pydantic Settings**: Type-safe configuration with automatic validation
- **Environment Variables**: Secure credential management through environment configuration
- **YAML Configuration**: External configuration files for prompts and templates
- **Default Values**: Sensible defaults for all configuration options
- **Configuration Validation**: Early validation of required settings on startup

### Code Organization and Modularity
- **Single Responsibility**: Each module has a clear, focused purpose
- **Dependency Injection**: Clean dependency management through constructor injection
- **Interface Segregation**: Minimal coupling between components
- **Abstraction Layers**: Clear separation between business logic and external APIs
- **Factory Patterns**: Tool creation using factory methods for flexibility

### Memory Management and Performance
- **Lazy Loading**: Repository connections established only when needed
- **Resource Cleanup**: Proper cleanup of temporary state and resources
- **Streaming Support**: Memory-efficient processing of large agent conversations
- **Connection Pooling**: Efficient HTTP connection management through httpx
- **State Management**: Immutable state patterns for thread safety

## Contributing

### Development Setup
1. **Clone the repository**: `git clone <repository-url>`
2. **Install dependencies**: `uv sync` (or `pip install -e .`)
3. **Copy environment template**: `cp .env.example .env`
4. **Configure environment variables** in `.env` file

### Development Workflow
1. **Create a feature branch**: `git checkout -b feature/your-feature`
2. **Make your changes** following the established patterns
3. **Run quality checks**:
   ```bash
   uv run black .          # Code formatting
   uv run isort .          # Import sorting
   uv run mypy github_ai_agent  # Type checking
   uv run pytest          # Run tests
   ```
4. **Test your changes** thoroughly
5. **Submit a pull request** with clear description

### Code Standards
- **Follow existing patterns** established in the codebase
- **Add comprehensive docstrings** for new classes and methods
- **Include type hints** for all function signatures
- **Write tests** for new functionality
- **Update documentation** when adding features
- **Follow PEP 8** style guidelines (enforced by Black)

## Dependencies and Technology Stack

### Core Dependencies
- **LangGraph (>=0.2.39)**: State-of-the-art framework for building stateful multi-actor LLM applications
- **LangChain (>=0.3.7)**: Comprehensive framework for LLM application development
- **LangChain-OpenAI (>=0.2.8)**: OpenAI integration with structured tool calling support
- **OpenAI GPT-4o-mini**: Cost-efficient model with excellent reasoning capabilities

### GitHub Integration
- **PyGithub (>=2.4.0)**: Comprehensive Python wrapper for GitHub REST API v3
- **PyJWT (>=2.8.0)**: JSON Web Token implementation for GitHub App authentication
- **Cryptography (>=41.0.0)**: Secure cryptographic operations for key management

### Configuration and Data Management
- **Pydantic (>=2.9.2)**: Data validation and serialization with type safety
- **Pydantic-Settings (>=2.6.0)**: Environment-based configuration management
- **PyYAML**: YAML configuration file parsing for prompts and templates
- **Python-dotenv (>=1.0.1)**: Environment variable loading from .env files

### Development and Quality Assurance
- **Black (>=24.10.0)**: Uncompromising code formatter for consistent style
- **isort (>=5.13.2)**: Import statement organization and sorting
- **MyPy (>=1.13.0)**: Static type checker for enhanced code reliability
- **Pytest (>=8.3.3)**: Modern testing framework with extensive plugin ecosystem

## Debugging and Monitoring

### Log Output Format

The agent provides comprehensive color-coded logging for easy monitoring:

- **🤖 AGENT**: Agent actions and state changes (cyan)
- **🧠 LLM**: LLM requests and responses with structured formatting (green)
- **� TOOL**: Tool executions with input/output details (pink/magenta)
- **� GITHUB**: GitHub API operations and authentication (orange)
- **✅ SUCCESS**: Successful operations (bright green)
- **❌ ERROR**: Error conditions and exceptions (red)
- **⚠️ WARNING**: Warning messages (orange)
- **ℹ️ INFO**: General information (light blue)

### Enhanced Logging Features

- **Structured JSON Output**: Pretty-printed JSON for complex data structures
- **Message Truncation**: Long messages are intelligently truncated for readability
- **Contextual Icons**: Different icons for different types of operations
- **Timestamp Precision**: HH:MM:SS format for easy chronological tracking
- **Visual Separators**: Clean separation between different log sections

### Debug Mode

Enable debug logging for detailed execution tracking:

```bash
# Set in .env file
LOG_LEVEL=DEBUG

# Run with enhanced logging
uv run python main.py
```

Debug mode provides:
- Complete message history with conversation flow
- State transitions at each step with detailed context
- Tool execution details including input validation and error handling
- LLM token usage and response timing
- GitHub API call logs with request/response details
- Branch and file operation tracking

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
| Authentication errors | Invalid GitHub token or insufficient permissions | Regenerate token with full repo permissions |
| Rate limiting | Too frequent API calls or quota exceeded | Increase `POLL_INTERVAL` or check API limits |
| OpenAI errors | Invalid API key, quota, or model access | Check API key, billing, and model availability |
| Branch creation failed | Permission issues or branch already exists | Ensure token has write access, check existing branches |
| File creation failed | Path issues, permission problems, or content errors | Validate file paths, check repository permissions |
| Tool execution failed | Network issues or API timeouts | Check network connectivity and GitHub status |
| Agent timeout | Complex reasoning or infinite loops | Adjust `recursion_limit` and `max_iterations` |

## Target Repository

This agent is designed to monitor the [LesterThomas/SAAA](https://github.com/LesterThomas/SAAA) repository for issues labeled "AI Agent" and automatically generate helpful responses.


## Example Execution output

```
uv run python main.py
════════════════════════════════════════════════════════════════════════════════
🤖 GITHUB AI AGENT - Automated Issue Processing
════════════════════════════════════════════════════════════════════════════════
════════════════════════════════════════════════════════════
🎯 GITHUB AI AGENT INITIALIZATION
────────────────────────────────────────────────────────────
[23:04:18] ℹ️ Target: LesterThomas/SAAA
[23:04:18] ℹ️ Label filter: 'AI Agent'
[23:04:18] ℹ️ AI Model: gpt-4o-mini
[23:04:18] ℹ️ Max iterations: 20
[23:04:18] 🐙 Authenticated via AI Agent Token
[23:04:19] 🤖 Initializing GitHub Issue Agent
[23:04:19] 🤖 Model: gpt-4o-mini, Max iterations: 20
[23:04:19] 🤖 Recursion limit: 50
[23:04:19] 🤖 Target SAAA repository: LesterThomas/SAAA
[23:04:19] 🤖 Created 1 tools: ['create_files_from_request']
[23:04:19] 🤖 ReAct agent created successfully
────────────────────────────────────────────────────────────────────────────────
════════════════════════════════════════════════════════════
🎯 SINGLE RUN MODE
────────────────────────────────────────────────────────────
════════════════════════════════════════════════════════════
🎯 SCANNING FOR ISSUES
────────────────────────────────────────────────────────────
[23:04:19] ℹ️ Looking for issues labeled 'AI Agent'
[23:04:19] ℹ️ Discovered 1 unprocessed issues
────────────────────────────────────────────────────────────────────────────────
════════════════════════════════════════════════════════════
🎯 PROCESSING ISSUE #91 TITLE: CREATE TEST.MD
────────────────────────────────────────────────────────────
[23:04:19] 🐙 Creating branch 'ai-agent/issue-91'
[23:04:19] 🐙 Creating branch 'ai-agent/issue-91' in LesterThomas/SAAA from 'main'
[23:04:21] 🐙 Successfully created branch 'ai-agent/issue-91' in LesterThomas/SAAA
[23:04:21] 🐙 Branch 'ai-agent/issue-91' created successfully
[23:04:21] 🤖 Starting to process issue #91
[23:04:21] 🤖 Fetching issue #91 from GitHub
[23:04:21] 🤖 Successfully fetched issue #91: Create TEST.md
[23:04:21] 🤖 Issue data prepared - Title: Create TEST.md, User: LesterThomas, Labels: ['AI Agent']
[23:04:21] 🤖 Creating system and human messages
[23:04:21] 🤖 Messages created, preparing to invoke agent
[23:04:21] 🤖 Invoking ReAct agent with thread_id: issue-91, recursion_limit: 50
[23:04:21] 🧠 values (HumanMessage)
    Process this GitHub issue:

    Issue #91: Create TEST.md

    Description: Create a TEST.md markdown file and in the content of the file make up a poem about clouds.

    Analyze the issue and use create_files_from_request with a JSON array to create the requested files.

    Example format:
    [
      {
        "filename": "example.md",
        "file_content": "# Example\n\nThis is example content."
      }
    ]

    Use the create_files_from_request tool with proper JSON formatting.
──────────────────────────────────────────────────
[23:04:25] 🧠 values (AIMessage)
    Tool Calls:
      1. **create_files_from_request**
         Args: {
      "__arg1": "[{\"filename\": \"TEST.md\", \"file_content\": \"# Clouds\n\nIn the sky so high and bright,  \nFluffy clouds take their flight.  \nWhispers of white, drifting slow,  \nPainting the blue with a gentle glow.  \n\nSome are like cotton, soft and sweet,  \nOthers like shadows, a cool retreat.  \nThey dance and twirl, a graceful ballet,  \nChanging their shapes throughout the day.  \n\nWhen the sun sets, they catch the light,  \nA canvas of colors, a breathtaking sight.  \nOh, how they wander, free and proud,  \nA beautiful mystery, the ever-changing cloud.\"}]}"
    }
──────────────────────────────────────────────────
[23:04:25] 🔧 TOOL create_files_from_request [{"filename": "TEST.md", "file_content": "# Clouds

In the sky so high and bright,
Fluffy clouds t...
[23:04:25] ❌ TOOL create_files_from_request Invalid JSON format: Invalid control character at: line 1 column 51 (char 50)
[23:04:25] 🧠 values (ToolMessage)
    {"success": false, "error": "Invalid JSON format: Invalid control character at: line 1 column 51 (char 50)", "files_created": []}
──────────────────────────────────────────────────
[23:04:28] 🧠 values (AIMessage)
    Tool Calls:
      1. **create_files_from_request**
         Args: {
      "__arg1": "[{\"filename\": \"TEST.md\", \"file_content\": \"# Clouds\\n\\nIn the sky so high and bright,  \\nFluffy clouds take their flight.  \\nWhispers of white, drifting slow,  \\nPainting the blue with a gentle glow.  \\n\\nSome are like cotton, soft and sweet,  \\nOthers like shadows, a cool retreat.  \\nThey dance and twirl, a graceful ballet,  \\nChanging their shapes throughout the day.  \\n\\nWhen the sun sets, they catch the light,  \\nA canvas of colors, a breathtaking sight.  \\nOh, how they wander, free and proud,  \\nA beautiful mystery, the ever-changing cloud.\"}]"
    }
──────────────────────────────────────────────────
[23:04:28] 🔧 TOOL create_files_from_request [{"filename": "TEST.md", "file_content": "# Clouds\n\nIn the sky so high and bright,  \nFluffy cloud...
[23:04:28] 🤖 Creating file TEST.md in SAAA repository on branch ai-agent/issue-91
[23:04:28] 🐙 Creating/updating file 'TEST.md' in LesterThomas/SAAA on branch 'ai-agent/issue-91'
[23:04:29] 🐙 Created file 'TEST.md' in LesterThomas/SAAA
[23:04:29] 🤖 Successfully created file: TEST.md
[23:04:29] 🔧 TOOL create_files_from_request Created 1 files directly in GitHub
[23:04:29] 🧠 values (ToolMessage)
    {
      "success": true,
      "files_created": [
        "TEST.md"
      ],
      "files_count": 1,
      "errors": null
    }
──────────────────────────────────────────────────
[23:04:30] 🧠 values (AIMessage)
    Created the file **TEST.md** with a poem about clouds.
──────────────────────────────────────────────────
[23:04:30] 🤖 Agent execution completed after 6 steps
[23:04:30] 🤖 Generated content length: 54 characters
[23:04:30] 🤖 Total files created by tool: 1
[23:04:30] 🤖 Files created successfully: ['TEST.md']
[23:04:30] 🤖 Describing file: TEST.md
[23:04:30] 🤖 File description for TEST.md: Test markdown file with example content
[23:04:30] 🤖 Creating pull request to SAAA repository: Create TEST.md as requested in issue #91
[23:04:30] 🐙 Creating pull request in LesterThomas/SAAA: 'Create TEST.md as requested in issue #91'
[23:04:30] 🐙 PR details - Head: ai-agent/issue-91, Base: main, Draft: False
[23:04:31] 🐙 Successfully created pull request #92 in LesterThomas/SAAA: Create TEST.md as requested in issue #91
[23:04:31] 🐙 Pull request URL: https://github.com/LesterThomas/SAAA/pull/92
[23:04:31] 🤖 Successfully created pull request #92 in SAAA repository
[23:04:31] 🤖 Pull request URL: https://github.com/LesterThomas/SAAA/pull/92
[23:04:31] 🤖 Adding comment to issue #91
[23:04:33] 🐙 Added comment to issue #91
[23:04:33] 🤖 Issue #91 processed successfully - created PR in SAAA repository
[23:04:33] 🐙 Issue completed! Created PR #92
────────────────────────────────────────────────────────────────────────────────
[23:04:33] ℹ️ Single run completed
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.