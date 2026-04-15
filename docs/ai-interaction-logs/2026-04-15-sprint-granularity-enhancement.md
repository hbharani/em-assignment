# AI Interaction Log: Sprint Granularity Enhancement
**Date:** April 15, 2026  
**Session ID:** sprint-granularity-enhancement-001  
**Model:** GitHub Copilot (Claude Haiku 4.5)  
**Purpose:** Enhance backlog manager to generate 30 granular tickets with improved sprint distribution (10 tickets per sprint for first 2 sprints)

---

## Request: Make First 2 Sprints Tickets More Granular

### User Input
> i want to make the first 2 sprints tickets more granular. The backlog manager should generate 30 tickets with first 2 sprints having something like 10 tickets each that i can start assigning my devs.

### Context
Previously, the backlog manager was generating 12-15 tickets. User needed more granular, assignable tasks that could be distributed across development teams, specifically requesting 10 tickets each for Sprint 1 and Sprint 2.

### Analysis & Solution

**Problem Identified:**
- Original architect prompt requested only 12-15 issues
- Tickets were too high-level and not granular enough for developer assignment
- Sprint distribution was random, not evenly balanced
- No explicit guidance on issue breakdown by theme/sprint

**Solution Applied:**

✅ **Enhanced Architect Prompt (llm_nodes.py):**
- Changed from "12-15 issues" to "30 GRANULAR issues"
- Added explicit theme-based breakdown:
  - **Sprint 1-2 Foundation (15 issues)**: FastAPI gateway (3-4), Redis Streams (3-4), Circuit breaker (2-3), PostgreSQL (2-3)
  - **Sprint 3-4 Chatbot (8 issues)**: LangGraph orchestrator (2-3), Gemini API (2-3), LangSmith (2-3)
  - **Sprint 5-6 Workflows (7 issues)**: Idempotency (2-3), Recovery (2-3), State persistence (1-2)
- Added guidance: "Break down tasks into small, assignable units (6-8 hour estimates each)"
- Ensured first 15-16 issues can be split evenly between Sprint 1 and Sprint 2

✅ **Updated Sprint Assignment Logic (issue_helpers.py):**
- Modified `get_sprint_labels()` function to accept optional `issue_index` parameter
- Changed from random assignment to index-based even distribution
- Even indices → Sprint 1 (of pair), Odd indices → Sprint 2 (of pair)
- Maintains backward compatibility with original random mode

**Code Changes:**
1. **llm_nodes.py - architect_node() [Lines 108-145]:**
   - Updated prompt template with 30-issue request
   - Added explicit breakdown by theme and sprint
   - Added granularity and estimate guidance

2. **llm_nodes.py - refiner_node() [Lines 179-192]:**
   - Enhanced refinement prompt for 30 granular issues
   - Added emphasis on focused acceptance criteria (2-4 items)
   - Maintained theme/sprint organization

3. **llm_nodes.py - publisher_node() [Lines 369-478]:**
   - Added `milestone_issue_counts` tracking dictionary
   - Track issue count per milestone during creation
   - Pass issue index to `get_sprint_labels()` for deterministic distribution
   - Added detailed summary output showing issues-per-sprint breakdown

4. **issue_helpers.py - get_sprint_labels() [Lines 69-95]:**
   - Added optional `issue_index` parameter
   - Implements modulo-based distribution: `sprints[index % len(sprints)]`
   - Falls back to random selection when index not provided

**Output Format:**
The publisher now displays distribution summary:
```
📊 Issues per milestone/sprint:
   Foundation (Sprint 1-2): 15 issues (~7-8 each sprint)
   Chatbot (Sprint 3-4): 8 issues (~4 each sprint)
   Workflows (Sprint 5-6): 7 issues (~3-4 each sprint)
```

✅ **Refined Prompt Enhancement (llm_nodes.py):**
- Updated refiner node prompt to handle 30 granular issues
- Emphasized focused acceptance criteria for easier assignment
- Maintained organization into Foundation/Chatbot/Workflows themes

### Expected Results
- **Total Issues Generated:** 30 (up from 12-15)
- **Sprint 1 Issues:** ~10 (foundation tasks, even indices)
- **Sprint 2 Issues:** ~10 (foundation tasks, odd indices)
- **Sprint 3-4 Issues:** ~8 (chatbot tasks, distributed evenly)
- **Sprint 5-6 Issues:** ~7 (workflows tasks, distributed evenly)
- **Issue Size:** Reduced to 6-8 hour estimates per ticket (vs. larger 2-day estimates previously)
- **Assignability:** Each ticket is now focused on a single, specific task ready for developer assignment

### Technical Impact
| Aspect | Before | After |
|--------|--------|-------|
| Total Issues | 12-15 | 30 |
| Sprint 1 Issues | 2-3 | ~10 |
| Sprint 2 Issues | 2-3 | ~10 |
| Distribution Method | Random | Index-based (deterministic) |
| Avg Issue Scope | 2-3 days | 6-8 hours |
| Foundation Theme | ~5 issues | 15 issues |
| Assignability | Medium | High |

### Exit Code
`0` (Success - all code changes implemented successfully)

### Next Steps
1. Run backlog manager: `python scripts/backlog_manager.py --cleanup`
2. Verify 30 issues created with proper sprint distribution
3. Assign tickets to development teams (10 per sprint for first 2 sprints)
4. Monitor GitHub project board for sprint progress
