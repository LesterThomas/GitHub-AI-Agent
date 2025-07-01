# Enhanced Logging Features

The GitHub AI Agent now includes comprehensive color-coded console logging to track all interactions between the agent, LLM, and tools as it processes issues and creates files in the SAAA repository.

## SAAA Repository Workflow

The agent operates on the SAAA repository with the following workflow:
1. **Fetch Issues**: Monitor issues in the source repository (where the agent runs)
2. **Create Feature Branch**: Create a new feature branch in the SAAA repository
3. **Generate Files**: Create or update files in the SAAA repository on the feature branch
4. **Create Pull Request**: Submit a PR to merge changes into the SAAA repository's main branch
5. **Add Comment**: Comment on the original issue with the PR link

## Color Scheme

- **🔵 Agent Actions (Blue)**: All agent-initiated actions and state changes
- **🟢 LLM Interactions (Green)**: Requests to and responses from the language model
- **🟣 Tool Usage (Magenta)**: Tool invocations with inputs and outputs
- **🔴 Errors (Red)**: Error messages and exceptions
- **🟡 Warnings (Yellow)**: Warning messages
- **🟦 Info (Cyan)**: General information and status updates

## Log Types

### Agent Actions
- `INIT`: Initialization steps
- `START`/`COMPLETE`: Process start and completion
- `FETCH`: Data retrieval operations  
- `BRANCH_CREATE`: Git branch creation
- `FILE_CREATE`/`FILE_COMMIT`: File operations
- `PR_CREATE`: Pull request creation
- `SUCCESS`/`FAILED`: Final status

### LLM Interactions
- `REQUEST`: Messages sent to the LLM
- `RESPONSE`: Responses received from the LLM

### Tool Usage
- Shows tool name, inputs, and outputs for all tool invocations
- Includes tools like `analyze_issue_requirements`, `create_file_content`, `validate_content`

## Testing the Logging

Run the demo script to see all logging types in action:

```bash
python test_logging.py
```

This will demonstrate all the different logging categories with color coding without processing real GitHub issues.

## Console Output Example

```
[14:32:01] AGENT INIT: Initializing GitHub Issue Agent
[14:32:01] INFO: Model: gpt-4, Max iterations: 10
[14:32:01] INFO: Target SAAA repository: LesterThomas/SAAA
[14:32:01] AGENT TOOLS: Created 3 tools: ['analyze_issue_requirements', 'create_file_content', 'validate_content']
[14:32:01] AGENT START: Starting to process issue #123
[14:32:01] AGENT BRANCH_CREATE: Creating feature branch 'ai-agent/issue-123' in SAAA repository
[14:32:01] INFO: Target repository: LesterThomas/SAAA
[14:32:01] TOOL analyze_issue_requirements:
  Input: Title: Create TEST.md describing Cardiff, Body: Please create a TEST.md file...
  Output: {'requested_files': ['TEST.md'], 'content_requirements': ['describing Cardiff']}
[14:32:02] LLM REQUEST: Input: Analyze this GitHub issue and identify what files need to be created...
[14:32:03] LLM RESPONSE: Output: I need to create a TEST.md file with content about Cardiff...
[14:32:03] AGENT FILE_COMMIT: Creating file TEST.md in SAAA repository on branch ai-agent/issue-123
[14:32:03] INFO: Successfully created file: TEST.md in SAAA repository
[14:32:04] AGENT PR_CREATE: Creating pull request to SAAA repository: Create TEST.md as requested in issue #123
[14:32:04] INFO: Successfully created pull request #45 in SAAA repository
[14:32:04] INFO: Pull request URL: https://github.com/LesterThomas/SAAA/pull/45
[14:32:04] AGENT SUCCESS: Issue #123 processed successfully - created PR in SAAA repository
```

## Implementation Details

The logging system includes:

1. **Color Support**: ANSI color codes for terminal output
2. **Timestamp Integration**: All log entries include timestamps
3. **Message Truncation**: Long messages are truncated for console readability
4. **Tool Tracking**: Detailed input/output logging for all tool calls
5. **LLM Monitoring**: Complete request/response cycle logging
6. **Error Handling**: Enhanced error logging with stack traces

The logging integrates seamlessly with Python's standard logging framework while adding visual enhancements for easier debugging and monitoring.
