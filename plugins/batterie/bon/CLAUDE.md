# CLAUDE.md

Guidance for working on bon (the codebase, not with bon).

## What This Is

Bon is a lightweight work tracker for Claude-human collaboration. JSONL in the repo, Git-tracked, self-syncing. A couple of dozen commands (incl. cross-repo `bon move` and `someday`/`unsomeday` parking), a few thousand lines of core, and a pytest suite. (An optional Dolt backend existed from March to October 2026; it was retired on 2026-10-24 and its code deleted the same evening — see Storage.) For exact counts ask the code (`bon --help`; `uv run pytest --collect-only -q`), not this file — hand-maintained numbers rot, and rotted ones get quoted into briefs (bon-niloza).

**This repo went PRIVATE in the 2026-09-23 security triage; it was public before that**, so everything pushed before then (handoffs, `understanding.md`, `docs/`) was world-readable and may still be cached elsewhere. It also means plugin users can't see this repo unless they are collaborators. Two family collaborators were added with write access to every private suite repo on 2026-09-23, so family fixes can land as PRs again. Anyone else's report reaches us by message: read it as a pull request with nowhere to land. The public-era guidance below still applies if the repo is ever made public again. (Handoffs moved out of `.bon/` to the visible root `handoffs/` in the 2026-08-22 migration, and `.bon/handoffs/` stopped being a resolution rung at all in bon-sedoze; `.bon/` is still tracked here for the bottle and understanding.md. Since 2026-10-24 bon's own board is `.bon/items.jsonl` in this repo, so the board is exactly as private as the repo.) Most sibling repos are private, and that asymmetry is the trap. A finding about a live service belongs in the repo that owns the service, with only a pointer left here; a handoff describing an unfixed weakness publishes that weakness. One command settles which world you're in: `gh repo view <repo> --json visibility`.

## Versioning & releasing (suite-managed)

bon ships as part of the **Batterie de Savoir** suite, which carries **one suite-wide version**. So:

- **Do NOT hand-bump `.claude-plugin/plugin.json` to release.** This repo's own `plugin.json` version is **local-dev-only** — the assembler stamps every published plugin to the suite version, overwriting it.
- **Release via `/ship`** from this working tree — it bumps the suite version centrally and ships the change (a 2-repo push: this repo + the central suite bump). Never hand-run the assemble.
- **A `CLAUDE.md` / `instructions.md` / `skills/` / `hooks/` edit here is vendored content** — it must ride a suite bump (a publish) to actually ship, or the assembler quarantines the plugin. `docs/` / `.bon/` edits are free.
- **`bon --version` is separate** — it reads *the suite release that last changed bon* (publish.py lazy-stamps only the repo it publishes), so a CLI number **below** the current suite number is expected, not drift.

Full picture: `spm1001/batterie-de-savoir` → `CLAUDE.md` "Versioning convention" + `.bon/understanding.md`.

## Quick Commands

```bash
uv run pytest                    # Run all tests
uv run pytest tests/test_X.py    # Run specific test file
uv run bon list                  # See current bon state
uv run bon --help                # CLI help
```

## Project Structure

```
src/bon/
├── cli.py        # All commands, argparse setup, main entry point
├── storage.py    # JSONL I/O, validation, prefix management, dedup, backend dispatch
├── ids.py        # ID generation (pronounceable 3-syllable)
├── display.py    # Output formatting (hierarchical, JSON, JSONL)
└── queries.py    # Filtering (ready, waiting)

tests/            # pytest suite, one file per command
fixtures/         # JSONL snapshots for parametrized tests
skills/open/SKILL.md     # Claude Code integration (session ritual + draw-down discipline)
```

## Module Dependencies

Verified against imports (2026-06-20). Intra-package edges only:

```
cli      ──▶ display, storage, ids, queries
storage  ──▶ ids
display  ──▶ ids, queries
ids, queries ── leaves (no intra-package imports)
```

- **`ids` and `queries` are leaves** — nothing in-package depends *up* from them; safe to read first.
- **A change to `ids`** (ID generation, ordering) is the most load-bearing leaf — it ripples into `storage`, `display`, and `cli`.

## Data Model

Items live in `.bon/items.jsonl`. Two types:

- **Outcome**: Desired result (has children)
- **Action**: Concrete step (has parent)

`waiting_for` applies to **both** types — a delegated outcome is GTD's textbook Waiting For (adjudicated 2026-08-16). `tactical` stays action-only.

Both require `brief: {why, what, done}` — all three non-empty. Two optional subfields: `how` captures approach/strategy, and `badly` carries a **pre-registered falsifier** — what would show the work went wrong, as against `--done`'s "how do we know it's complete".

`badly` is outcomes-shaped (the CLI *warns* on an action via `check_falsifier_placement()` but accepts it — coaching, not validation), additive, and never backfilled: it joins `OPTIONAL_BRIEF_FIELDS` in `display.py` so `--json` emits `null` when absent, the jejuge read-boundary precedent. (When it shipped, Dolt still existed and `brief` was one JSON column there too, so a new subfield also survived a write by an older client.) **The authorship rule is rite-side, not schema:** the data layer cannot know who wrote a string, so the human-facing rites ask — `/lay-out` at creation, `/bon-review` at the ceremony's apex (top-N only; adopted 2026-08-09, bon-hipapu) — and leave the field absent when unanswered. A Claude-authored falsifier is `--done` in a hat.

Open items can be **parked Someday/Maybe**: the optional `someday` field holds a required revisit condition (`bon someday ID "condition"` / `bon unsomeday ID`). It's a flag, not a status — status stays open/done so older clients never lose sight of the item. Parked subtrees leave default views at read time (children inherit, no mutation) and `bon list` states the parked count in a tail line; `bon list --someday` is the parked view.

Items can also carry an optional **`area`** tag (Areas of Focus, bon-razonu — `--area` on `new`/`edit`, `''` clears). `bon list --group-by area` clusters the text view ([name] headers sorted, (ungrouped) last); `--area X` filters to one. Grouping keys on top-level items — an outcome's subtree travels with the outcome's area; a parented action's own tag is inert (the CLI coaches, warn not refuse). Like `someday` it's a top-level key, and a JSONL write by an older client keeps keys it doesn't know, so nothing decays. (Under Dolt, retired 2026-10-24, it was a real column that an old client's write stripped — the accepted majoca trade.)

