"""
Tests for issue helper functions
"""

import pytest
from backlog.issue_helpers import (
    normalize_issue_body,
    categorize_issue_to_milestone,
    get_sprint_labels,
)


class TestNormalizeIssueBody:
    """Tests for normalize_issue_body function"""
    
    def test_plain_text_body(self):
        """Test normalization of plain text body"""
        issue = {"body": "This is a simple issue body"}
        result = normalize_issue_body(issue)
        assert result == "This is a simple issue body"
    
    def test_empty_body(self):
        """Test normalization of empty body"""
        issue = {"body": ""}
        result = normalize_issue_body(issue)
        assert result == ""
    
    def test_missing_body_key(self):
        """Test issue without body key"""
        issue = {}
        result = normalize_issue_body(issue)
        assert result == ""
    
    def test_dict_body_with_user_story(self):
        """Test normalization of dict body with user story"""
        issue = {
            "body": {
                "user_story": "As a user, I want to...",
                "acceptance_criteria": ["Criteria 1", "Criteria 2"]
            }
        }
        result = normalize_issue_body(issue)
        assert "User Story" in result
        assert "As a user, I want to..." in result
        assert "Acceptance Criteria" in result
        assert "Criteria 1" in result
        assert "Criteria 2" in result
    
    def test_dict_body_with_technical_notes(self):
        """Test normalization of dict body with technical notes"""
        issue = {
            "body": {
                "user_story": "User story",
                "acceptance_criteria": ["Criteria 1"],
                "technical_notes": "Use FastAPI for this"
            }
        }
        result = normalize_issue_body(issue)
        assert "Technical Notes" in result
        assert "Use FastAPI for this" in result
    
    def test_dict_body_with_string_acceptance_criteria(self):
        """Test dict body with acceptance criteria as string"""
        issue = {
            "body": {
                "acceptance_criteria": "Single criteria string"
            }
        }
        result = normalize_issue_body(issue)
        assert "Single criteria string" in result
    
    def test_whitespace_trimming(self):
        """Test that whitespace is trimmed"""
        issue = {"body": "  Some content  \n\n"}
        result = normalize_issue_body(issue)
        assert result == "Some content"


class TestCategorizeIssueToMilestone:
    """Tests for categorize_issue_to_milestone function"""
    
    def test_foundation_keywords(self):
        """Test categorization of foundation issues"""
        titles = [
            "Setup FastAPI gateway",
            "Deploy to Kubernetes",
            "Configure Redis Streams",
            "Setup PostgreSQL database",
            "Create K8s StatefulSet",
            "Add ConfigMap for configuration"
        ]
        for title in titles:
            result = categorize_issue_to_milestone(title)
            assert result == "foundation", f"Failed for title: {title}"
    
    def test_chatbot_keywords(self):
        """Test categorization of chatbot issues"""
        titles = [
            "Implement LangGraph orchestrator",
            "Integrate Gemini API",
            "Add LangSmith tracing",
            "Build chatbot interface",
            "Add observability layer"
        ]
        for title in titles:
            result = categorize_issue_to_milestone(title)
            assert result == "chatbot", f"Failed for title: {title}"
    
    def test_workflows_keywords(self):
        """Test categorization of workflows issues"""
        titles = [
            "Implement circuit breaker pattern",
            "Add idempotency support",
            "Create recovery checkpoints",
            "Persist application state",
            "Implement fallback mechanism"
        ]
        for title in titles:
            result = categorize_issue_to_milestone(title)
            assert result == "workflows", f"Failed for title: {title}"
    
    def test_case_insensitivity(self):
        """Test that categorization is case-insensitive"""
        result1 = categorize_issue_to_milestone("SETUP FASTAPI GATEWAY")
        result2 = categorize_issue_to_milestone("setup fastapi gateway")
        result3 = categorize_issue_to_milestone("Setup FastAPI Gateway")
        
        assert result1 == result2 == result3 == "foundation"
    
    def test_default_to_foundation(self):
        """Test that unrecognized titles default to foundation"""
        result = categorize_issue_to_milestone("Some random issue title")
        assert result == "foundation"


class TestGetSprintLabels:
    """Tests for get_sprint_labels function"""
    
    def test_foundation_milestone_without_index(self):
        """Test sprint labels for foundation without index"""
        result = get_sprint_labels("foundation")
        assert len(result) == 1
        assert result[0] in ["Sprint 1", "Sprint 2"]
    
    def test_chatbot_milestone_without_index(self):
        """Test sprint labels for chatbot without index"""
        result = get_sprint_labels("chatbot")
        assert len(result) == 1
        assert result[0] in ["Sprint 3", "Sprint 4"]
    
    def test_workflows_milestone_without_index(self):
        """Test sprint labels for workflows without index"""
        result = get_sprint_labels("workflows")
        assert len(result) == 1
        assert result[0] in ["Sprint 5", "Sprint 6"]
    
    def test_foundation_with_index_even(self):
        """Test foundation sprint distribution with even index"""
        result = get_sprint_labels("foundation", issue_index=0)
        assert result == ["Sprint 1"]
    
    def test_foundation_with_index_odd(self):
        """Test foundation sprint distribution with odd index"""
        result = get_sprint_labels("foundation", issue_index=1)
        assert result == ["Sprint 2"]
    
    def test_chatbot_with_index_even(self):
        """Test chatbot sprint distribution with even index"""
        result = get_sprint_labels("chatbot", issue_index=0)
        assert result == ["Sprint 3"]
    
    def test_chatbot_with_index_odd(self):
        """Test chatbot sprint distribution with odd index"""
        result = get_sprint_labels("chatbot", issue_index=1)
        assert result == ["Sprint 4"]
    
    def test_workflows_with_index_cycling(self):
        """Test workflows sprint cycling"""
        results = [get_sprint_labels("workflows", issue_index=i) for i in range(6)]
        
        # Should cycle through Sprint 5 and 6
        assert results[0] == ["Sprint 5"]
        assert results[1] == ["Sprint 6"]
        assert results[2] == ["Sprint 5"]
        assert results[3] == ["Sprint 6"]
        assert results[4] == ["Sprint 5"]
        assert results[5] == ["Sprint 6"]
    
    def test_unknown_milestone_defaults(self):
        """Test that unknown milestone defaults to Sprint 1"""
        result = get_sprint_labels("unknown_milestone")
        assert result == ["Sprint 1"]
