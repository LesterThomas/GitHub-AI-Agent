# SAAA Repository Workflow

The GitHub AI Agent is configured to work with the **SAAA repository** (System for Automated AI Assistance) as its target for creating and updating files based on GitHub issues.

## Repository Configuration

The agent is configured via environment variables or `.env` file:

```env
# GitHub Settings
GITHUB_TOKEN=your_github_token_here
TARGET_OWNER=LesterThomas
TARGET_REPO=SAAA
ISSUE_LABEL=AI Agent

# OpenAI Settings  
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini

# Agent Settings
MAX_ITERATIONS=20
RECURSION_LIMIT=50
POLL_INTERVAL=300
```

## Workflow Overview

### 1. Issue Monitoring
- The agent monitors GitHub issues with the "AI Agent" label
- Issues can be created in any repository where the agent has access
- The agent processes these issues and creates files in the **SAAA repository**

### 2. Feature Branch Creation
- For each issue, the agent creates a feature branch in the SAAA repository
- Branch naming convention: `ai-agent/issue-{issue_number}`
- Example: `ai-agent/issue-123` for issue #123

### 3. File Operations
- The agent analyzes the issue to identify requested files
- Files are created or updated in the SAAA repository on the feature branch
- All changes are committed with descriptive commit messages

### 4. Pull Request Creation
- A pull request is created in the SAAA repository
- PR merges the feature branch into the main branch
- PR includes detailed information about the original issue and created files

### 5. Issue Feedback
- The agent comments on the original issue with the PR link
- Users can review the changes before merging

## Example Workflow

```
Issue Created: "Create TEST.md describing Cardiff"
    ↓
Agent processes issue
    ↓
Creates feature branch: ai-agent/issue-123 in SAAA repo
    ↓
Creates TEST.md with Cardiff content on feature branch
    ↓
Creates PR: SAAA repo feature branch → main branch
    ↓
Comments on original issue with PR link
```

## Benefits

### Repository Separation
- **Source Issues**: Can be created in any repository
- **Target Files**: All created in the centralized SAAA repository
- **Clean Organization**: Separates issue tracking from file storage

### Feature Branch Workflow
- **Safe Changes**: All modifications happen on feature branches
- **Review Process**: Changes require PR approval before merging
- **Change Tracking**: Full history of all AI-generated content

### Automated Integration
- **Seamless Process**: From issue creation to file delivery
- **Clear Attribution**: Every file links back to its originating issue
- **Audit Trail**: Complete logging of all operations

## File Organization

Files in the SAAA repository are organized as:
- **Direct files**: Requested files created in the root or specified paths
- **Generated folder**: Fallback location for metadata files
- **Branch history**: Complete record of all feature branches and merges

## Monitoring and Logging

The agent provides comprehensive logging of:
- Feature branch creation in SAAA repository
- File operations with full paths and content
- Pull request creation with URLs
- Repository-specific success/failure messages

All log messages clearly indicate operations are targeting the SAAA repository for transparency and debugging.

## Troubleshooting

### Recursion Limit Error
If you encounter "Recursion limit of 25 reached without hitting a stop condition", you can:

1. **Increase the recursion limit** in your `.env` file:
   ```env
   RECURSION_LIMIT=50
   ```

2. **Reduce max iterations** if the agent is looping:
   ```env
   MAX_ITERATIONS=10
   ```

3. **Check issue complexity** - very complex requests may require multiple iterations

### Common Settings
- **Default recursion limit**: 50 (increased from LangGraph default of 25)
- **Default max iterations**: 20
- **Recommended model**: gpt-4o-mini for cost efficiency

The recursion limit controls how many internal steps the LangGraph agent can take, while max iterations controls the overall ReAct loop iterations.