## Adding a Command

1. Add handler in `cli.py`:
   ```python
   def cmd_mycommand(args):
       check_initialized()
       items = load_items()
       # ... implementation
       save_items(items)
   ```

2. Register subparser in `main()`:
   ```python
   mycommand_parser = subparsers.add_parser("mycommand", help="...")
   mycommand_parser.set_defaults(func=cmd_mycommand)
   ```

3. Create `tests/test_mycommand.py` using `run_bon()` helper

4. Update README.md command table

## Adding a Brief Subfield

Every touchpoint below is a place a new subfield gets silently dropped — and
silently is the operative word: the field stores and displays fine while some
consumer never sees it. `how` was lost this way on the first big review run
(0 of 650 items carried it), and `badly` nearly repeated it in the same file.

1. **`display.py` → `OPTIONAL_BRIEF_FIELDS`** — gives `--json` a `null` default at
   the read boundary, so every existing item is covered with no backfill.
2. **`cli.py` → `require_brief_flags()`** — accept it on `bon new` (flag + JSON stdin).
3. **`cli.py` → `EDIT_BRIEF_KEYS` and `edit_flags_given()`** — `bon edit` needs both,
   or the field is accepted and then fails the at-least-one-flag check.
4. **`cli.py` → `cmd_show`** — render it, and decide where; position carries meaning.
5. **Both parsers** — `new_parser` and `edit_parser`.
6. **`skills/bon-review/scripts/audit_survey.py` → the `item_record` field tuple** — the
   review's verification subagents see ONLY this record. Omit it and any skill
   guidance that references the field is inert.
7. **`scripts/bon-read.sh`** — only if the mode you care about renders briefs;
   today `list`/`ready` render titles only, so usually a no-op. Check, don't assume.
8. **Docs:** `docs/CONTRACT.md` (it is contract surface), CLAUDE.md's Data Model,
   README's command table and JSON shape, and the brief table in `skills/open/SKILL.md`.

## Critical Behaviors

### Unblock on Done

When marking done, items waiting for it are automatically unblocked:
```python
for other in items:
    if other.get("waiting_for") == item["id"]:
        other["waiting_for"] = None
```
This is the dependency mechanism. Don't break it.

### Prefix-Tolerant ID Matching

Users can type `gabdur` instead of `bon-gabdur`. The `find_by_id()` function handles this — always use it for lookups.

### Atomic Writes

