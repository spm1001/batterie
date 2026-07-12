# Batterie de Savoir — Agent Guide

This repo has **two jobs**: it is the **documentation umbrella** for the Batterie de Savoir tool suite (docs, registry, generation scripts — no runnable tools), **and the source of the suite-level `batterie` plugin** that [`spm1001/batterie`](https://github.com/spm1001/batterie) assembles and distributes (see "The Marketplace Lives Elsewhere" below). The two repos are a source/artifact pair: author here, consume there. Retirement was assessed and rejected 2026-06-11 — "batterie is the marketplace anchor" is true of distribution only; this repo stays.

## What this repo does

- `brigade.toml` — single source of truth for all tool metadata
- `scripts/render.py` — regenerates GENERATED sections in docs from the registry
- `scripts/lint.py` — detects drift between registry and docs (exit 1 if stale)
- `docs/` — Jekyll site, published to GitHub Pages

## The one rule

**Edit `brigade.toml`, then run `uv run --script scripts/render.py`.**

Adding or changing a tool means touching exactly one file. The render script handles the rest. Never hand-edit content between GENERATED markers — it will be overwritten. Two marker formats exist: HTML comments (`<!-- GENERATED:*:START -->`) in README.md, and Liquid comments (`{% comment %}GENERATED:*:START{% endcomment %}`) in docs/ files. The dual format exists because kramdown treats HTML comments as block elements that break table parsing, while Jekyll strips Liquid comments before kramdown runs.

To check for drift without writing: `uv run --script scripts/lint.py`

## What's generated vs authored

| File | Status |
|------|--------|
| Brigade tables in `README.md`, `docs/index.md` | **Generated** — run render.py |
| Vocabulary, routing, deps, repos in `docs/for-agents.md` | **Generated** — run render.py |
| `docs/tools/*.md` — individual tool pages | **Hand-authored** — never generated |
| `docs/getting-started.md` | **Hand-authored** |
| `docs/principles.md` | **Hand-authored** |
| `docs/MAINTAINING.md` | **Hand-authored** |

Tool pages are hand-authored by design. The registry holds one-liners; tool pages hold judgement.

## Versioning convention

**This is the canonical description of how the suite is versioned and released.** Component repos carry a thin pointer back here; this section (plus `.bon/understanding.md`) is the full picture.

**One version number across the whole suite.** Since 2026-06-28 (suite 1.2.2) every published plugin — `batterie`, `bon`, `trousse`, `mise`, `todoist-gtd` — carries the *same* version. The earlier "Debian model" (independent per-plugin numbers under a headline suite number) is **dead**: the suite is operated as a unit — the assembler re-vendors it whole daily, and `/batterie:update` pulls every plugin in one go — so per-plugin granularity was never consumed, only confusing.

**Source of truth: the `batterie` plugin's `plugin.json` version (this repo) IS the suite version.** You never hand-edit it to release — `/batterie:publish` bumps it centrally (below).

**How the one number reaches every plugin — the assembler stamps it.** `spm1001/batterie`'s `assemble.sh` vendors each source repo's plugin content, then *overwrites* every vendored `plugin.json` version with the suite version. Consequences:

- **A source repo's own `plugin.json` version is local-dev-only** — hatchling reads it for the CLI `--version` footnote (below), but it's irrelevant to what ships. **Do NOT hand-bump a source `plugin.json` to "release"** — the stamp overwrites it. `/batterie:publish` is the only lever.
- **The ratchet is suite-level.** If a plugin's vendored *content* changed but the *suite* version didn't bump, the assembler **quarantines** that plugin (keeps it at its last-good version) rather than shipping an unversioned change. So any vendored-content edit needs a suite bump to actually ship — see the GOTCHA below.
- `pyproject.toml` still uses `dynamic = ["version"]` reading `.claude-plugin/plugin.json` via a hatchling regex — never a hardcoded version. Repos on this pattern: **bon, mise-en-space, trousse, todoist-gtd** (passe left the suite 2026-07-07 — see "The Marketplace Lives Elsewhere"). A new tool with a `pyproject.toml` follows the same pattern.

**Releasing: `/batterie:publish` from the edited repo's working tree.** It bumps the suite version centrally (this repo's `plugin.json`), commits, pushes, triggers `assemble.yml`, watches it green, and pulls this machine current. Editing a *non*-`batterie` source repo makes it a **2-repo push** (the content repo + the central suite bump). Never run `assemble.sh` locally — assembling is CI's job. (Engine: `scripts/publish.py`.)

