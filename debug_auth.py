#!/usr/bin/env python3
"""Detailed test for GitHub App authentication methods."""

import requests
import logging
from github import Github

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_direct_api_calls():
    """Test direct GitHub API calls with your credentials."""
    client_id = "Iv23li1X8zLzRMyupwtg"
    client_secret = "9dd7ef609807abc37b9cda8d798bc35cad1065be"

    print("Testing GitHub API authentication methods...")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret[:10]}...")

    # Test 1: Try using client_secret as direct token
    print("\n=== Test 1: Client Secret as Token ===")
    try:
        github_client = Github(client_secret)
        user = github_client.get_user()
        print(f"✅ SUCCESS: Authenticated as user: {user.login}")
        return client_secret
    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test 2: OAuth Client Credentials
    print("\n=== Test 2: OAuth Client Credentials ===")
    try:
        response = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json", "User-Agent": "EA-Agent/1.0"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            token_data = response.json()
            if "access_token" in token_data:
                print(f"✅ SUCCESS: Got access token")
                return token_data["access_token"]

    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test 3: GitHub App API
    print("\n=== Test 3: GitHub App API ===")
    try:
        response = requests.post(
            "https://api.github.com/app/oauth/token",
            headers={"Accept": "application/json", "User-Agent": "EA-Agent/1.0"},
            auth=(client_id, client_secret),
            json={"grant_type": "client_credentials"},
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            token_data = response.json()
            if "access_token" in token_data:
                print(f"✅ SUCCESS: Got access token")
                return token_data["access_token"]

    except Exception as e:
        print(f"❌ FAILED: {e}")

    # Test 4: Check what type of app this might be
    print("\n=== Test 4: App Type Detection ===")
    try:
        # Try to get app info
        response = requests.get(
            f"https://api.github.com/apps/{1496943}",
            headers={"Accept": "application/json", "User-Agent": "EA-Agent/1.0"},
        )
        print(f"App Info Status: {response.status_code}")
        if response.status_code == 200:
            app_info = response.json()
            print(f"App Name: {app_info.get('name', 'Unknown')}")
            print(f"App Type: GitHub App")
        else:
            print("This might be an OAuth App, not a GitHub App")

    except Exception as e:
        print(f"❌ App detection failed: {e}")

    return None


if __name__ == "__main__":
    token = test_direct_api_calls()
    if token:
        print(f"\n🎉 Found working authentication method!")
        print(f"Token: {token[:20]}...")
    else:
        print(f"\n❌ No working authentication method found")
