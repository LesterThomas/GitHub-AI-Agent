# PowerShell script to test the GitHub AI Agent with uv
# Run this script from the project root directory

Write-Host "GitHub AI Agent Test Script for Windows PowerShell + uv" -ForegroundColor Green
Write-Host "=" * 60

# Check if uv is installed
try {
    $uvVersion = uv --version
    Write-Host "✓ uv found: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ uv not found. Please install uv first:" -ForegroundColor Red
    Write-Host "  powershell -c ""irm https://astral.sh/uv/install.ps1 | iex"""
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "pyproject.toml")) {
    Write-Host "✗ pyproject.toml not found. Please run this script from the project root." -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found pyproject.toml" -ForegroundColor Green

# Check if OpenAI API key is set
if (-not $env:OPENAI_API_KEY) {
    Write-Host "✗ OPENAI_API_KEY environment variable not set" -ForegroundColor Red
    Write-Host "Please set your OpenAI API key:" -ForegroundColor Yellow
    Write-Host "  `$env:OPENAI_API_KEY = 'your-api-key-here'" -ForegroundColor Yellow
    
    # Optionally prompt for API key
    $apiKey = Read-Host "Enter your OpenAI API key (or press Enter to skip)"
    if ($apiKey) {
        $env:OPENAI_API_KEY = $apiKey
        Write-Host "✓ OpenAI API key set temporarily" -ForegroundColor Green
    } else {
        Write-Host "Skipping test due to missing API key" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "✓ OpenAI API key found" -ForegroundColor Green
}

# Install dependencies with uv
Write-Host "`nInstalling dependencies with uv..." -ForegroundColor Blue
try {
    uv sync
    Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Run the test
Write-Host "`nRunning agent test..." -ForegroundColor Blue
try {
    uv run python test_simple_agent.py
    Write-Host "`n✓ Test completed successfully" -ForegroundColor Green
} catch {
    Write-Host "`n✗ Test failed" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
}

# Show log file if it exists
if (Test-Path "agent_test.log") {
    Write-Host "`nTest log file created: agent_test.log" -ForegroundColor Blue
    Write-Host "View the log with: Get-Content agent_test.log" -ForegroundColor Blue
}

Write-Host "`nTo manually test the agent:" -ForegroundColor Blue
Write-Host "1. Set your API key: `$env:OPENAI_API_KEY = 'your-key'" -ForegroundColor Yellow
Write-Host "2. Run: uv run python test_simple_agent.py" -ForegroundColor Yellow

Write-Host "`nTo run the actual agent:" -ForegroundColor Blue
Write-Host "1. Configure your GitHub tokens in the config" -ForegroundColor Yellow
Write-Host "2. Run: uv run python -m github_ai_agent.main" -ForegroundColor Yellow