`save_items()` writes to `.tmp` then renames. Don't bypass this.

### The Bottle (.bon/README.md)

`bon init` writes `.bon/README.md` — the "message in a bottle" telling a stranger
Claude (no CLI, any vendor) how to read the board and route writes as handoff
candidates — and prints a CLAUDE.md/AGENTS.md discovery stanza. The canonical text
is `BOARD_README` in `storage.py`. Every `save_items()`/`save_items_at()` refreshes
a missing or stale copy on the back of the write (same parasitic pattern the
old Dolt repos-table registration used), and `bon doctor` reports staleness / `bon doctor --fix`
repairs it without touching items. So a wording change to `BOARD_README` converges
the estate's static copies as boards get written; dormant boards take the doctor
route.

### Merge-Friendly Storage

`save_items()` sorts by ID before writing, producing deterministic line order.
`.gitattributes` uses `merge=union` for `.bon/*.jsonl` so concurrent branches
that touch different items merge cleanly. `load_items()` deduplicates by ID
(last occurrence wins) to handle union merge artifacts where both old and new
versions of an edited line survive.

**What merges cleanly:** Two branches adding different items. Two branches
editing different items (when 3+ unchanged lines separate them).

**What still conflicts:** Two branches editing the same item, or editing
adjacent items. This is acceptable — it means two sessions touched the same
work, which needs human resolution anyway.

## Testing Patterns

**Fixtures** (`fixtures/*.jsonl`): Snapshot data for parametrized tests
**Runner** (`conftest.py`): `run_bon(*args, cwd=...)` subprocess helper

```python
def test_something(bon_dir):
    result = run_bon("list", cwd=bon_dir)
    assert result.returncode == 0
    assert "Expected output" in result.stdout
```

Parametrized fixture loading:
```python
@pytest.mark.parametrize("bon_dir_with_fixture", ["outcome_with_actions"], indirect=True)
def test_with_data(bon_dir_with_fixture):
    result = run_bon("list", cwd=bon_dir_with_fixture)
```

## Common Patterns in cli.py

```python
check_initialized()              # Always first — errors if no .bon/
items = load_items()             # Load current state
prefix = load_prefix()           # Get ID prefix
item = find_by_id(items, id, prefix)  # Lookup (handles prefix tolerance)
error("Message")                 # Print to stderr, exit 1
save_items(items)                # Atomic write back
```

### `bon new` Input Modes

`bon new` accepts items via three paths, auto-detected:

1. **JSON stdin (default for piped input)**: No title arg + stdin is piped → reads JSON from stdin. No `--json` flag needed.
2. **Flags**: Title as positional arg + `--why`/`--what`/`--done` flags. For quick stubs.
3. **Interactive**: TTY + no flags → prompts for brief fields.
4. **Explicit `--json`**: Forces JSON stdin regardless of other args. Backward-compatible.

```bash
cat <<'EOF' | bon new -q          # JSON stdin (auto-detected)
{"title":"...","brief":{"why":"...","what":"...","done":"..."}}
EOF
bon new "Quick fix" --why w --what x --done d -q   # Flags (stubs only)
```

The JSON path accepts `title`, `type`, `parent`/`outcome`, `waiting_for`, `area` and `brief` —
brief subfields nested or flat (flat-and-nested conflict errors). `waiting_for` (string
or list) creates the item born blocked, with cmd_wait's unresolvable-id warning. Any
other key is a **hard error** (bon-gezela) — a silently-dropped key looks exactly like
success, the same contract `bon edit` adopted in bon-cefisu.

**Stdin never hangs (bon-zutowo).** Both `bon new` and `bon edit` wait at most 10 s for the first byte of piped JSON, then fail naming the cause; `BON_STDIN_TIMEOUT` overrides (`0`/`inf` = no limit). JSON passed as an argument is refused at once with a pipe hint — an agent's Bash tool hands an open-but-silent stdin, which used to block forever.

### `bon edit` Input Modes (bon-cefisu)

Same auto-detection, same reason — flag quoting mangles briefs carrying quotes,
backticks or `$`, and a mangled field looks exactly like an edited one.

1. **JSON stdin (default for piped input)**: No edit flag + stdin piped → reads JSON.
2. **Flags**: any of `--title/--outcome/--why/--how/--what/--done/--note/--order/--area`, and `--append-how/--append-why/--append-what/--append-done` to add to a field rather than overwrite it.
3. **Explicit `--json`**: forces the stdin path; an empty stdin errors here rather
   than falling through.

