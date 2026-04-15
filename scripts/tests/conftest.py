"""
Shared pytest configuration and fixtures
"""

import pytest
from pathlib import Path
import sys


# Add scripts directory to path so imports work
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))


@pytest.fixture
def sample_backlog_state():
    """Fixture providing a sample BacklogState"""
    return {
        "docs_content": {
            "README.md": "# Project",
            "docs/architecture.md": "# Architecture"
        },
        "draft_issues": [
            {
                "title": "Setup FastAPI",
                "body": "Set up FastAPI server"
            }
        ],
        "refined_issues": [
            {
                "title": "Setup FastAPI",
                "body": {"user_story": "As a developer", "acceptance_criteria": ["Set up server"]},
                "milestone": "foundation"
            }
        ],
        "published_issue_numbers": [1, 2],
        "errors": [],
    }


@pytest.fixture
def sample_issue():
    """Fixture providing a sample GitHub issue"""
    return {
        "title": "Setup FastAPI gateway",
        "body": {
            "user_story": "As a developer, I want a FastAPI server",
            "acceptance_criteria": [
                "Server starts on port 8000",
                "Health check endpoint works",
                "Handles GET requests"
            ],
            "technical_notes": "Use FastAPI with uvicorn"
        },
        "labels": ["EPIC"],
        "milestone": "foundation"
    }


@pytest.fixture
def sample_docs_content():
    """Fixture providing sample documentation content"""
    return {
        "README.md": """# AI Agents Platform
A production-grade intelligent agent platform.
""",
        "docs/architecture/01-overview.md": """# Architecture Overview
This is the main architecture document.
""",
        "docs/architecture/02-c4-diagrams.md": """# C4 Diagrams
System architecture diagrams.
""",
    }


@pytest.fixture
def temp_workspace(tmp_path):
    """Fixture providing a temporary workspace with docs structure"""
    # Create docs directory structure
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    
    arch_dir = docs_dir / "architecture"
    arch_dir.mkdir()
    
    # Create markdown files
    (tmp_path / "README.md").write_text("# Root README")
    (arch_dir / "01-overview.md").write_text("# Overview")
    (arch_dir / "02-c4-diagrams.md").write_text("# Diagrams")
    
    return tmp_path


@pytest.fixture
def mock_github_issue():
    """Fixture providing a mock GitHub API issue response"""
    return {
        "id": 1234567,
        "number": 42,
        "title": "Setup FastAPI",
        "body": "Configure FastAPI server",
        "state": "open",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z",
        "labels": [{"name": "EPIC"}],
        "milestone": {"title": "Foundation", "number": 1}
    }
