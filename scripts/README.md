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

Example output:
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
✅ Found existing project: #1 (em-assignment Backlog)

✅ Created issue #15: Implement FastAPI Gateway
  📌 Added to project: #15

⏭️  Issue already exists (idempotent): #14 - Develop LangGraph Orchestrator
  📌 Added to project: #14

✅ Created 1 new issues
⏭️  Skipped 13 existing issues (idempotent)
📊 Total issues involved: 14
================================================================================
```

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
- ✅ **Full error tracking** - Continues on partial failures  
- ✅ **JSON parsing** - Handles Gemini markdown code block responses  
- ✅ **Subprocess management** - Timeouts & error handling for `gh` CLI calls  
- ✅ **Cross-platform** - Works on Windows, macOS, Linux