Only keys **present** in the JSON are applied. Brief subfields are accepted nested
under `brief` *or* flat at the top level, because Claude's prior is the flat form and
a silently-dropped key would print `Updated` having changed nothing. An unknown key is
a hard error for the same reason. `edit_args_from_stdin()` overlays the parsed JSON
onto `args`, so exactly one apply path runs whichever way the edit arrived — add new
editable fields to `EDIT_TOP_KEYS`/`EDIT_BRIEF_KEYS` **and** `edit_flags_given()`.

`--note` writes `done_note` and requires the item to be done. It exists because
`cmd_done` refuses to overwrite an existing note (cli.py, the `Already done` branch),
which made a shell-mangled closing note permanent.

## Gotchas

| Gotcha | Fix |
|--------|-----|
| Forgetting `check_initialized()` | Add at command start |
| Direct file writes | Use `save_items()` for atomicity |
| Reading JSONL by line position | Items are sorted by ID, not insertion order. Find by type/ID, not `lines[N]` |
| Case-sensitive ID lookup | Use `find_by_id()` with prefix |
| Breaking unblock-on-done | Test with `waiting_dependency` fixture |
| Standalone actions forgotten | Check items where `parent` is None. Create with `type: "action"` in JSON stdin |
| Interactive mode untested | Test with `input=` parameter |
| Mixed-case IDs (bon-huHida) | Pre-lowercase legacy. IDs are immutable — don't try to rename |
| Changing schema fields | bon-read.sh reads items.jsonl directly with jq |
| Repairing duplicate sibling orders with `bon edit --order` | `--order` is a positional MOVE, not raw assignment — it assumes unique sibling orders, so each single-move "repair" re-mints the dup one rung down. `bon doctor --fix` resequences the group 1..N (by order, then created_at); repair lives with detection (bon-tagoje) |
| Releasing a tactical claim | `bon work --release` keeps steps+current and sets `tactical.released`; `--clear` discards. `_tactical_is_active()` in storage.py is the single gate — released is not active, so it can't block, inject, or read as orphaned. The two raw-JSONL readers (`scripts/bon-read.sh`, `hooks/bon-tactical.sh`) each need the check independently; they bypass storage.py |
| Adding a nested tactical key | Put it INSIDE the tactical object, not beside it as an item column. `tactical` round-trips as one opaque JSON value, so a nested key travels with the claim it describes. (The original reason was Dolt's fixed `_ITEM_COLUMNS` list, which stripped a new top-level column on an older client's write; Dolt is retired and JSONL keeps unknown keys, so this is now convention, not survival.) |
| Tactical lookup ignoring session | Always pass `session=os.getcwd()` to `find_active_tactical()`. Omitting it returns only unscoped (legacy) tacticals. |
| Stale global install after code changes | `uv tool install` reuses a cached *build* of the local source, and `uv cache clean bon` does **not** clear it. Since bon's version is dynamic from `plugin.json` (hatchling regex-read), a bump touching only `plugin.json`/CLAUDE.md leaves `src/` byte-identical, so the old wheel is reused and the version never moves (verified 2026-06-17). Force a real rebuild with `--no-cache`: `uv tool install ~/repos/spm1001/bon --force --reinstall --no-cache` |
| Session identity | Use `get_session_identity()` not `os.path.realpath(os.getcwd())`: it is the realpath of the board root, so every subdir of one repo shares one claim. |
| A clone still carrying `.bon/backend=dolt` | It predates its board's move (Dolt retired 2026-10-24). `check_initialized()` and every board write refuse with `storage.DOLT_RETIRED`, which says `git pull`. Never restore a Dolt path to read such a clone. |

## Storage

Every board is `.bon/items.jsonl` (plus `archive.jsonl`) in its own repo, git-tracked, zero dependencies.

