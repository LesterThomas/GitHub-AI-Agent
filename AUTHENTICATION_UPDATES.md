# GitHub Client Authentication Updates

## Overview

The GitHub client has been updated to support both GitHub Token and GitHub App authentication methods with configurable preferences.

## Changes Made

### 1. GitHubClient Class Updates

**File**: `github_ai_agent/github_client.py`

- Added `prefer_token` parameter to the constructor
- Implemented authentication method selection logic:
  - If `prefer_token=True`: Use token authentication if available, fallback to GitHub App
  - If `prefer_token=False`: Use GitHub App authentication if available, fallback to token

### 2. Reset Script Updates

**File**: `reset_saaa_repo.py`

- Modified to prefer token authentication (`GITHUB_TOKEN`) as requested
- Added fallback to GitHub App authentication if token fails
- Enhanced error handling and user feedback
- Shows which authentication method was successfully used

### 3. Main Application Updates

**File**: `github_ai_agent/main.py`

- Updated to explicitly prefer GitHub App authentication (maintains existing behavior)
- Provides token as fallback option

## Authentication Behavior

### Reset Script (`reset_saaa_repo.py`)
1. **Primary**: Attempts to use `GITHUB_TOKEN` (Personal Access Token)
2. **Fallback**: Uses GitHub App credentials if token authentication fails
3. **Error**: Exits with helpful message if neither method works

### Main Application (`github_ai_agent/main.py`)
1. **Primary**: Uses GitHub App authentication (as before)
2. **Fallback**: Uses `GITHUB_TOKEN` if GitHub App credentials unavailable
3. **Error**: Exits with helpful message if neither method works

## Configuration

Both authentication methods are configured via environment variables in `.env`:

```properties
# Token Authentication (for reset script)
GITHUB_TOKEN=ghp_your_personal_access_token_here

# GitHub App Authentication (for main application)
GITHUB_APP_ID=1496943
GITHUB_CLIENT_ID=Iv23li1X8zLzRMyupwtg
GITHUB_CLIENT_SECRET=9dd7ef609807abc37b9cda8d798bc35cad1065be
```

## Usage Examples

### Reset Script with Token Preference
```python
client = GitHubClient(
    target_owner="owner",
    target_repo="repo",
    token=github_token,
    app_id=github_app_id,
    client_id=github_client_id,
    client_secret=github_client_secret,
    prefer_token=True  # Prefers token authentication
)
```

### Main App with GitHub App Preference
```python
client = GitHubClient(
    target_owner="owner",
    target_repo="repo",
    token=github_token,
    app_id=github_app_id,
    client_id=github_client_id,
    client_secret=github_client_secret,
    prefer_token=False  # Prefers GitHub App authentication
)
```

## Testing

The implementation has been tested with:
- ✅ Authentication method selection logic
- ✅ Fallback behavior when preferred method fails
- ✅ Reset script functionality with both authentication methods
- ✅ Main application compatibility

## Benefits

1. **Flexibility**: Supports both authentication methods
2. **Robustness**: Automatic fallback prevents authentication failures
3. **User Control**: Explicit preference setting for different use cases
4. **Backward Compatibility**: Existing code continues to work unchanged
