# Scripts

Scripts for automating various tasks related to the em-assignment project.

## backlog_manager.py

A LangGraph agent that generates GitHub issues from architecture documentation using Google Gemini.

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

3. **Publisher Node**: Uses the `gh` CLI to create issues on GitHub

### Requirements

```bash
pip install langgraph langchain langchain_google_genai pydantic
```

### Environment Setup

```bash
# Set your Google Gemini API key
export GOOGLE_API_KEY="your-api-key-here"

# Authenticate with GitHub (for gh CLI)
gh auth login
```

### Usage

**Dry Run (preview issues without publishing to GitHub):**
```bash
python scripts/backlog_manager.py --dry-run
```

**Auto-publish to GitHub:**
```bash
python scripts/backlog_manager.py
```

The script automatically loads:
- `README.md` (project root)
- `docs/**/*.md` (all architecture documentation)

### Output

The script outputs a summary with:
- Number of draft, refined, and published issues
- GitHub issue numbers created
- Any errors encountered

Example:
```
================================================================================
📊 WORKFLOW SUMMARY
================================================================================
📄 Docs loaded: 8
📝 Draft issues: 14
✨ Refined issues: 14
✅ Published issues: 14

🎉 Issue Numbers: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
================================================================================
```

### State Flow

```
BacklogState
├── docs_content: dict[filename -> content]
├── draft_issues: list[dict with title, body]
├── refined_issues: list[dict with title, body]
├── published_issue_numbers: list[int]
└── errors: list[str]

Flow: Architect -> Refiner -> Publisher
```

### Key Features

- **Linear Graph**: Architect → Refiner → Publisher (no branches)
- **Error Tracking**: Collects all errors in state for review
- **Partial Success**: Continues if some issues fail (doesn't crash entire workflow)
- **JSON Parsing**: Handles Gemini responses with markdown code blocks
- **Subprocess Management**: Timeout and error handling for `gh` CLI calls
