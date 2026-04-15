"""
LangGraph nodes: Architect, Refiner, Publisher
"""

import json
import re
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from .state import BacklogState
from .issue_helpers import normalize_issue_body, categorize_issue_to_milestone, get_sprint_labels
from .github_operations import (
    get_or_create_project,
    get_or_create_milestones,
    ensure_sprint_labels,
    create_epic_issues,
    get_parent_epic_for_milestone,
    issue_exists,
    add_issue_to_project,
)


def clean_json_string(json_str: str) -> str:
    """
    Clean JSON string with literal newlines.
    Simply use json.loads then json.dumps to normalize it.
    """
    try:
        # Try to parse as-is first
        parsed = json.loads(json_str)
        # Re-serialize to normalize
        return json.dumps(parsed)
    except json.JSONDecodeError:
        # If that fails, try basic newline escaping
        # But be very conservative - only escape newlines that break JSON
        import re
        
        # Strategy: find all strings in the JSON and escape newlines within them
        def escape_newlines_in_strings(text):
            # This regex finds quoted strings and replaces unescaped newlines
            def replace_in_string(match):
                s = match.group(0)
                # Only replace actual newlines, leave already-escaped ones alone
                return s.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            
            # Match quoted strings but be careful with escape sequences
            return re.sub(r'"(?:[^"\\]|\\.)*"', replace_in_string, text)
        
        cleaned = escape_newlines_in_strings(json_str)
        return cleaned


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

Based on the following architecture documentation, generate 30 GRANULAR GitHub issues that cover:

**Sprint 1-2 Foundation (15 issues for foundation milestone)**:
1. FastAPI gateway setup and configuration (3-4 granular issues)
2. Redis Streams implementation and consumer groups (3-4 granular issues)  
3. Circuit breaker pattern implementation (2-3 granular issues)
4. PostgreSQL persistence setup (2-3 granular issues)

**Sprint 3-4 Chatbot (8 issues for chatbot milestone)**:
5. LangGraph orchestrator setup (2-3 granular issues)
6. Gemini API integration (2-3 granular issues)
7. LangSmith integration and observability (2-3 granular issues)

**Sprint 5-6 Workflows (7 issues for workflows milestone)**:
8. Idempotency layer implementation (2-3 granular issues)
9. Recovery and error handling (2-3 granular issues)
10. State persistence mechanisms (1-2 granular issues)

For EACH issue, provide:
- A concise, granular title (50-70 chars) describing a single small task
- A detailed body as a single markdown string with:
  - User Story section (As a..., I want..., So that...)
  - Acceptance Criteria section (numbered checklist, 2-4 items max for granularity)
  - Technical notes section (architecture references, key dependencies)
- A dependencies list: titles of other issues this one depends on (empty list if no dependencies)

Format as a JSON array of objects with exactly these keys: "title", "body", "dependencies"
The body MUST be a single string containing markdown, NOT nested objects.
Dependencies should be a list of issue titles, e.g., ["Deploy Redis StatefulSet", "Configure Kubernetes"]

Break down tasks into small, assignable units (6-8 hour estimates each).
Ensure first 15-16 issues can be split between Sprint 1 and Sprint 2 (8 each).

ARCHITECTURE DOCS:
{docs}

