"""
GitHub operations: projects, milestones, labels, issues, and epics
"""

import json
import subprocess
from pathlib import Path


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
            f'gh project create --title "{project_title}"',
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
            f"gh issue list --search {title_escaped} --state all --json number,title",
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


def get_or_create_milestones() -> dict[str, str]:
    """
    Create or get milestones for the project.
    Returns: dict mapping milestone name to title (for use with gh CLI)
    Milestones: Foundation (Sprint 1-2), Chatbot (Sprint 3-4), Workflows (Sprint 5-6)
    """
    print(f"\n🎯 Managing milestones...")
    
    milestones_config = {
        "foundation": "Foundation (Sprint 1-2)",
        "chatbot": "Chatbot (Sprint 3-4)",
        "workflows": "Workflows (Sprint 5-6)",
    }
    
    milestones_map = {}
    
    try:
        # List existing milestones via GitHub REST API
        result = subprocess.run(
            "gh api repos/:owner/:repo/milestones --format json",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        existing = {}
        if result.returncode == 0:
            try:
                milestones = json.loads(result.stdout)
                for milestone in milestones:
                    existing[milestone.get("title")] = milestone.get("title")
            except json.JSONDecodeError:
                pass
        
        # Create missing milestones via GitHub REST API
        for key, title in milestones_config.items():
            if title in existing:
                print(f"  ✅ Found milestone: {title}")
                milestones_map[key] = title
            else:
                print(f"  📝 Creating milestone: {title}")
                create_result = subprocess.run(
                    f'gh api repos/:owner/:repo/milestones -f title="{title}" -f description="Part of em-assignment Backlog"',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if create_result.returncode == 0:
                    print(f"  ✅ Created milestone: {title}")
                    milestones_map[key] = title
                else:
                    print(f"  ⚠️  Could not create milestone {title}: {create_result.stderr}")
    
    except Exception as e:
        print(f"⚠️  Error managing milestones: {str(e)}")
    
    return milestones_map


def ensure_sprint_labels() -> bool:
    """
    Create Sprint 1-6 labels, story label, and EPIC label if they don't exist.
    Returns: True if all labels exist or were created, False otherwise
    """
    print(f"\n🏷️  Ensuring labels exist...")
    
    all_labels = {
        "story": "FC2929",    # Red (for story issues)
        "EPIC": "3E1F79",     # Purple (for epic issues)
        "Sprint 1": "0366D6",  # Blue
        "Sprint 2": "0366D6",  # Blue
        "Sprint 3": "28A745",  # Green
        "Sprint 4": "28A745",  # Green
        "Sprint 5": "D73A49",  # Red
        "Sprint 6": "D73A49",  # Red
    }
    
    try:
        # Check existing labels
        result = subprocess.run(
            "gh api repos/:owner/:repo/labels",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        
        existing_labels = set()
        if result.returncode == 0:
            try:
                labels = json.loads(result.stdout)
                for label in labels:
                    existing_labels.add(label.get("name"))
            except json.JSONDecodeError:
                pass
        
        # Create missing labels
        all_created = True
        for label_name, color in all_labels.items():
            if label_name in existing_labels:
                print(f"  ✅ {label_name} label already exists")
                continue
            
            print(f"  📝 Creating {label_name} label...")
            
            # Build description based on label type
            if label_name == "story":
                desc = "Story issue - user-facing feature or task"
            elif label_name == "EPIC":
                desc = "Epic issue - spans multiple sprints"
            else:
                desc = f"Work scheduled for {label_name}"
            
            create_result = subprocess.run(
                f'gh api repos/:owner/:repo/labels -f name="{label_name}" -f color={color} -f description="{desc}"',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if create_result.returncode == 0:
                print(f"  ✅ Created {label_name} label")
            else:
                print(f"  ⚠️  Could not create {label_name} label: {create_result.stderr[:100]}")
                all_created = False
        
        return all_created
    
    except Exception as e:
        print(f"⚠️  Error managing sprint labels: {str(e)}")
        return False


def create_epic_issues(milestones_map: dict[str, str]) -> dict[str, int]:
    """
    Create 3 Epic-level issues (one per milestone track).
    Returns: dict mapping milestone_key to epic issue number
    """
    print(f"\n📍 Creating Epic-level issues...")
    
    epics = {
        "foundation": {
            "title": "EPIC: Infrastructure & Architecture Foundation",
            "body": """# Infrastructure & Architecture Foundation

Parent epic for all work related to platform infrastructure, Kubernetes deployment, database setup, and core gateway implementation.

## Scope (Sprints 1-2)
- FastAPI Gateway core logic
- Kubernetes deployments and StatefulSets
- PostgreSQL database schema and persistence
- Redis Streams setup and consumer groups
- Configuration management (ConfigMaps, Secrets)

## Related Issues
This epic tracks foundation work. See child issues for specific implementation tasks.""",
            "milestone": "Foundation (Sprint 1-2)"
        },
        "chatbot": {
            "title": "EPIC: AI Chatbot Platform",
            "body": """# AI Chatbot Platform

Parent epic for all work related to the LangGraph orchestrator, AI workflow execution, and observability.

## Scope (Sprints 3-4)
- LangGraph Orchestrator core workflow engine
- Agent worker pods core execution logic
- RAG/LLM integration with Gemini
- LangSmith observability and tracing
- Session management and context handling

## Related Issues
This epic tracks chatbot platform work. See child issues for specific implementation tasks.""",
            "milestone": "Chatbot (Sprint 3-4)"
        },
        "workflows": {
            "title": "EPIC: Resilience & State Management",
            "body": """# Resilience & State Management

Parent epic for all work related to circuit breaker patterns, state persistence, and resilience capabilities.

## Scope (Sprints 5-6)
- Circuit Breaker pattern implementation and integration
- Two-tier state persistence (Redis + PostgreSQL)
- Idempotency and request deduplication
- Error handling and fallback strategies
- Monitoring and alerting

## Related Issues
This epic tracks resilience work. See child issues for specific implementation tasks.""",
            "milestone": "Workflows (Sprint 5-6)"
        }
    }
    
    epic_numbers = {}
    repo_root = Path(__file__).parent.parent.parent
    
    for epic_key, epic_data in epics.items():
        try:
            title_escaped = json.dumps(epic_data["title"])
            milestone_escaped = json.dumps(epic_data["milestone"])
            
            # Write body to temp file
            temp_body_file = Path(__file__).parent / "temp_epic_body.md"
            temp_body_file.write_text(epic_data["body"], encoding="utf-8")
            
            # Create epic with EPIC label and milestone
            cmd = f"gh issue create --title {title_escaped} --body-file {temp_body_file} --label EPIC --milestone {milestone_escaped}"
            
            result = subprocess.run(
                cmd,
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True,
            )
            
            if result.returncode == 0:
                # Extract issue number
                output = result.stdout.strip()
                if "Created issue" in output and "#" in output:
                    issue_num_str = output.split("#")[1].split()[0]
                    issue_number = int(issue_num_str)
                    epic_numbers[epic_key] = issue_number
                    print(f"  ✅ Created Epic #{issue_number}: {epic_data['title']}")
            else:
                print(f"  ⚠️  Could not create epic {epic_key}: {result.stderr[:100]}")
            
            # Clean up temp file
            if temp_body_file.exists():
                temp_body_file.unlink()
                
        except Exception as e:
            print(f"  ⚠️  Error creating epic {epic_key}: {str(e)[:100]}")
    
    return epic_numbers


def get_parent_epic_for_milestone(milestone_key: str, epic_numbers: dict[str, int]) -> tuple[int | None, str]:
    """
    Get parent epic number and description for a milestone.
    Returns: tuple of (epic_number, epic_title) or (None, "")
    """
    epic_map = {
        "foundation": ("Infrastructure & Architecture Foundation", "foundation"),
        "chatbot": ("AI Chatbot Platform", "chatbot"),
        "workflows": ("Resilience & State Management", "workflows"),
    }
    
    if milestone_key in epic_map:
        epic_title, epic_key = epic_map[milestone_key]
        epic_num = epic_numbers.get(epic_key)
        return (epic_num, epic_title)
    
    return (None, "")


def delete_all_issues(skip_confirmation: bool = False) -> int:
    """
    Permanently delete all issues in the repository using gh issue delete command.
    Returns: number of issues deleted
    """
    print(f"\n🗑️  DELETE MODE: Preparing to permanently delete all issues...")
    
    if not skip_confirmation:
        response = input("⚠️  This will DELETE ALL issues permanently. Continue? (yes/no): ").strip().lower()
        if response != "yes":
            print("❌ Deletion cancelled")
            return 0
    
    repo_root = Path(__file__).parent.parent.parent
    
    try:
        # First, verify gh CLI is working
        version_check = subprocess.run(
            "gh --version",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=repo_root,
        )
        if version_check.returncode != 0:
            print(f"❌ gh CLI not available: {version_check.stderr}")
            return 0
        
        print("📋 Fetching all issues (open + closed)...")
        
        # Get all issues (both open and closed)
        result = subprocess.run(
            "gh issue list --state all --json number,title --limit 1000",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=repo_root,
        )
        
        print(f"   Return code: {result.returncode}")
        
        if result.returncode != 0:
            print(f"❌ Failed to list issues: {result.stderr}")
            return 0
        
        try:
            issues = json.loads(result.stdout)
            print(f"✅ Found {len(issues)} total issues")
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse issue list: {str(e)}")
            print(f"   Output was: {result.stdout[:200]}")
            return 0
        
        if not issues:
            print("✅ No issues to delete")
            return 0
        
        deleted_count = 0
        failed_count = 0
        
        for issue in issues:
            issue_num = issue.get("number")
            title = issue.get("title", "N/A")
            
            if not issue_num:
                print(f"  ⚠️  Skipping issue with no number: {title}")
                continue
            
            try:
                print(f"  Attempting to delete issue #{issue_num}: {title[:40]}...", end=" ")
                
                # Use gh issue delete command with --yes flag to skip confirmation
                delete_result = subprocess.run(
                    f'gh issue delete {issue_num} --yes',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=repo_root,
                )
                
                if delete_result.returncode == 0:
                    print(f"✅ DELETED")
                    deleted_count += 1
                else:
                    print(f"❌ (stderr: {delete_result.stderr[:80]})")
                    failed_count += 1
            except subprocess.TimeoutExpired:
                print(f"⏱️  (timeout)")
                failed_count += 1
            except Exception as e:
                print(f"❌ (error: {str(e)[:80]})")
                failed_count += 1
        
        print(f"\n📊 Deletion Summary:")
        print(f"   ✅ Deleted: {deleted_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   Total: {deleted_count + failed_count}")
        
        return deleted_count
    
    except Exception as e:
        print(f"❌ Error during deletion: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0
