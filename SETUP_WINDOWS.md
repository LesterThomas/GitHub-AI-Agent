# GitHub AI Agent - Windows PowerShell + uv Setup Guide

## Quick Setup

### 1. Install uv (if not already installed)
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Set your OpenAI API Key
```powershell
$env:OPENAI_API_KEY = "your-openai-api-key-here"
```

### 3. Install dependencies and run test
```powershell
# Navigate to project directory
cd C:\Dev\lesterthomas\GitHub-AI-Agent

# Run the test script
.\test_agent.ps1
```

## Manual Testing

If you prefer to run commands manually:

### Install dependencies
```powershell
uv sync
```

### Test the agent tools
```powershell
uv run python test_simple_agent.py
```

### Run the actual agent (after configuring GitHub tokens)
```powershell
uv run python -m github_ai_agent.main
```

## Expected Behavior

For an issue like: **"Create a new file TEST.md and write in it 'this is a test'"**

The agent should:
1. ✅ Extract file request: `TEST.md` with content `this is a test`
2. ✅ Create the file in the target repository
3. ✅ Create a pull request
4. ✅ Complete without infinite loops

## Key Fixes Made

1. **Simplified Tools**: Reduced from 3 complex tools to 2 focused tools
2. **Clear System Prompt**: Direct instructions without over-analysis
3. **Reduced Recursion**: Limited to 10 steps (was 50)
4. **Lower Iterations**: Max 5 iterations (was 10)
5. **Better Error Handling**: Proper imports and complete implementations

## Troubleshooting

### If the agent still loops:
- Check that `recursion_limit=10` in the agent initialization
- Verify the system prompt is simple and direct
- Ensure tools return clear results

### If tools fail:
- Verify OpenAI API key is set correctly
- Check internet connection for OpenAI API calls
- Review logs in `agent_test.log`

### If imports fail:
- Make sure you're in the project root directory
- Run `uv sync` to ensure dependencies are installed
- Check that `github_ai_agent` package is properly structured

## Environment Variables

```powershell
# Required for testing
$env:OPENAI_API_KEY = "your-key"

# Required for actual GitHub operations
$env:GITHUB_TOKEN = "your-github-token"
$env:GITHUB_OWNER = "your-username"
$env:GITHUB_REPO = "your-repo"
$env:TARGET_OWNER = "target-username" 
$env:TARGET_REPO = "target-repo"
```
