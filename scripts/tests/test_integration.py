"""
Integration tests for the backlog management workflow
"""

import pytest
from backlog.state import BacklogState
from backlog.issue_helpers import (
    normalize_issue_body,
    categorize_issue_to_milestone,
    get_sprint_labels,
)


class TestWorkflowIntegration:
    """Integration tests for complete workflow scenarios"""
    
    def test_complete_issue_processing_workflow(self, sample_docs_content):
        """Test complete issue processing from docs to state"""
        # Start with documentation
        initial_state: BacklogState = {
            "docs_content": sample_docs_content,
            "draft_issues": [],
            "refined_issues": [],
            "published_issue_numbers": [],
            "errors": [],
        }
        
        # Simulate creating draft issues
        draft_issues = [
            {
                "title": "Setup FastAPI gateway",
                "body": "Configure FastAPI server for infrastructure"
            },
            {
                "title": "Implement LangGraph orchestrator",
                "body": "Build workflow orchestration layer"
            }
        ]
        initial_state["draft_issues"] = draft_issues
        
        # Simulate refinement: normalize bodies and categorize
        refined = []
        for i, issue in enumerate(draft_issues):
            normalized_body = normalize_issue_body(issue)
            milestone = categorize_issue_to_milestone(issue["title"])
            sprint = get_sprint_labels(milestone, issue_index=i)
            
            refined_issue = {
                **issue,
                "body": normalized_body,
                "milestone": milestone,
                "sprint": sprint[0]
            }
            refined.append(refined_issue)
        
        initial_state["refined_issues"] = refined
        
        # Validate refined state
        assert len(initial_state["refined_issues"]) == 2
        assert initial_state["refined_issues"][0]["milestone"] == "foundation"
        assert initial_state["refined_issues"][1]["milestone"] == "chatbot"
        assert initial_state["refined_issues"][0]["sprint"] == "Sprint 1"
        assert initial_state["refined_issues"][1]["sprint"] == "Sprint 4"
    
    def test_error_tracking_workflow(self):
        """Test error tracking through workflow"""
        state: BacklogState = {
            "docs_content": {},
            "draft_issues": [],
            "refined_issues": [],
            "published_issue_numbers": [],
            "errors": [],
        }
        
        # Simulate errors at different stages
        state["errors"].append("Failed to load docs directory")
        state["errors"].append("GitHub API rate limit exceeded")
        
        assert len(state["errors"]) == 2
        assert "Failed to load docs directory" in state["errors"][0]
        assert "GitHub API rate limit exceeded" in state["errors"][1]
    
    def test_issue_categorization_and_sprint_assignment(self):
        """Test categorizing issues and assigning them to sprints"""
        test_issues = [
            {"title": "Setup FastAPI gateway", "index": 0},
            {"title": "Setup Redis Streams", "index": 1},
            {"title": "Deploy Kubernetes", "index": 2},
            {"title": "Implement LangGraph", "index": 3},
            {"title": "Add circuit breaker", "index": 4},
        ]
        
        categorized_issues = []
        for issue in test_issues:
            milestone = categorize_issue_to_milestone(issue["title"])
            sprints = get_sprint_labels(milestone, issue_index=issue["index"])
            
            categorized_issues.append({
                "title": issue["title"],
                "milestone": milestone,
                "sprint": sprints[0]
            })
        
        # Validate distribution
        foundation_issues = [i for i in categorized_issues if i["milestone"] == "foundation"]
        chatbot_issues = [i for i in categorized_issues if i["milestone"] == "chatbot"]
        workflow_issues = [i for i in categorized_issues if i["milestone"] == "workflows"]
        
        assert len(foundation_issues) > 0
        assert len(chatbot_issues) > 0
        assert len(workflow_issues) > 0


class TestIssueBatchProcessing:
    """Tests for processing multiple issues together"""
    
    def test_batch_normalize_bodies(self):
        """Test normalizing multiple issue bodies"""
        issues = [
            {
                "body": "Simple text body"
            },
            {
                "body": {
                    "user_story": "As a user",
                    "acceptance_criteria": ["Criteria 1", "Criteria 2"]
                }
            },
            {
                "body": ""
            }
        ]
        
        normalized = [normalize_issue_body(issue) for issue in issues]
        
        assert len(normalized) == 3
        assert "Simple text body" in normalized[0]
        assert "As a user" in normalized[1]
        assert normalized[2] == ""
    
    def test_batch_categorize_and_label(self):
        """Test categorizing and labeling a batch of issues"""
        titles = [
            "Setup FastAPI",
            "Configure PostgreSQL",
            "Implement LangGraph",
            "Add circuit breaker",
            "Setup Redis",
        ]
        
        results = []
        for i, title in enumerate(titles):
            milestone = categorize_issue_to_milestone(title)
            sprint = get_sprint_labels(milestone, issue_index=i)
            results.append({
                "title": title,
                "milestone": milestone,
                "sprint": sprint[0]
            })
        
        # Check distribution
        milestones = [r["milestone"] for r in results]
        assert "foundation" in milestones
        assert "chatbot" in milestones
        
        # Check sprint assignments
        sprints = [r["sprint"] for r in results]
        for sprint in sprints:
            assert sprint.startswith("Sprint ")