Generate the 30 granular issues now with proper dependencies and plain text body:"""
    )

    # Create chain and invoke
    chain = prompt | llm
    response = chain.invoke({"docs": docs_summary})
    response_text = response.content

    # Parse JSON response
    try:
        print(f"   📝 Received response ({len(response_text)} chars)")
        
        # Extract JSON from response (may be wrapped in markdown code blocks)
        json_str = response_text
        
        # Remove markdown code fence if present
        if "```json" in json_str:
            json_str = json_str.split("```json")[1]
            if "```" in json_str:
                json_str = json_str.split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1]
            if "```" in json_str:
                json_str = json_str.split("```")[0]
        
        json_str = json_str.strip()
        print(f"   🔍 Extracted JSON ({len(json_str)} chars), starts with: '{json_str[:20]}'")
        
        # Try to parse directly first (most common case)
        try:
            draft_issues = json.loads(json_str)
        except json.JSONDecodeError as first_error:
            # If that fails, try cleaning
            print(f"   ⚠️  Direct parse failed, attempting to clean...")
            json_str = clean_json_string(json_str)
            draft_issues = json.loads(json_str)
        
        if not isinstance(draft_issues, list):
            draft_issues = [draft_issues]
        
        # Validate and normalize each issue
        normalized_issues = []
        for issue in draft_issues:
            if not isinstance(issue, dict):
                continue
            normalized = {
                "title": str(issue.get("title", "")).strip(),
                "body": normalize_issue_body(issue),
                "dependencies": issue.get("dependencies", []) if isinstance(issue.get("dependencies"), list) else []
            }
            if normalized["title"] and normalized["body"]:
                normalized_issues.append(normalized)
        
        if not normalized_issues:
            error_msg = "No valid issues found after parsing"
            print(f"❌ {error_msg}")
            state["errors"].append(error_msg)
            state["draft_issues"] = []
            return state

        print(f"✅ Generated {len(normalized_issues)} draft issues")
        state["draft_issues"] = normalized_issues
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse Gemini response as JSON: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"   📋 Response preview: {response_text[:300]}...")
        state["errors"].append(error_msg)
        state["draft_issues"] = []
    except ValueError as e:
        # Custom error from our extraction attempts
        error_msg = f"Could not extract JSON from response: {str(e)}"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        state["draft_issues"] = []

    return state


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

For EACH of the 30 granular issues, ensure:
- Technical accuracy regarding Redis Streams or Circuit Breaker usage (if applicable)
- Clear acceptance criteria that test specific mechanisms (2-4 items, focused and actionable)
- Proper sequencing (e.g., Circuit Breaker issues should reference Redis task handling)
- Dependencies are valid issue titles that exist in the list (or empty if no deps)
- Body is a single markdown string, NOT nested objects
- Issues are granular and assignable - each focusing on one specific task

If an issue is unclear or missing these references, enhance it.
If dependencies reference non-existent issues, update them to actual issue titles in the list.
Convert any nested structure (user_story, acceptance_criteria, technical_notes) into a single markdown body string.
Keep the JSON format: array of objects with "title", "body", and "dependencies" keys ONLY.
Maintain the organization into Foundation (Sprint 1-2), Chatbot (Sprint 3-4), and Workflows (Sprint 5-6) themes.

DRAFT ISSUES:
{issues}

Return the refined issues as valid JSON array with dependencies and plain text body:"""
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
            json_str = response_text.strip()
        
        print(f"   🔍 Extracted JSON ({len(json_str)} chars)")
        
        # Validate it looks like JSON
        json_str = json_str.strip()
        if not (json_str.startswith('[') or json_str.startswith('{')):
            # Try to find JSON array in the response
            import re
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                print(f"   ✅ Found JSON array in response")
            else:
                raise ValueError(f"No valid JSON found in refiner response")
        
        # Clean up JSON: escape literal newlines and control characters
        json_str = clean_json_string(json_str)

        refined_issues = json.loads(json_str)
        if not isinstance(refined_issues, list):
            refined_issues = [refined_issues]
        
        # Validate and normalize each issue
        normalized_issues = []
        for issue in refined_issues:
            if not isinstance(issue, dict):
                continue
            normalized = {
                "title": str(issue.get("title", "")).strip(),
                "body": normalize_issue_body(issue),
                "dependencies": issue.get("dependencies", []) if isinstance(issue.get("dependencies"), list) else []
            }
            if normalized["title"] and normalized["body"]:
                normalized_issues.append(normalized)
        
        if not normalized_issues:
            error_msg = "No valid issues after refinement"
            print(f"⚠️  {error_msg}, falling back to draft issues")
            state["errors"].append(error_msg)
            state["refined_issues"] = state["draft_issues"]
            return state

        print(f"✅ Refined {len(normalized_issues)} issues")
        state["refined_issues"] = normalized_issues
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse Refiner response as JSON: {str(e)}"
        print(f"❌ {error_msg}")
        print(f"   📋 Response preview: {response_text[:300]}...")
        state["errors"].append(error_msg)
        state["refined_issues"] = state["draft_issues"]
    except ValueError as e:
        error_msg = f"Could not extract JSON from refiner response: {str(e)}"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        state["refined_issues"] = state["draft_issues"]

    return state


