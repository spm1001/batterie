# CLI Reference

Setup, authentication, query patterns, and data model for the todoist CLI.

## CLI Setup

Installed via `uv tool install` from the source repo (local clone or `git+https`), which creates a `todoist` shim in `~/.local/bin/`.

```bash
todoist <command>
```

### Authentication

```bash
todoist auth              # Print setup instructions
todoist auth --token T    # Store API token (get from Todoist settings)
todoist auth --status     # Check authentication status
```

**Setup:** Run `todoist auth` for instructions — it prints the URL to get your API token from Todoist's developer settings. Then run `todoist auth --token YOUR_TOKEN` to store it.

Token is stored in macOS Keychain (if available) or in `~/.claude/plugins/data/todoist-gtd-batterie-de-savoir/token` on Linux.

If auth fails, prompt user to run `todoist auth` or re-run `todoist auth --token` with a fresh token.

**Key design choice:** On workspace (team) projects, the CLI auto-filters to show only your tasks by default. Use `--team` for all tasks, `--unassigned` for triage. On personal projects, all tasks are shown regardless of collaborators.

### Error Handling

When CLI commands fail, use these patterns:

| Error | Likely Cause | Action |
|-------|--------------|--------|
| `not authenticated` | Token missing or cleared | Ask user to run `todoist auth` |
| `Token revoked or expired` | User revoked app access | Ask user to re-run `todoist auth` |
| `Request timed out` | Slow network or API issues | Retry once, then tell user |
| `Could not connect` | Network down | Tell user to check connection |
| `Rate limited` | Too many requests | Wait 30s and retry |
| `Task not found` | Bad task ID | Verify ID with user |
| `Cannot move between workspaces` | API limitation | Suggest complete + recreate |

**When to escalate to user:**
- Auth errors (they need to act)
- Repeated timeouts (might be their network)
- Permission errors (might need to unlock Keychain)

**When to retry silently:**
- Single timeout (transient)
- Single rate limit (just wait)

**When to suggest re-auth:**
- Any 401 error
- "Token revoked" message
- Repeated "not authenticated" after confirming auth status

## Query Patterns

**All commands return JSON.** Parse with jq or read directly.

### Get Account Overview
```bash
# List all projects
todoist projects

# Get sections in a project
todoist sections --project-id "<project-id>"
```

### Find Outcomes (Remember: sections, not tasks!)
```bash
# Get Q4 outcomes (sections in the outcomes project)
todoist sections --project-id "<desired-outcomes-q4-id>"

# Get tasks under a specific outcome
todoist tasks --section-id "<outcome-section-id>"
```

**Workspace filtering:** On team projects, shows only your tasks by default. Use `--team` for all, `--unassigned` for untriaged items.

### Check Claude Inbox
```bash
# Find @Claude project ID first
todoist projects | jq '.[] | select(.name == "@Claude")'

# Get tasks in @Claude inbox
todoist tasks --project-id "<claude-inbox-id>"
```

**Triage note:** Comments are included inline — check `.comments[]` for attachments and context before skipping items. See [PATTERNS.md](PATTERNS.md#inbox-triage-workflow) for the full workflow.

### Filter with Todoist Syntax
```bash
# Today's tasks (including overdue)
todoist filter "today"

# Assigned to someone
todoist filter "assigned to: Alex"

# By label
todoist filter "@waiting-for"

# Complex queries
todoist filter "#Work & today"
```

### Common Label Queries
```bash
todoist tasks --label "someday-maybe"
todoist tasks --label "areas-of-focus"
```

### Convenience Flags
```bash
# Filter by project name (not just ID)
todoist tasks --project "@Wait"

# Filter by assignee name (requires --project)
todoist tasks --project "Areas of Focus" --section-id "<id>" --assignee "Alex"

# Filter by creation date (for staleness checks)
todoist tasks --project "@Wait" --created-before "2025-12-01"

# Filter by age (convenience alternative to --created-before)
todoist tasks --project "@Wait" --older-than 30d   # 30 days
todoist tasks --project "@Wait" --older-than 2w    # 2 weeks
todoist tasks --project "@Wait" --older-than 3m    # 3 months

# Include section names in output (avoids manual section_id lookup)
todoist tasks --project "@Work" --include-section-name
```

## Data Model

**Task objects are complete.** The CLI returns tasks with comments inline:

```json
{
  "id": "...",
  "content": "Add this to the Team Handbook",
  "description": "",
  "comments": [
    { "content": "", "attachment": { "file_name": "document.pdf" } },
    { "content": "Progress note from UI", "attachment": null }
  ]
}
```

| Data | Location |
|------|----------|
| Task title | `content` field |
| Notes/details | `description` field |
| Due dates | `due` object |
| Attachments | `comments[].attachment` |
| Progress notes | `comments[].content` |

### Forwarded Emails Pattern

When emails are forwarded to a Todoist project's email address:
- Subject → task `content`
- Body → `comments[0]` with empty content, HTML attachment
- Attachments → additional `comments[]` entries with attachments

**Auth limitation:** Attachment URLs (`files.todoist.com`) require Todoist authentication. You cannot curl them directly — tell user to open in browser.

### Subtask Navigation

**Parent→child is one-way.** Tasks have `parent_id` pointing to their parent, but parents don't list their children.

```bash
# To find a task's parent:
# Read the parent_id field from the task JSON

# Note: CLI doesn't have --parent-id filter for listing subtasks
# Use filter syntax: todoist filter "subtask of: <parent-task-id>"
```

### Labels Limitation

**No label discovery endpoint.** You can filter by labels, but can't list all labels in an account. User must know label names.

```bash
todoist tasks --label "waiting-for"  # Works if label exists
# But no: list-all-labels                       # Doesn't exist
```

### Cross-Workspace Limitation

**Moving tasks between personal and shared projects fails.** The `move_task` API cannot move tasks across workspace boundaries (personal account ↔ MIT shared workspace).

**Workaround:** Complete the task in the source project, then recreate it in the target project. History is preserved in both locations.

```bash
# This fails:
todoist update <task-id> --project "Someday/Maybe"  # Error if crossing workspace

# Workaround:
todoist add "Task content" --project "Someday/Maybe"
todoist done <old-task-id>
```
