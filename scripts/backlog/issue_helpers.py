"""
Helper functions for processing GitHub issues
"""

import json
import random


def normalize_issue_body(issue: dict) -> str:
    """
    Normalize issue body: converts nested structures to single markdown string.
    Handles both plain text bodies and nested structures (user_story, acceptance_criteria, etc)
    """
    body = issue.get("body", "")
    
    # If body is a dict, consolidate into markdown
    if isinstance(body, dict):
        sections = []
        if "user_story" in body:
            sections.append(f"## User Story\n{body['user_story']}")
        if "acceptance_criteria" in body:
            ac = body['acceptance_criteria']
            if isinstance(ac, list):
                criteria_text = "\n".join(f"- {item}" for item in ac)
            else:
                criteria_text = str(ac)
            sections.append(f"## Acceptance Criteria\n{criteria_text}")
        if "technical_notes" in body:
            sections.append(f"## Technical Notes\n{body['technical_notes']}")
        
        body = "\n\n".join(sections) if sections else str(body)
    
    return str(body).strip()


def categorize_issue_to_milestone(title: str) -> str:
    """
    Categorize an issue to a milestone based on keywords in title.
    Returns: milestone key (foundation, chatbot, workflows)
    """
    title_lower = title.lower()
    
    # Foundation: infrastructure, gateway, redis, postgresql, kubernetes, deployment
    if any(kw in title_lower for kw in ["fastapi", "gateway", "kubernetes", "redis", "postgresql", "deployment", "k8s", "statefulset", "configmap"]):
        return "foundation"
    
    # Chatbot: orchestrator, langraph, gemini, langsmith, observability
    if any(kw in title_lower for kw in ["langgraph", "orchestrator", "gemini", "langsmith", "chatbot", "observability", "tracing"]):
        return "chatbot"
    
    # Workflows: circuit breaker, idempotency, persistent, recovery, state
    if any(kw in title_lower for kw in ["circuit breaker", "idempotency", "checkpoint", "recovery", "state", "persistent", "fallback"]):
        return "workflows"
    
    # Default to foundation if unsure
    return "foundation"


def get_sprint_labels(milestone_key: str, issue_index: int = None) -> list[str]:
    """
    Get sprint label for an issue based on milestone.
    Returns: list with single sprint label (alternates within milestone)
    Foundation (Sprint 1-2) → rotates between "Sprint 1" and "Sprint 2"
    Chatbot (Sprint 3-4) → rotates between "Sprint 3" and "Sprint 4"
    Workflows (Sprint 5-6) → rotates between "Sprint 5" and "Sprint 6"
    
    If issue_index is provided, uses it to distribute evenly (for granular sprint assignment).
    """
    sprint_map = {
        "foundation": ["Sprint 1", "Sprint 2"],
        "chatbot": ["Sprint 3", "Sprint 4"],
        "workflows": ["Sprint 5", "Sprint 6"],
    }
    sprints = sprint_map.get(milestone_key, ["Sprint 1"])
    
    # If index is provided, use it for even distribution (e.g., even indices → Sprint 1, odd → Sprint 2)
    if issue_index is not None:
        return [sprints[issue_index % len(sprints)]]
    
    # Otherwise, randomly choose (backward compatibility)
    return [random.choice(sprints)]
