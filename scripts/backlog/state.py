"""
State definition for backlog management workflow
"""

from typing import TypedDict, Any


class BacklogState(TypedDict):
    """State for the backlog management workflow"""
    docs_content: dict[str, str]  # filename -> content mapping
    draft_issues: list[dict[str, Any]]  # Draft issues from Architect
    refined_issues: list[dict[str, Any]]  # Refined issues from Refiner
    published_issue_numbers: list[int]  # GitHub issue numbers created by Publisher
    errors: list[str]  # Track any errors during execution
