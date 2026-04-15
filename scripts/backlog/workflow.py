"""
LangGraph workflow orchestration
"""

from langgraph.graph import StateGraph, END

from .state import BacklogState
from .llm_nodes import architect_node, refiner_node, publisher_node


def build_backlog_graph():
    """Create and compile the LangGraph workflow"""
    graph = StateGraph(BacklogState)

    # Add nodes
    graph.add_node("architect", architect_node)
    graph.add_node("refiner", refiner_node)
    graph.add_node("publisher", publisher_node)

    # Linear orchestration: Architect -> Refiner -> Publisher -> END
    graph.add_edge("architect", "refiner")
    graph.add_edge("refiner", "publisher")
    graph.add_edge("publisher", END)

    # Set entry point
    graph.set_entry_point("architect")

    return graph.compile()


def run_backlog_manager(dry_run: bool = False) -> BacklogState:
    """
    Run the backlog manager agent
    
    Args:
        dry_run: If True, stop after Refiner node (don't publish to GitHub)
    
    Returns:
        Final state after workflow execution
    """
    from .document_loader import load_docs
    
    print("=" * 70)
    print("🚀 BACKLOG MANAGER STARTED")
    print("=" * 70)

    # Load documentation
    print("\n📚 Loading architecture documentation...")
    docs_content = load_docs()

    if not docs_content:
        print("❌ No documentation files found!")
        return {
            "docs_content": {},
            "draft_issues": [],
            "refined_issues": [],
            "published_issue_numbers": [],
            "errors": ["No documentation files found"],
        }

    # Initialize state
    initial_state: BacklogState = {
        "docs_content": docs_content,
        "draft_issues": [],
        "refined_issues": [],
        "published_issue_numbers": [],
        "errors": [],
    }

    # Build and run graph
    agent = build_backlog_graph()

    print(f"\n🔄 Running workflow (dry_run={dry_run})...")
    final_state = agent.invoke(initial_state)

    # Handle dry-run: stop after refiner
    if dry_run:
        print("\n🛑 DRY RUN MODE: Not publishing to GitHub")
        final_state["published_issue_numbers"] = []
    else:
        # If Publisher node was skipped, run it now
        if not final_state["published_issue_numbers"] and final_state["refined_issues"]:
            print("\n📤 Running Publisher node...")
            final_state = publisher_node(final_state)

    # Summary
    print("\n" + "=" * 70)
    print("📊 WORKFLOW SUMMARY")
    print("=" * 70)
    print(f"📄 Docs loaded: {len(final_state['docs_content'])}")
    print(f"📝 Draft issues: {len(final_state['draft_issues'])}")
    print(f"✨ Refined issues: {len(final_state['refined_issues'])}")
    print(f"✅ Published issues: {len(final_state['published_issue_numbers'])}")

    if final_state["published_issue_numbers"]:
        print(f"\n🎉 Issue Numbers: {final_state['published_issue_numbers']}")

    if final_state["errors"]:
        print(f"\n⚠️  Errors ({len(final_state['errors'])}):")
        for error in final_state["errors"]:
            print(f"   - {error}")

    print("=" * 70)

    return final_state
