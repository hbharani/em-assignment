# Scripts

Scripts for automating various tasks related to the em-assignment project.

## backlog_manager.py

A LangGraph agent that generates GitHub issues from architecture documentation using Google Gemini, with automatic project management and idempotent issue creation.

### What it does

1. **Architect Node**: Reads all markdown files from `docs/` and uses Gemini to draft 12-15 GitHub issues covering:
   - Infrastructure setup (FastAPI, LangGraph, workers)
   - Redis Streams implementation
   - Circuit breaker patterns
   - PostgreSQL persistence
   - LangSmith integration
   - Kubernetes deployment

2. **Refiner Node**: Re-evaluates draft issues to ensure they properly reference:
   - Redis Streams (async distribution, consumer groups, exactly-once delivery)
   - Circuit Breaker patterns (CLOSED/OPEN/HALF_OPEN states)
   - Clear acceptance criteria

3. **Publisher Node**: Uses the `gh` CLI to:
   - **Create or find** a GitHub project (`em-assignment Backlog`)
   - **Check for existing issues** by title (idempotent - won't create duplicates)
   - **Create new issues** only if they don't already exist
   - **Add all issues** (new and existing) to the GitHub project
   - Track created vs. skipped issues

### Idempotency

The agent is **fully idempotent**:
- Before creating an issue, it queries GitHub to check if an issue with the same title already exists
- If found, it skips creation and adds the existing issue to the project
- Status: `⏭️ Issue already exists (idempotent): #42 - Issue Title`
- Multiple runs won't duplicate issues

### GitHub Project Management

The script automatically:
- Creates a new GitHub project named `em-assignment Backlog` (if it doesn't exist)
- Adds all generated/existing issues to this project
- Provides clear feedback on project creation and issue assignment

### Milestones

The script creates and manages **3 milestones** via GitHub REST API (`gh api`), each spanning 2 sprints:

1. **Foundation (Sprint 1-2)**: Infrastructure setup
   - FastAPI gateway, Kubernetes deployment
   - Redis Streams, PostgreSQL setup
   - Monitoring baseline

2. **Chatbot (Sprint 3-4)**: Core agent platform
   - LangGraph orchestrator
   - Gemini integration
   - LangSmith observability

3. **Workflows (Sprint 5-6)**: Advanced features
   - Circuit breaker implementation
   - State persistence and recovery
   - Idempotency and request deduplication

Issues are automatically categorized to milestones based on keywords in their titles.

### Labels

The script automatically creates an **EPIC** label (red color) and tags all generated issues with it for easy filtering and tracking.

Features:
- Creates label via `gh api` if it doesn't exist
- Uses color: #FF6B6B (red) for visibility
- Conditionally adds label only if creation succeeded
- Non-blocking: continues if label creation fails

### Issue Body Formatting

The script uses `--body-file` to preserve markdown formatting in issue bodies:
- Writes issue body to temporary file (`temp_body.md`)
- Passes file path to `gh issue create --body-file`
- Automatically cleans up temp file after creation
- Fixes newline and formatting issues from inline body strings

### Example output:
```
✅ Found existing project: #1 (em-assignment Backlog)
✅ Created issue #15: Some Feature
  📌 Added to project: #15
⏭️  Issue already exists (idempotent): #14 - Another Feature
  📌 Added to project: #14
```

### Requirements

```bash
pip install langgraph langchain langchain_google_genai pydantic
```

### Environment Setup

```bash
# Set your Google Gemini API key
export GOOGLE_API_KEY="your-api-key-here"

# Authenticate with GitHub (for gh CLI and project access)
gh auth login

# Verify gh CLI is installed
gh --version
```

### Usage

**Dry Run (preview issues without publishing to GitHub):**
```bash
python scripts/backlog_manager.py --dry-run
```

**Auto-publish to GitHub and create project:**
```bash
python scripts/backlog_manager.py
```

**Cleanup all issues (interactive confirmation):**
```bash
python scripts/backlog_manager.py --cleanup-only
```

**Cleanup and recreate all issues:**
```bash
python scripts/backlog_manager.py --cleanup
```

The script automatically loads:
- `README.md` (project root)
- `docs/**/*.md` (all architecture documentation)

### Output

The script outputs a comprehensive summary with:
- Number of draft, refined, and published issues
- Number of skipped issues (idempotent)
- GitHub issue numbers created
- GitHub project information
- Any errors encountered

Example:
```
================================================================================
🏗️  THE ARCHITECT: Reading docs and drafting issues...
✅ Generated 14 draft issues

🔧 THE REFINER: Validating Redis Streams and Circuit Breaker references...
✅ Refined 14 issues

📤 THE PUBLISHER: Managing GitHub issues and project...
📋 Checking for project: em-assignment Backlog
✅ Found existing project: #1

🎯 Managing milestones...
  ✅ Found milestone: Foundation (Sprint 1-2)
  ✅ Found milestone: Chatbot (Sprint 3-4)
  ✅ Found milestone: Workflows (Sprint 5-6)

✅ Created issue #15: Implement FastAPI Gateway
   📌 Milestone: Foundation (Sprint 1-2)
   📌 Added to project: #15

⏭️  Issue already exists (idempotent): #14 - Develop LangGraph Orchestrator
   📌 Milestone: Chatbot (Sprint 3-4)
   📌 Added to project: #14

✅ Created 1 new issues
⏭️  Skipped 13 existing issues (idempotent)
📊 Total issues involved: 14
================================================================================
```

### Cleanup and Recreation

The script supports completely resetting the backlog by permanently deleting all issues:

**Interactive deletion (with confirmation):**
```bash
python scripts/backlog_manager.py --cleanup-only
```
- Prompts: "This will DELETE ALL issues permanently. Continue? (yes/no)"
- Uses GitHub REST API to permanently delete issues (not just close)
- Shows progress with ✅ for each issue deleted
- Reports summary: deleted count, failed count

**Delete and recreate in one command (automatic):**
```bash
python scripts/backlog_manager.py --cleanup
```
- Automatically deletes all issues (no confirmation)
- Uses `gh api -X DELETE repos/:owner/:repo/issues/{number}`
- Verifies deletion succeeded (checks for remaining issues)
- Immediately creates new issues from architecture docs
- Full reset in one command

**Output includes:**
- Total issue count found
- Real-time feedback for each deletion (✅/❌)
- Summary of successful/failed deletions
- Verification check after deletion
- New issue creation immediately after

**Note:** This permanently deletes issues from GitHub. They cannot be recovered through normal means. The `--cleanup` flag is designed for development/testing workflows where you need a fresh backlog state.

### Troubleshooting

**Issue: Milestone creation fails**
- Cause: Using wrong `gh` command
- Fix: Script now uses `gh api repos/:owner/:repo/milestones` (REST API)
- Fallback: Issues still created without milestone if this fails

**Issue: Label not found error when creating issues**
- Cause: EPIC label doesn't exist yet
- Fix: Script now calls `ensure_epic_label()` before creating issues, creates EPIC label if needed
- Fallback: Issues still created without label if label creation fails

**Issue: Milestone assignment not working**
- Check: Ensure milestone title matches exactly (case-sensitive)
- Debug: Run with `--dry-run` to see milestone categorization
- Note: Using REST API to bypass gh CLI limitations

### State Flow

```
BacklogState
├── docs_content: dict[filename → content]
├── draft_issues: list[dict with title, body]
├── refined_issues: list[dict with title, body]
├── published_issue_numbers: list[int] (new issues created)
└── errors: list[str]

Flow: Architect → Refiner → Publisher
```

### Key Features

- ✅ **Linear graph** - Architect → Refiner → Publisher  
- ✅ **Idempotent issue creation** - Won't duplicate existing issues
- ✅ **GitHub project management** - Automatic creation and issue assignment
- ✅ **Milestone management** - Creates 3 milestone tracks (Foundation, Chatbot, Workflows)
- ✅ **Intelligent categorization** - Assigns issues to milestones based on keywords
- ✅ **Body file preservation** - Uses --body-file for proper markdown formatting
- ✅ **EPIC labels** - Automatically tags all issues with EPIC label
- ✅ **Full error tracking** - Continues on partial failures  
- ✅ **JSON parsing** - Handles Gemini markdown code block responses  
- ✅ **Subprocess management** - Timeouts & error handling for `gh` CLI calls  
- ✅ **Cross-platform** - Works on Windows, macOS, Linux
- ✅ **Cleanup support** - Interactively or automatically delete and recreate issues