def publisher_node(state: BacklogState) -> BacklogState:
    """
    Node 3: Create Epic issues, then story issues on GitHub
    """
    print("\n📤 THE PUBLISHER: Creating Epic and Story issues...")

    if not state["refined_issues"]:
        print("❌ No refined issues to publish")
        return state

    import subprocess
    
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
    
    # Create or get milestones
    milestones_map = get_or_create_milestones()
    
    # Ensure Sprint labels exist
    sprint_labels_exist = ensure_sprint_labels()
    if not sprint_labels_exist:
        warning_msg = "Could not ensure all Sprint labels exist, issues will be created without some labels"
        print(f"⚠️  {warning_msg}")
        state["errors"].append(warning_msg)

    # ========== STEP 1: Create Epic Issues ==========
    print(f"\n🎯 STEP 1: Creating Epic-level issues...")
    epic_numbers = create_epic_issues(milestones_map)
    
    # ========== STEP 2: Create Story Issues ==========
    print(f"\n🎯 STEP 2: Creating Story issues...")
    published_numbers = []
    skipped_numbers = []
    temp_body_file = Path(__file__).parent / "temp_body.md"
    
    # Track issue counts per milestone for proper sprint distribution
    milestone_issue_counts = {"foundation": 0, "chatbot": 0, "workflows": 0}

    for i, issue in enumerate(state["refined_issues"], 1):
        title = issue.get("title", "")
        body = issue.get("body", "")
        dependencies = issue.get("dependencies", [])
        
        # Ensure title and body are strings
        if isinstance(title, dict):
            title = json.dumps(title)
        if isinstance(body, dict):
            body = json.dumps(body)
        
        title = str(title).strip()
        body = str(body).strip()

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
            if project_number:
                add_issue_to_project(existing_issue_num, project_number)
            continue

        try:
            # Determine milestone based on issue title
            milestone_key = categorize_issue_to_milestone(title)
            milestone_title = milestones_map.get(milestone_key, "")
            
            # Use issue index within milestone for even sprint distribution
            issue_index_in_milestone = milestone_issue_counts.get(milestone_key, 0)
            milestone_issue_counts[milestone_key] = issue_index_in_milestone + 1
            
            sprint_labels = get_sprint_labels(milestone_key, issue_index_in_milestone)
            
            # Add epic reference to body
            full_body = body
            epic_num, epic_title = get_parent_epic_for_milestone(milestone_key, epic_numbers)
            if epic_num:
                epic_ref = f"**Related Epic:** #{epic_num} - {epic_title}\n\n"
                full_body = epic_ref + full_body
            
            # Prepare body with dependencies section if they exist
            if dependencies:
                dep_section = "\n\n## Dependencies\n"
                dep_section += "This issue depends on:\n"
                for dep in dependencies:
                    dep_section += f"- [ ] {dep}\n"
                full_body = full_body + dep_section
            
            # Write body to temporary file to preserve formatting
            temp_body_file.write_text(full_body, encoding="utf-8")
            
            # Build command with body-file
            title_escaped = json.dumps(title)
            cmd = f"gh issue create --title {title_escaped} --body-file {temp_body_file}"
            
            # Add labels: story + sprint labels
            labels_to_add = ["story"]
            labels_to_add.extend(sprint_labels)
            
            if labels_to_add:
                for label in labels_to_add:
                    cmd += f" --label {json.dumps(label)}"
            
            # Add milestone if available
            if milestone_title:
                milestone_escaped = json.dumps(milestone_title)
                cmd += f" --milestone {milestone_escaped}"
            
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent.parent,
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

            # Extract issue number from output
            output = result.stdout.strip()
            if "Created issue" in output and "#" in output:
                issue_num_str = output.split("#")[1].split()[0]
                issue_number = int(issue_num_str)
                published_numbers.append(issue_number)
                print(f"✅ Created issue #{issue_number}: {title}")
                print(f"   📌 Milestone: {milestone_title or 'None'}")
                print(f"   🏷️  Labels: {', '.join(labels_to_add) or 'None'}")
                if epic_num:
                    print(f"   🔗 Epic: #{epic_num}")
                if dependencies:
                    print(f"   🔗 Dependencies: {', '.join(dependencies)}")

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
        finally:
            if temp_body_file.exists():
                temp_body_file.unlink()

    state["published_issue_numbers"] = published_numbers
    print(f"\n✅ Created {len(epic_numbers)} Epic issues")
    print(f"✅ Created {len(published_numbers)} Story issues")
    print(f"⏭️  Skipped {len(skipped_numbers)} existing issues (idempotent)")
    print(f"📊 Total story issues involved: {len(published_numbers) + len(skipped_numbers)}")
    print(f"\n📊 Issues per milestone/sprint:")
    print(f"   Foundation (Sprint 1-2): {milestone_issue_counts['foundation']} issues (~{milestone_issue_counts['foundation']//2} each sprint)")
    print(f"   Chatbot (Sprint 3-4): {milestone_issue_counts['chatbot']} issues (~{milestone_issue_counts['chatbot']//2} each sprint)")
    print(f"   Workflows (Sprint 5-6): {milestone_issue_counts['workflows']} issues (~{milestone_issue_counts['workflows']//2} each sprint)")

    return state
