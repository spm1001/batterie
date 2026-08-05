# Accomplis — Instruction Shard

Auto-loaded via `~/.claude/rules/accomplis.md`, rewritten each session start by this
plugin's `hooks/ensure-accomplis.sh` — edit `instructions.md` in the source repo,
never the copy in `rules/`.

## Skill Loading

**Any Todoist read or write through `accomplis` — invoke `Skill(coaching)` FIRST.**
This holds however the session arrived at Todoist: a data question ("can you see my
tasks?") is still a Todoist operation. The CLI is plumbing; the skill carries the
GTD semantics the data alone can't — where this user's outcomes live, workspace
filtering, sections-as-outcomes vs status lanes, review order.

## Overrides

| Your Default | What I Need |
|-------------|-------------|
| Read CLI output as one stream | accomplis info lines ("Showing 23 of 68…") go to **stderr** — `2>&1 \| jq` breaks; pipe stdout only |
