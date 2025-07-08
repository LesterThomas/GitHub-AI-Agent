"""Tests for YAML prompt configuration loading."""

import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from github_ai_agent.config import (
    load_prompts,
    get_system_prompt,
    get_human_message_template,
    get_tool_description,
)


def test_load_prompts_success():
    """Test that prompts can be loaded from YAML file."""
    # Create a temporary YAML file with test prompts
    test_prompts = {
        "system_prompt": "Test system prompt for {target_owner}/{target_repo}",
        "human_message_template": "Test human message with issue #{issue_number}: {issue_title}",
        "tool_descriptions": {
            "test_tool": "Test tool description"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_prompts, f)
        temp_file = f.name
    
    try:
        # Mock the prompts file path
        with patch('github_ai_agent.config.os.path.join', return_value=temp_file):
            prompts = load_prompts()
            
        assert prompts["system_prompt"] == test_prompts["system_prompt"]
        assert prompts["human_message_template"] == test_prompts["human_message_template"]
        assert prompts["tool_descriptions"]["test_tool"] == "Test tool description"
    finally:
        os.unlink(temp_file)


def test_load_prompts_file_not_found():
    """Test that FileNotFoundError is raised when prompts file doesn't exist."""
    with patch('github_ai_agent.config.os.path.join', return_value='/nonexistent/path.yaml'):
        with pytest.raises(FileNotFoundError, match="Prompts configuration file not found"):
            load_prompts()


def test_load_prompts_invalid_yaml():
    """Test that ValueError is raised for invalid YAML."""
    # Create a temporary file with invalid YAML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: content: [")
        temp_file = f.name
    
    try:
        with patch('github_ai_agent.config.os.path.join', return_value=temp_file):
            with pytest.raises(ValueError, match="Invalid YAML in prompts configuration"):
                load_prompts()
    finally:
        os.unlink(temp_file)


def test_get_system_prompt():
    """Test system prompt generation with target repository information."""
    test_prompts = {
        "system_prompt": "System prompt for {target_owner}/{target_repo}",
        "human_message_template": "Human message",
        "tool_descriptions": {}
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_prompts, f)
        temp_file = f.name
    
    try:
        with patch('github_ai_agent.config.os.path.join', return_value=temp_file):
            prompt = get_system_prompt("TestOwner", "TestRepo")
            
        assert prompt == "System prompt for TestOwner/TestRepo"
    finally:
        os.unlink(temp_file)


def test_get_human_message_template():
    """Test human message template generation with issue information."""
    test_prompts = {
        "system_prompt": "System prompt",
        "human_message_template": "Issue #{issue_number}: {issue_title} in {target_owner}/{target_repo}\nDescription: {issue_description}",
        "tool_descriptions": {}
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_prompts, f)
        temp_file = f.name
    
    try:
        with patch('github_ai_agent.config.os.path.join', return_value=temp_file):
            message = get_human_message_template(
                target_owner="TestOwner",
                target_repo="TestRepo", 
                issue_number=123,
                issue_title="Test Issue",
                issue_description="Test description"
            )
            
        expected = "Issue #123: Test Issue in TestOwner/TestRepo\nDescription: Test description"
        assert message == expected
    finally:
        os.unlink(temp_file)


def test_get_tool_description():
    """Test tool description retrieval."""
    test_prompts = {
        "system_prompt": "System prompt",
        "human_message_template": "Human message",
        "tool_descriptions": {
            "create_file": "Creates a new file",
            "edit_file": "Edits an existing file"
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(test_prompts, f)
        temp_file = f.name
    
    try:
        with patch('github_ai_agent.config.os.path.join', return_value=temp_file):
            # Test existing tool
            description = get_tool_description("create_file")
            assert description == "Creates a new file"
            
            # Test non-existing tool (should return default)
            description = get_tool_description("unknown_tool") 
            assert description == "Tool: unknown_tool"
    finally:
        os.unlink(temp_file)


def test_actual_prompts_file_structure():
    """Test that the actual prompts.yaml file has the expected structure."""
    # This test checks the real prompts file in the project
    prompts = load_prompts()
    
    # Check that all required keys exist
    assert "system_prompt" in prompts
    assert "human_message_template" in prompts
    assert "tool_descriptions" in prompts
    
    # Check that tool descriptions exist for all expected tools
    expected_tools = [
        "create_file_in_repo",
        "list_files_in_repo", 
        "read_file_from_repo",
        "edit_file_in_repo"
    ]
    
    for tool in expected_tools:
        assert tool in prompts["tool_descriptions"]
        assert isinstance(prompts["tool_descriptions"][tool], str)
        assert len(prompts["tool_descriptions"][tool]) > 0
    
    # Check that prompts are strings and not empty
    assert isinstance(prompts["system_prompt"], str)
    assert len(prompts["system_prompt"]) > 0
    assert isinstance(prompts["human_message_template"], str)
    assert len(prompts["human_message_template"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])