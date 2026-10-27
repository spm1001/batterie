# Bon — Instruction Shard

Auto-loaded via `~/.claude/rules/bon.md`. Carries always-on rules only — skill context (`/open`, `/close`) handles the rest.

## Skill Loading

When `.bon/` exists, invoke `Skill(open)` at session start and before bon CLI commands — it provides context that makes the rest of the session better.

Bon is the default tracker. Check bon briefs for staleness before executing — the open skill's "Three legs of staleness" names the method, and it is three commands, not an investigation.

When a skill or tool fails during real work: file a Field Report bon item in the repo that owns it. **Check for an existing one first.** Search that board's open items for the same failure (`bon list | grep -i "field report"`, then grep the symptom). If one is already there, add this sighting to it with `bon edit ID --append-how "SEEN AGAIN <date>, <host>: <what happened>"` instead of filing a twin. A persistent failure should grow one report with a count of sightings, not a new report every session.

## Overrides

| Your Default | What I Need |
|-------------|-------------|
| EnterPlanMode for complex tasks | `batterie:lay-out` — thinking expressed as understanding.md + bon hierarchy |
| Plan files | Plans → Bon before execution |
| TodoWrite for work tracking | Bon for anything that persists across sessions. TodoWrite is fine for ephemeral in-session checklists. |

## GTD Vocabulary

| Say This | Not This |
|----------|----------|
| Desired Outcome | Epic, User Story |
| Next Action | Task, Ticket |
| Waiting For | Blocked, Blocker |
| Someday/Maybe | Backlog |

Frame outcomes as achievements: "Taught Claude to generate charts" not "Create chart generation skill." Past-tense verb + the "so what."

## Storage: JSONL in the repo

Every board is `.bon/items.jsonl` in its own repo, and syncs itself on each write (fetch, rebase, merge by item, commit, push). Dolt was retired on 2026-10-24: the server is stopped, and its final state is in `spm1001/bon-dolt-backup`.

A clone that still carries `.bon/backend` containing `dolt` hasn't pulled the migrate commit. bon refuses, says so and names the fix (`git pull`, after `git checkout -- .bon/README.md` if the pull objects to that file). Never restart Dolt or recreate its client config to get a board back.

## Commit Citation

A commit doing work tracked by a bon cites it: trailing `(bon-ID)` in the subject or body (e.g. `fix(close): resolve session id from env (bon-casovo)`). This is the link the orphans check reads — an open item no commit ever cites, or a commit citing an unknown ID, is a review-time signal. Untracked work commits normally; don't invent an item just to have an ID.

**bon commits its own board changes — never `git add .bon` yourself.** Every write (`new`, `edit`, `done`, `wait`…) lands as its own `bon: …` commit on the checked-out branch, so staging `.bon/` afterwards does nothing. If a board change must reach `main`, check which branch is checked out before writing.

**`Warning: board sync: board write landed on <branch>, not <default>` means exactly that** — the write was committed to that branch (and pushed when online), and sessions reading the remote's default branch won't see it. It stays silent when `<remote>/HEAD` is unset, since the default is then unknown. bon never refuses; if the branch was an accident, switch to the default and re-apply the change there.

## Discoverability

`bon show ID --json` and `bon list --json` already pretty-print (indent=2). Pipe direct — no need to wrap in `python3 -m json.tool` or `json.dumps(d, indent=2)`.

## Session Lifecycle

**Starting:** Hooks provide orientation. Draw-down from bon before writing code.

**Stopping:** Use `/close` skill.

## Capture Generously

During /close, lean toward capturing rather than filtering. If something came up during the session — even if it seems minor, pre-existing, or someone else's domain — put it into Now, Bon, or Handoff Next. You propose which bin; the operator decides what drops. The cost of capturing something unnecessary is low; the cost of losing a useful observation is high.