class TestStateProgression:
    """Tests for state transitions through workflow stages"""
    
    def test_state_progression_empty_to_draft(self):
        """Test state transitioning from empty to having draft issues"""
        state: BacklogState = {
            "docs_content": {},
            "draft_issues": [],
            "refined_issues": [],
            "published_issue_numbers": [],
            "errors": [],
        }
        
        # Add draft issues
        state["draft_issues"] = [
            {"title": "Issue 1"},
            {"title": "Issue 2"},
        ]
        
        assert len(state["draft_issues"]) == 2
        assert len(state["refined_issues"]) == 0
        assert len(state["published_issue_numbers"]) == 0
    
    def test_state_progression_draft_to_refined(self):
        """Test state transitioning from draft to refined issues"""
        state: BacklogState = {
            "docs_content": {},
            "draft_issues": [
                {"title": "Setup FastAPI", "body": "text"}
            ],
            "refined_issues": [],
            "published_issue_numbers": [],
            "errors": [],
        }
        
        # Move to refined
        for draft in state["draft_issues"]:
            milestone = categorize_issue_to_milestone(draft["title"])
            refined = {
                **draft,
                "milestone": milestone,
                "normalized_body": normalize_issue_body(draft)
            }
            state["refined_issues"].append(refined)
        
        assert len(state["refined_issues"]) == 1
        assert state["refined_issues"][0]["milestone"] == "foundation"
    
    def test_state_progression_refined_to_published(self):
        """Test state transitioning from refined to published"""
        state: BacklogState = {
            "docs_content": {},
            "draft_issues": [],
            "refined_issues": [
                {"title": "Setup FastAPI", "milestone": "foundation"}
            ],
            "published_issue_numbers": [],
            "errors": [],
        }
        
        # Simulate publishing
        state["published_issue_numbers"] = [42, 43]
        
        assert len(state["published_issue_numbers"]) == 2
        assert 42 in state["published_issue_numbers"]
        assert 43 in state["published_issue_numbers"]


class TestErrorHandling:
    """Tests for error handling in workflow"""
    
    def test_graceful_handling_missing_fields(self):
        """Test graceful handling when issue is missing fields"""
        issue_without_body = {"title": "Issue without body"}
        
        result = normalize_issue_body(issue_without_body)
        assert isinstance(result, str)
    
    def test_graceful_handling_invalid_body_type(self):
        """Test handling of unexpected body types"""
        issues = [
            {"body": None},
            {"body": 123},
            {"body": []},
        ]
        
        for issue in issues:
            result = normalize_issue_body(issue)
            # Should convert to string representation
            assert isinstance(result, str)
    
    def test_state_with_multiple_errors(self):
        """Test state tracking multiple errors"""
        state: BacklogState = {
            "docs_content": {},
            "draft_issues": [],
            "refined_issues": [],
            "published_issue_numbers": [],
            "errors": [
                "Error 1: Failed to load docs",
                "Error 2: GitHub API failed",
                "Error 3: LLM timeout",
            ],
        }
        
        assert len(state["errors"]) == 3
        assert all(isinstance(e, str) for e in state["errors"])


@pytest.mark.integration
class TestFullWorkflowSimulation:
    """Simulate complete workflow execution"""
    
    def test_complete_workflow_execution(self, sample_backlog_state):
        """Test simulating complete workflow execution"""
        state = sample_backlog_state
        
        # Verify initial state
        assert len(state["docs_content"]) > 0
        assert len(state["draft_issues"]) > 0
        
        # Simulate full workflow
        processed_issues = []
        for i, draft in enumerate(state["draft_issues"]):
            normalized = normalize_issue_body(draft)
            milestone = categorize_issue_to_milestone(draft["title"])
            sprint = get_sprint_labels(milestone, issue_index=i)
            
            processed_issues.append({
                "original": draft,
                "normalized_body": normalized,
                "milestone": milestone,
                "sprint": sprint[0]
            })
        
        # Add to state
        state["refined_issues"] = [
            {
                **item["original"],
                "body": item["normalized_body"],
                "milestone": item["milestone"],
                "sprint": item["sprint"]
            }
            for item in processed_issues
        ]
        
        state["published_issue_numbers"] = [1, 2, 3]
        
        # Final validation
        assert len(state["refined_issues"]) > 0
        assert len(state["published_issue_numbers"]) == 3
        assert 1 in state["published_issue_numbers"]
