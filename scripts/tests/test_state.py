"""
Tests for the BacklogState data structure
"""

import pytest
from backlog.state import BacklogState


def test_backlog_state_initialization():
    """Test creating a valid BacklogState"""
    state: BacklogState = {
        "docs_content": {"README.md": "# Project"},
        "draft_issues": [],
        "refined_issues": [],
        "published_issue_numbers": [],
        "errors": [],
    }
    
    assert state["docs_content"] == {"README.md": "# Project"}
    assert state["draft_issues"] == []
    assert state["refined_issues"] == []
    assert state["published_issue_numbers"] == []
    assert state["errors"] == []


def test_backlog_state_with_data():
    """Test BacklogState with populated data"""
    state: BacklogState = {
        "docs_content": {
            "README.md": "# Project",
            "docs/architecture.md": "# Architecture"
        },
        "draft_issues": [
            {"title": "Setup FastAPI", "body": "Set up FastAPI server"}
        ],
        "refined_issues": [
            {"title": "Setup FastAPI", "body": "Set up FastAPI server", "milestone": "foundation"}
        ],
        "published_issue_numbers": [1, 2, 3],
        "errors": [],
    }
    
    assert len(state["docs_content"]) == 2
    assert len(state["draft_issues"]) == 1
    assert len(state["refined_issues"]) == 1
    assert state["published_issue_numbers"] == [1, 2, 3]


def test_backlog_state_with_errors():
    """Test BacklogState error tracking"""
    state: BacklogState = {
        "docs_content": {},
        "draft_issues": [],
        "refined_issues": [],
        "published_issue_numbers": [],
        "errors": ["Failed to load docs", "GitHub API error"],
    }
    
    assert len(state["errors"]) == 2
    assert "Failed to load docs" in state["errors"]


def test_backlog_state_all_keys_present():
    """Test that all required keys are present in BacklogState"""
    state: BacklogState = {
        "docs_content": {},
        "draft_issues": [],
        "refined_issues": [],
        "published_issue_numbers": [],
        "errors": [],
    }
    
    required_keys = {"docs_content", "draft_issues", "refined_issues", "published_issue_numbers", "errors"}
    assert set(state.keys()) == required_keys