**History: Dolt, March to October 2026.** Bon had an optional Dolt (MySQL-compatible) backend from 2026-03-21. On 2026-10-24 all 18 Dolt boards migrated back to JSONL in their repos with empty id+content diffs (bon-bozocu), the `dolt-bon` server was stopped, and the same evening `dolt.py`, `migrate`, `register`, `init --backend`, the `[dolt]` extra and the Dolt tests were deleted (bon-sujeno). The full Dolt history is archived in the private, archived repo `spm1001/bon-dolt-backup`: a native `dolt clone`-able copy, a tarball of the data directory as a release asset, and `readable/` (plain JSONL of every board and every recorded change). What survives in code: a clone still carrying `.bon/backend=dolt` is refused with `storage.DOLT_RETIRED` ("git pull"), and the half-pulled guard (bon-famuwi: `.bon/backend` gone from disk but still tracked by git as `dolt`, `items.jsonl` untracked) still refuses a write that would start a second board. The review survey's Dolt reader went in bon-hetewa: `audit_survey.py` and `net_motion.py` read only the boards cloned on the machine, and name any clone still carrying `backend=dolt` as stale (`stale_clones`) rather than counting it.

**Concurrency on one clone** (bon-beneba, 2026-09-25): every JSONL save takes a per-board flock (lock file under `$XDG_CACHE_HOME/bon/locks/`, outside the repo) and merges at item grain with the file on disk before its atomic rename, so two processes on one clone commute; an item both changed refuses loudly. Across clones, gitsync's rebase + item-grain merge does the same job.

**JSONL boards sync themselves on write (bon-guritu, `src/bon/gitsync.py`).** Every
mutating verb on a JSONL board runs fetch → rebase → item-grain merge → write →
commit → push, so teammates' clones converge with no git discipline. Engagement is
self-gating: items.jsonl must be git-TRACKED (committing the board is the deliberate
adoption step — fresh `bon init` boards and gitignored `.bon/` repos never sync), the
branch needs a configured upstream, and `.bon/sync` containing `off` disables it
(`~/notes` carries that marker: notes-sync owns every git write there; `BON_SYNC=off`
in the environment is the per-process override). Conflict semantics are
two-tier (the second tier added after a live essayeur refutation, 2026-08-30): an
IN-SESSION collision (this verb's change vs origin) is ONE loud refusal before
anything is written — origin's version stays in the tree, the verb's change is not
applied, nothing lost; a WHILE-APART collision (an already-committed offline/deferred
edit meeting origin's at integration) resolves newest-wins with every displaced
version preserved in the committed `.bon/sync-conflicts.jsonl` sidecar, the collision
named loudly, and a standing warning on every clone's every verb until the sidecar is
reviewed and deleted. Offline degrades to write + commit locally with one warning,
and a later verb pushes the backlog; a push is refused (with the reason named) when
unpushed commits touch non-board files, so a board verb can never publish code as a
side effect. The item-grain three-way
merge (`merge_items`) is the same grain lesson as the old Dolt diff-at-save: a whole-file
write after an integrate would clobber the other clone. `bon init` seeds
`.bon/.gitattributes` (`*.jsonl merge=union`) so the git-level merge is line-wise
under rebase.

**Recovery on a JSONL board is `bon restore ID`** (bon-wibota): an item lost from
items.jsonl or archive.jsonl comes back from git history, ranked by the item's own
timestamps rather than commit order. Never hand-edit the board to recover one.

## Key Files

| Need to... | Read... |
|------------|---------|
| Understand architecture & invariants | `.bon/understanding.md` |
| See expected outputs | `fixtures/*.jsonl` |
| Add/modify command | `cli.py` |
| Change storage format | `storage.py` |
| Update Claude integration | `skills/open/SKILL.md` |
| Docket/rite boundary (probe, query surface, ownership) | `docs/CONTRACT.md` |
| Handoff format spec | `docs/HANDOFF-CONTRACT.md` |
| Where handoffs/understanding.md resolve (READ+WRITE share this) | `scripts/lib-handoff.sh` |
| Test bon-read.sh | `tests/test_bon_read.py` |
| Crumb list: unclosed sessions shown at session start (scanner, cache, `--dismiss`) | `scripts/crumbs.py` (section 2a of `open-context.sh`; tests `tests/test_crumbs.py`) |



## README skill table is generated

The Skills table in README.md (between `GENERATED:SKILLS` markers) is rendered from
`skills/*/SKILL.md` frontmatter — never hand-edit it. After adding, removing or renaming
a skill: `uv run --script ../batterie-de-savoir/scripts/render-skills.py .` from the repo
root. CI re-checks it on every push (fetching the canonical script from batterie-de-savoir
raw main), so a stale table fails the build. If a table one-liner reads badly, fix the
SKILL.md description (skill-forge), not the table.

**Notes room:** `~/notes/practices/cohabiting-codebases/` — the pattern language this tool is the largest worked example of. (bon-jezahi, 2026-08-16)
