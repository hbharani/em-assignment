"""
LangGraph Agent for GitHub Backlog Management
Reads architecture docs and creates issues via Gemini + gh CLI
"""

import json
import subprocess
from pathlib import Path
from typing import TypedDict, Any

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate


# ============================================================================
# STATE DEFINITION
# ============================================================================

class BacklogState(TypedDict):
    """State for the backlog management workflow"""
    docs_content: dict[str, str]  # filename -> content mapping
    draft_issues: list[dict[str, Any]]  # Draft issues from Architect
    refined_issues: list[dict[str, Any]]  # Refined issues from Refiner
    published_issue_numbers: list[int]  # GitHub issue numbers created by Publisher
    errors: list[str]  # Track any errors during execution


# ============================================================================
# NODE 1: THE ARCHITECT
# ============================================================================

def architect_node(state: BacklogState) -> BacklogState:
    """
    Node 1: Read architecture docs and draft 12-15 GitHub issues using Gemini
    """
    print("\n🏗️  THE ARCHITECT: Reading docs and drafting issues...")

    # Initialize LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
    )

    # Prepare docs summary for the prompt
    docs_summary = "\n".join(
        [f"## {name}\n{content}\n" for name, content in state["docs_content"].items()]
    )

    # Create prompt template
    prompt = ChatPromptTemplate.from_template(
        """You are a technical architect analyzing system design documentation.

Based on the following architecture documentation, generate 12-15 GitHub issues that cover:
1. Core infrastructure setup (FastAPI gateway, LangGraph orchestrator, workers)
2. Redis Streams implementation
3. Circuit breaker implementation
4. PostgreSQL persistence layer
5. LangSmith integration
6. Kubernetes deployment configurations

For EACH issue, provide:
- A concise title (50-70 chars)
- A detailed body with:
  - User Story (As a..., I want..., So that...)
  - Acceptance Criteria (numbered checklist)
  - Technical notes (architecture references, key dependencies)

Format as a JSON array of objects with keys: "title", "body"

ARCHITECTURE DOCS:
{docs}

Generate the issues now:"""
    )

    # Create chain and invoke
    chain = prompt | llm
    response = chain.invoke({"docs": docs_summary})
    response_text = response.content

    # Parse JSON response
    try:
        # Extract JSON from response (may be wrapped in markdown code blocks)
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text

        draft_issues = json.loads(json_str)
        if not isinstance(draft_issues, list):
            draft_issues = [draft_issues]

        print(f"✅ Generated {len(draft_issues)} draft issues")
        state["draft_issues"] = draft_issues
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse Gemini response as JSON: {str(e)}"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        state["draft_issues"] = []

    return state


# ============================================================================
# NODE 2: THE REFINER
# ============================================================================

def refiner_node(state: BacklogState) -> BacklogState:
    """
    Node 2: Re-evaluate draft issues to ensure they correctly reference
    Redis Streams and Circuit Breakers
    """
    print("\n🔧 THE REFINER: Validating Redis Streams and Circuit Breaker references...")

    if not state["draft_issues"]:
        print("❌ No draft issues to refine")
        return state

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
    )

    # Create refinement prompt
    prompt = ChatPromptTemplate.from_template(
        """Review and refine these GitHub issues to ensure they properly reference:
1. Redis Streams (async task distribution, consumer groups, exactly-once delivery)
2. Circuit Breaker patterns (CLOSED/OPEN/HALF_OPEN states, failure thresholds)

For EACH issue, ensure:
- Technical accuracy regarding Redis Streams or Circuit Breaker usage
- Clear acceptance criteria that test these specific mechanisms
- Proper sequencing (e.g., Circuit Breaker issues should reference Redis task handling)

If an issue is unclear or missing these references, enhance it.
Keep the JSON format: array of objects with "title" and "body" keys.

DRAFT ISSUES:
{issues}

Return the refined issues as valid JSON array:"""
    )

    draft_json = json.dumps(state["draft_issues"], indent=2)
    chain = prompt | llm
    response = chain.invoke({"issues": draft_json})
    response_text = response.content

    try:
        # Extract JSON
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text

        refined_issues = json.loads(json_str)
        if not isinstance(refined_issues, list):
            refined_issues = [refined_issues]

        print(f"✅ Refined {len(refined_issues)} issues")
        state["refined_issues"] = refined_issues
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse Refiner response as JSON: {str(e)}"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        state["refined_issues"] = state["draft_issues"]

    return state


