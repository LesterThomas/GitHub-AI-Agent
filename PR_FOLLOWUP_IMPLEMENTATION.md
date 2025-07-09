# GitHub AI Agent - PR Follow-up Comment Implementation

## Overview
This implementation adds the ability for the GitHub AI Agent to detect follow-up comments on open pull requests and re-process the related issues with the new context.

## Key Features Implemented

### 1. PR Comment Detection
- **`get_pull_request_comments_since()`**: Retrieves comments on a PR since a specific timestamp
- **`find_related_issue_for_pr()`**: Finds the related issue number for a PR by parsing:
  - PR body for patterns like `#123`, `fixes #123`, `closes #123`, etc.
  - PR title for patterns like `Issue #123`, `Processing Issue #123`, etc.
- **`get_open_prs_with_recent_comments()`**: Aggregates open PRs with recent comments and their related issues

### 2. Issue Re-processing
- **Enhanced `process_issue()` method**: Now accepts `additional_context` parameter
- **Enhanced `get_human_message_template()`**: Includes additional context in the AI agent prompt
- **Re-processing workflow**: When PR comments are detected, the related issue is re-processed with the comment context

### 3. Comment Processing Logic
- **User comment filtering**: Excludes AI agent's own comments to prevent infinite loops
- **Timestamp tracking**: Tracks the last PR comment check time to avoid duplicate processing
- **Multiple comment aggregation**: Combines multiple comments into context for the AI agent

### 4. Integration with Main Workflow
- **`check_pr_follow_up_comments()`**: Main method that orchestrates the PR comment checking process
- **Integrated polling**: PR comment checking happens after regular issue processing
- **Automatic notifications**: Posts updates to both the issue and PR when re-processing occurs

## Workflow

1. **Regular Issue Processing**: The agent first processes new assigned issues or labeled issues
2. **PR Comment Scanning**: After processing new issues, the agent scans open PRs for recent comments
3. **Comment Filtering**: Filters out AI agent's own comments and checks for user comments
4. **Issue Re-processing**: If user comments are found, re-processes the related issue with comment context
5. **Updates**: Posts updates to both the issue and PR about the re-processing

## Code Changes

### GitHubClient (`github_client.py`)
- Added `get_pull_request_comments_since()` method
- Added `find_related_issue_for_pr()` method  
- Added `get_open_prs_with_recent_comments()` method

### Main Application (`main.py`)
- Added `check_pr_follow_up_comments()` method
- Added `last_pr_comment_check` timestamp tracking
- Integrated PR comment checking into `poll_and_process_issues()`

### Agent (`agent.py`)
- Enhanced `process_issue()` method to accept `additional_context`
- Updated method signature and docstring

### Configuration (`config.py`)
- Enhanced `get_human_message_template()` to include additional context

## Example Usage

When a user comments on a PR:
```
User comment: "Can you also add logging to this function?"
```

The agent will:
1. Detect the comment on the PR
2. Find the related issue (#456)
3. Re-process the issue with the comment as additional context
4. Update the PR with the changes
5. Post notifications to both the issue and PR

## Benefits

- **Responsive**: Automatically responds to user feedback on PRs
- **Contextual**: Provides full comment context to the AI agent
- **Efficient**: Only processes PRs with new comments
- **Safe**: Prevents infinite loops by filtering out AI agent comments
- **Transparent**: Clearly communicates when re-processing occurs

## Testing

The implementation includes:
- Unit tests for PR comment functionality
- Integration demo showing the complete workflow
- Error handling for edge cases
- Logging for debugging and monitoring

## Future Enhancements

Potential improvements:
- Support for PR review comments (not just issue comments)
- Configurable comment patterns for issue detection
- Rate limiting for PR comment checking
- Webhook integration for real-time comment processing