**One version → one changelog (bds-mawitu, suite 1.8.2).** There is a single canonical `CHANGELOG.md` in *this* repo (the suite anchor). At release, `publish.py` prepends a dated `## [<suite-version>] - <date>` entry with a one-line narrative — passed via `--changelog "line"` (the `/batterie:publish` skill prompts for it) and defaulting to the commit message, so an entry is *always* written and a shipped changelog can never predate its release. Shipped plugins do **not** carry their own changelog: `assemble.sh` writes each a small *generated stub* (suite version + pointer back to this repo's `CHANGELOG.md`) instead of vendoring per-repo ones. Because the stub is a pure function of the suite version — regenerated identically every run, like the stamped `plugin.json` version — it's filtered out of the ratchet's drift check (miss that filter and a generated artifact's first appearance quarantines every plugin at once). Editing `CHANGELOG.md` itself is free (source-only, not vendored).

### The CLIs keep their own numbers (lazy convergence)

The plugin version is one number; the **CLIs** (`bon` / `passe` / `todoist --version`) are NOT stamped to it. A CLI's `--version` reads *the suite release that last **changed** that CLI* — `publish.py` lazy-stamps only the source repo being published (japoca, 2026-07-06). So CLIs converge toward the suite number over normal releases with no multi-repo dance every release (the dance the 2026-06-28 scope decision explicitly rejected). What a Claude should know:

- `/batterie:version` shows the suite number as headline, each CLI's own `--version` as a **footnote** — a CLI number *below* the suite number is expected, not drift.
- **Session hooks are install-if-missing only** — no version-drift check at session start (that produced a false reinstall every session). They install a *missing* CLI and report the version that actually landed.
- **`/batterie:update`'s CLI-drift check is commit-based** — installed commit (`direct_url.json` in the tool's dist-info) vs `git ls-remote` HEAD of the source repo, no version semantics. Install source is provenance-sticky: a `~/repos` clone appearing doesn't flip an install onto the working tree.

### Surfaces

- **`/batterie:version`** — suite version (headline) + every installed plugin + CLI `--version` (footnotes). The canonical "what am I on?" answer.
- **`/batterie:update`** — suite-version banner atop the update; **marketplace-aware** (`bds-lodita`): updates plugins across every batterie-family marketplace — the public one and the family-private Directory one.

### GOTCHA — which edits need a suite bump

The assembler vendors each source repo's `CLAUDE.md`, `instructions.md`, `skills/`, `hooks/`, `.claude-plugin/`. So editing any of those in a source repo — **including this one** — is a *content change* the suite ratchet catches: it must ride a suite bump (ship it via `/batterie:publish`) or the assembler quarantines the plugin. A `docs/` or `.bon/` edit is **free** (not vendored). Rule of thumb: inside vendored content → rides a publish; docs-site or bon bookkeeping → doesn't.

## Deliberate quirks — do not "fix" these

- **jeton has no public README** — it's the renamed `itv-google-auth` library. A 404 when fetching its README is expected.
- **`lint.py` imports `render.py` via `sys.path`** — intentional. Keeps one set of templates so lint tests exactly what render produces. Only safe because render.py's module-level code is side-effect-free (loads TOML, builds templates). Don't refactor by duplicating the rendering logic.
- **`from = ["all"]` in `[[dependency]]`** — sentinel for "All tools" in the dependency direction table. Documented in brigade.toml's schema comment.
- **Vocabulary and key-repos have static rows in separate tables** — GTD terms (Brigade, Outcome, Action, etc.) live in a "GTD & Brigade Terms" sub-table below the generated vocabulary table. The "This docs site" row lives in a separate mini-table below the generated key-repos table. Both are intentionally excluded from generation. The split exists because kramdown can't parse a table that spans across comment markers.

## Local Jekyll preview

Test rendering before pushing: `docker run --rm -v "$PWD/docs:/srv/jekyll" -p 4000:4000 jekyll/jekyll jekyll serve`. Saves deploy-wait-screenshot cycles — kramdown quirks (HTML comment blocks, SmartyPants em-dash conversion) only show up in the real Jekyll pipeline, not in GitHub's GFM preview.

## Python version note