# ============================================================================
# HELPER FUNCTIONS FOR PROJECT & ISSUE MANAGEMENT
# ============================================================================

def get_or_create_project(project_title: str = "em-assignment Backlog") -> str | None:
    """
    Get existing project or create a new one.
    Returns project number (for use with gh CLI) or None if failed.
    """
    print(f"\n📋 Checking for project: {project_title}")

    try:
        # List existing projects
        result = subprocess.run(
            "gh project list --format json",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            try:
                projects = json.loads(result.stdout)
                # Find project by title
                for project in projects:
                    if project.get("title") == project_title:
                        project_num = project.get("number")
                        print(f"✅ Found existing project: #{project_num} ({project_title})")
                        return str(project_num)
            except json.JSONDecodeError:
                pass

        # Project doesn't exist, create it
        print(f"📝 Creating new project: {project_title}")
        create_result = subprocess.run(
            f'gh project create --title "{project_title}" --format json',
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if create_result.returncode == 0:
            try:
                created_project = json.loads(create_result.stdout)
                project_num = created_project.get("number")
                print(f"✅ Created new project: #{project_num}")
                return str(project_num)
            except json.JSONDecodeError:
                pass

        return None

    except Exception as e:
        print(f"⚠️  Could not manage project: {str(e)}")
        return None


def issue_exists(title: str) -> int | None:
    """
    Check if an issue with the given title already exists.
    Returns issue number if found, None otherwise.
    """
    try:
        # Search for issue by title
        title_escaped = json.dumps(title)
        result = subprocess.run(
            f"gh issue list --search {title_escaped} --state all --format json",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            try:
                issues = json.loads(result.stdout)
                for issue in issues:
                    if issue.get("title") == title:
                        return issue.get("number")
            except json.JSONDecodeError:
                pass

        return None

    except Exception as e:
        print(f"⚠️  Error checking issue existence: {str(e)}")
        return None


def add_issue_to_project(issue_number: int, project_number: str) -> bool:
    """
    Add an issue to a project.
    Returns True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            f"gh project item-add {project_number} --issue {issue_number}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print(f"  📌 Added to project: #{issue_number}")
            return True
        else:
            print(f"  ⚠️  Could not add to project: {result.stderr}")
            return False

    except Exception as e:
        print(f"  ⚠️  Error adding to project: {str(e)}")
        return False


# ============================================================================
# NODE 3: THE PUBLISHER
# ============================================================================

def publisher_node(state: BacklogState) -> BacklogState:
    """
    Node 3: Use gh CLI to create issues on GitHub and add them to a project
    """
    print("\n📤 THE PUBLISHER: Managing GitHub issues and project...")

    if not state["refined_issues"]:
        print("❌ No refined issues to publish")
        return state

    # Check if gh CLI is available
    try:
        check_result = subprocess.run(
            "gh --version",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if check_result.returncode != 0:
            error_msg = "gh CLI is not installed or not in PATH. Install it from https://github.com/cli/cli"
            print(f"❌ {error_msg}")
            state["errors"].append(error_msg)
            return state
    except Exception as e:
        error_msg = f"Failed to verify gh CLI: {str(e)}"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        return state

    # Create or get project
    project_number = get_or_create_project()
    if not project_number:
        warning_msg = "Could not create/find project, issues will be created without project assignment"
        print(f"⚠️  {warning_msg}")
        state["errors"].append(warning_msg)

    published_numbers = []
    skipped_numbers = []

    for i, issue in enumerate(state["refined_issues"], 1):
        title = issue.get("title", "").strip()
        body = issue.get("body", "").strip()

        if not title or not body:
            error_msg = f"Issue {i} missing title or body"
            print(f"❌ {error_msg}")
            state["errors"].append(error_msg)
            continue

        # Check if issue already exists (idempotency)
        existing_issue_num = issue_exists(title)
        if existing_issue_num:
            print(f"⏭️  Issue already exists (idempotent): #{existing_issue_num} - {title}")
            skipped_numbers.append(existing_issue_num)
            # Try to add to project if not already there
            if project_number:
                add_issue_to_project(existing_issue_num, project_number)
            continue

        try:
            # Create new issue
            title_escaped = json.dumps(title)
            body_escaped = json.dumps(body)
            cmd = f"gh issue create --title {title_escaped} --body {body_escaped}"
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,  # Run from repo root
                capture_output=True,
                text=True,
                timeout=30,
                shell=True,
            )

            if result.returncode != 0:
                error_msg = f"gh CLI error for issue '{title}': {result.stderr}"
                print(f"❌ {error_msg}")
                state["errors"].append(error_msg)
                continue

            # Extract issue number from output (e.g., "Created issue #42")
            output = result.stdout.strip()
            if "Created issue" in output and "#" in output:
                issue_num_str = output.split("#")[1].split()[0]
                issue_number = int(issue_num_str)
                published_numbers.append(issue_number)
                print(f"✅ Created issue #{issue_number}: {title}")

                # Add to project
                if project_number:
                    add_issue_to_project(issue_number, project_number)
            else:
                print(f"⚠️  Issue created but couldn't parse number: {output}")

        except subprocess.TimeoutExpired:
            error_msg = f"Timeout creating issue: {title}"
            print(f"❌ {error_msg}")
            state["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"Exception creating issue '{title}': {str(e)}"
            print(f"❌ {error_msg}")
            state["errors"].append(error_msg)

    state["published_issue_numbers"] = published_numbers
    print(f"\n✅ Created {len(published_numbers)} new issues")
    print(f"⏭️  Skipped {len(skipped_numbers)} existing issues (idempotent)")
    print(f"📊 Total issues involved: {len(published_numbers) + len(skipped_numbers)}")

    return state


# ============================================================================
# LOAD DOCS
# ============================================================================

def load_docs() -> dict[str, str]:
    """Load all markdown files from docs/ and README.md (hardcoded paths)"""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    docs_dir = repo_root / "docs"

    docs_content = {}

    # Load top-level README.md first
    readme_path = repo_root / "README.md"
    if readme_path.exists():
        try:
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
                docs_content["README.md"] = content
                print(f"📖 Loaded: README.md")
        except Exception as e:
            print(f"⚠️  Failed to load README.md: {e}")

    # Recursively find all .md files in docs/
    if docs_dir.exists():
        for md_file in docs_dir.rglob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Use relative path as key
                    rel_path = md_file.relative_to(docs_dir)
                    key = f"docs/{rel_path}"
                    docs_content[key] = content
                    print(f"📖 Loaded: {key}")
            except Exception as e:
                print(f"⚠️  Failed to load {md_file}: {e}")
    else:
        print(f"⚠️  docs/ directory not found at {docs_dir}")

    return docs_content


# ============================================================================
# BUILD GRAPH
# ============================================================================

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


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_backlog_manager(dry_run: bool = False):
    """
    Run the backlog manager agent
    
    Args:
        dry_run: If True, stop after Refiner node (don't publish to GitHub)
    """
    print("=" * 70)
    print("🚀 BACKLOG MANAGER STARTED")
    print("=" * 70)

    # Load documentation
    print("\n📚 Loading architecture documentation...")
    docs_content = load_docs()

    if not docs_content:
        print("❌ No documentation files found!")
        return

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


if __name__ == "__main__":
    import sys

    # Parse arguments
    dry_run = "--dry-run" in sys.argv

    run_backlog_manager(dry_run=dry_run)
