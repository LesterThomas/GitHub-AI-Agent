# SAAA Repository Reset Script

This directory contains a test script that can reset the SAAA repository by closing all open issues and pull requests, then creating a new issue.

## Files Added

### `reset_saaa_repo.py`
Main script that performs the repository reset operation.

**What it does:**
1. Retrieves all open issues in `https://github.com/LesterThomas/SAAA` and closes them
2. Retrieves all open pull requests in `https://github.com/LesterThomas/SAAA` and closes them  
3. Creates 1 new issue with:
   - **Title**: Create TEST.md
   - **Description**: Create a TEST.md markdown file and in the content of the file make up a poem about clouds.
   - **Labels**: AI Agent

### Enhanced GitHubClient Methods

Added the following methods to `github_ai_agent/github_client.py`:

- `close_issue(issue_number: int) -> bool` - Close an issue
- `get_pull_requests(state: str = "open") -> List[PullRequest]` - Get pull requests
- `close_pull_request(pr_number: int) -> bool` - Close a pull request  
- `create_issue(title: str, body: str, labels: Optional[List[str]] = None) -> Optional[Issue]` - Create a new issue

### Test Files

- `test_reset_functionality.py` - Unit tests for the new GitHubClient methods
- `test_reset_dry_run.py` - Dry-run test that validates the reset script logic without making API calls
- Updated `tests/test_basic.py` - Added tests for new methods to the main test suite

## Usage

### Prerequisites
- Python 3.12+
- GitHub token with permissions to read/write issues and pull requests for `LesterThomas/SAAA`

### Running the Script

1. Set your GitHub token:
   ```bash
   export GITHUB_TOKEN=your_github_token_here
   ```

2. Run the script:
   ```bash
   python reset_saaa_repo.py
   ```

3. For help:
   ```bash
   python reset_saaa_repo.py --help
   ```

### Testing

Run the unit tests:
```bash
python test_reset_functionality.py
```

Run the dry-run test:
```bash
python test_reset_dry_run.py
```

## Example Output

```
🔄 Starting SAAA repository reset...
📁 Target repository: LesterThomas/SAAA

📋 Step 1: Closing all open issues...
🔍 Found 2 open issue(s)
  🔒 Closing issue #123: Old issue title
    ✅ Successfully closed issue #123
  ⏭️  Skipping #124 (is a pull request)

🔀 Step 2: Closing all open pull requests...
🔍 Found 1 open pull request(s)
  🔒 Closing pull request #124: Old PR title
    ✅ Successfully closed pull request #124

📝 Step 3: Creating new issue...
✅ Successfully created new issue #125: Create TEST.md
🔗 Issue URL: https://github.com/LesterThomas/SAAA/issues/125

🎉 SAAA repository reset completed!
```

## Safety Features

- The script distinguishes between real issues and pull requests (PRs appear as issues in GitHub API)
- Comprehensive error handling for each operation
- Clear logging of all actions taken
- Dry-run testing capability for validation

## Integration with AI Agent

Once the new issue is created with the "AI Agent" label, the existing GitHub AI Agent will detect it and process it according to the SAAA workflow, creating the requested TEST.md file with a poem about clouds.