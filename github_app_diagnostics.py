#!/usr/bin/env python3
"""
GitHub App Setup Diagnostics and Helper Script

This script helps diagnose GitHub App authentication issues and provides
guidance on what's needed for proper GitHub App authentication.
"""

import requests
import sys
from pathlib import Path


def check_github_app_setup():
    """Check GitHub App setup and provide guidance."""
    print("🔍 GitHub App Authentication Diagnostics")
    print("=" * 50)

    # Your current settings
    app_id = "1496943"
    client_id = "Iv23li1X8zLzRMyupwtg"
    client_secret = "9dd7ef609807abc37b9cda8d798bc35cad1065be"

    print(f"App ID: {app_id}")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret[:10]}...")
    print()

    # Check if this is a GitHub App or OAuth App
    print("📋 Checking App Type...")
    try:
        # Try to access the GitHub App endpoint
        response = requests.get(
            f"https://api.github.com/apps/{app_id}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "EA-Agent/1.0",
            },
        )

        if response.status_code == 200:
            app_data = response.json()
            print(f"✅ This is a GitHub App: {app_data.get('name', 'Unknown')}")
            print(f"   Owner: {app_data.get('owner', {}).get('login', 'Unknown')}")
            print(f"   Created: {app_data.get('created_at', 'Unknown')}")
            return True, app_data
        elif response.status_code == 404:
            print("❌ File not found")
            return False, None
        else:
            print(f"❓ Unexpected response: {response.status_code}")
            return False, None

    except Exception as e:
        print(f"❌ Error checking app type: {e}")
        return False, None


def check_private_key():
    """Check for private key file."""
    print("\n🔑 Checking for Private Key...")

    # Common private key file names
    key_files = [
        "ea-agent.2025-07-02.private-key.pem",
        "private-key.pem",
        "ea-agent-private-key.pem",
        "github-app-private-key.pem",
        f"app-{1496943}-private-key.pem",
    ]

    project_root = Path(".")
    found_key = False

    for key_file in key_files:
        key_path = project_root / key_file
        if key_path.exists():
            print(f"✅ Found private key: {key_path}")
            found_key = True
            return str(key_path)

    if not found_key:
        print("❌ No private key file found")
        print("\n📝 To get your private key:")
        print("1. Go to https://github.com/settings/apps")
        print("2. Click on your 'EA Agent' app")
        print("3. Scroll down to 'Private keys' section")
        print("4. Click 'Generate a private key'")
        print("5. Download the .pem file")
        print("6. Save it in this project directory as 'ea-agent-private-key.pem'")
        return None


def check_app_installation():
    """Check if the app is installed on the target repository."""
    print("\n🏠 Checking App Installation...")

    try:
        # Check if app is installed on the target repo
        response = requests.get(
            "https://api.github.com/repos/LesterThomas/SAAA/installation",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "EA-Agent/1.0",
            },
        )

        if response.status_code == 200:
            install_data = response.json()
            print(f"✅ App is installed on LesterThomas/SAAA")
            print(f"   Installation ID: {install_data.get('id')}")
            print(f"   Account: {install_data.get('account', {}).get('login')}")
            return install_data.get("id")
        elif response.status_code == 404:
            print("❌ App is NOT installed on LesterThomas/SAAA")
            print("\n📝 To install your app:")
            print("1. Go to https://github.com/apps/ea-agent")
            print("2. Click 'Install'")
            print("3. Select 'LesterThomas' account")
            print("4. Choose 'Only select repositories' and select 'SAAA'")
            print("5. Click 'Install'")
            return None
        else:
            print(f"❓ Unexpected response: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error checking installation: {e}")
        return None


def provide_next_steps(is_github_app, has_private_key, has_installation):
    """Provide next steps based on the diagnosis."""
    print("\n🎯 Next Steps")
    print("=" * 50)

    if not is_github_app:
        print("❌ Your app appears to be an OAuth App, not a GitHub App")
        print("   For OAuth Apps, you can use different authentication methods.")
        print("   Consider creating a new GitHub App instead for better functionality.")
        return

    if not has_private_key:
        print("🔑 REQUIRED: Generate and download a private key")
        print("   This is essential for GitHub App authentication")
        return

    if not has_installation:
        print("🏠 REQUIRED: Install the app on your repository")
        print("   The app must be installed to access repository resources")
        return

    print("✅ All requirements met! You can now implement GitHub App authentication")
    print("\n📋 Implementation checklist:")
    print("1. ✅ GitHub App created")
    print("2. ✅ Private key available")
    print("3. ✅ App installed on repository")
    print("4. 🔄 Update code to use proper JWT + installation token flow")


def main():
    """Main diagnostic function."""
    print("GitHub App Authentication Setup Helper")
    print("====================================\n")

    # Run diagnostics
    is_github_app, app_data = check_github_app_setup()
    private_key_path = check_private_key()
    installation_id = check_app_installation()

    # Provide guidance
    provide_next_steps(
        is_github_app, private_key_path is not None, installation_id is not None
    )

    # Save results for reference
    if is_github_app and private_key_path and installation_id:
        print(f"\n💡 Ready to implement! Use these values:")
        print(f"   App ID: 1496943")
        print(f"   Private Key: {private_key_path}")
        print(f"   Installation ID: {installation_id}")
        print(f"   Client ID: Iv23li1X8zLzRMyupwtg")


if __name__ == "__main__":
    main()