This machine runs Python 3.9, which doesn't have `tomllib` (added in 3.11). The PEP 723 scripts declare `tomli; python_version < '3.11'` as a dependency — `uv run --script` handles this automatically. Don't validate TOML with bare `python3 -c "import tomllib"` — it'll fail. Use `uv run --with tomli python3 -c "import tomli; ..."` or just run the scripts via uv.

## The Marketplace Lives Elsewhere

This repo **stopped being a marketplace on 2026-06-10** (the bds-bajibo cutover — there is no `marketplace.json` here anymore). [`spm1001/batterie`](https://github.com/spm1001/batterie) is the single assembled marketplace, serving the **CLI and personal Desktop installs** (both accept a public repo). It vendors each plugin's content physically (Desktop's backend rejects external URL sources), reassembled daily by its GitHub Actions bot from the source repos. **The claude.ai *org/Teams* Directory is NOT a working surface for this repo — see "Repo visibility" below.**

This repo remains a **source repo**: the suite-level `batterie` plugin (`.claude-plugin/plugin.json`, `skills/`, `hooks/`, `instructions.md`) is vendored from here. To ship a change to it (or to any batterie source repo): **`/batterie:publish`** from the repo's working tree — it bumps the suite version, commits, pushes, triggers `assemble.yml`, watches it green, and pulls this machine current (`scripts/publish.py` is the engine). Under the hood, publish bumps the **suite** version (this repo's `plugin.json`) — *never* a source repo's own — and triggers the assemble (the daily bot also runs it, or `gh workflow run assemble.yml -R spm1001/batterie` fires it now). See **Versioning convention** above for the single-version mechanics. A commit landing in spm1001/batterie is what makes clients re-resolve plugins — its commit stream is the suite's update bus.

**passe was delisted from the suite on 2026-07-07** (browser infra, not a knowledge plugin — `bds-wobari`): it's no longer assembled or stamped, and its CLI installs standalone. tube was uninstalled + registry-swept the same day (`bds-tujoro`, done); hezza (deprecating) and possibly the Mac still carry an orphaned `passe@batterie` plugin — harmless, but their `/batterie:update` errors once on it until `claude plugin uninstall passe@batterie` runs there.

Anyone who installed plugins as `<name>@batterie-de-savoir` before the cutover migrates by add + reinstall + remove (plugin keys change with the marketplace name; a plain repoint isn't enough).

### Repo visibility — deliberately PUBLIC (and what that costs)

`spm1001/batterie` is **public on purpose** (decided 2026-06-20, `bds-kanuve`): ITV + public users install via `claude plugin marketplace add spm1001/batterie`, and personal Desktop installs (Customize → Add marketplace) also accept a public repo. The cost, accepted knowingly: **org/Teams Directory marketplaces require a _private or internal_ repo** — public is rejected by Anthropic policy (error: *"Only private and internal repositories can be used for marketplaces"* on the org sync endpoint; documented at code.claude.com/docs/en/plugin-marketplaces). "Internal" isn't available here — it needs a GitHub Org/Enterprise, and `spm1001` is a personal account.

**So the Teams Directory one-click path is unavailable for this repo. Do NOT re-add the org marketplace (it errors on every sync), and do NOT flip the repo private to "fix Teams" — that breaks the CLI/personal path everyone actually uses.** Family-scale users get a *separate private* Directory marketplace — `spm1001/batterie-home`, built and owner-verified 2026-07-07 — carrying a planetmodha-cred flavour of mise (`mise-home`); the missing planetmodha OAuth cred for mise (not distribution) was always the blocker. Public plugins still come from here, and `/batterie:update` is marketplace-aware (`bds-lodita`) so one update spans both the public and the private marketplace. Tracked under `bds-niluga` (one non-admin family install remains to verify member-level access — `bds-bajaja`). (Separately, Desktop's *personal* marketplace can serve a stale pre-cutover snapshot — a server-side Anthropic cache bug tracked in `bds-hitoga`, not this visibility policy.)

### Debugging Desktop marketplace

- UI errors are opaque ("Marketplace sync failed")
- Real errors: `~/Library/Logs/Claude/claude.ai-web.log` — shows per-plugin validation results
- Sync status: `~/Library/Logs/Claude/main.log` — shows `failed_content` / `success` / `in_progress`

## Open outcomes

Tracked on the bon board, not hand-listed here (a hand-maintained list drifts — see `bds-naceje`). Run `bon list` for current outcomes and actions.
