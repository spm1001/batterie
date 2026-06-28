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

**`plugin.json` is the single source of truth for version numbers across the entire suite.**

- `pyproject.toml` uses `dynamic = ["version"]` with `[tool.hatch.version]` pointing at `.claude-plugin/plugin.json` via regex — never has a hardcoded version
- To bump a version: edit the `"version"` field in `.claude-plugin/plugin.json` only
- `/batterie:update` triggers when the installed plugin.json version is lower than the repo's — so bumping plugin.json is what drives updates

Repos aligned on this pattern: bon, passe, mise-en-space, trousse. If you add a new tool with a pyproject.toml, follow the same pattern.

### Suite version (the human-facing number)

The **`batterie` plugin's own version doubles as the suite version** — the single number a user quotes ("I'm on Batterie v1.0") or checks against ("you need ≥ v1.x"). It's the Debian model: one headline number on top of the independent per-plugin versions (`bon 0.26.5`, `passe 0.6.2`, …), which stay separate so each plugin's "update available" signal only fires when *that* plugin actually changes.

- **Set it at milestones**, not every change — bump the `batterie` plugin.json to a round number when the suite reaches a meaningful state (set to `1.0.0` on 2026-06-20, the first real suite release). Patch ticks still happen when the batterie plugin itself changes; that's fine.
- **Surfaced via `/batterie:version`** (reports suite version + per-plugin + CLI versions) and as a banner atop `/batterie:update`. The "build date" half is the clients' own "last updated" date — no extra machinery needed.
- Distribution is **public CLI** (`claude plugin marketplace add spm1001/batterie`); the Teams/org Directory is unavailable (see "Repo visibility"). So `/batterie:version` is the canonical "what am I on?" surface.

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

This repo remains a **source repo**: the suite-level `batterie` plugin (`.claude-plugin/plugin.json`, `skills/`, `hooks/`, `instructions.md`) is vendored from here. To ship a change to it (or to any batterie source repo): **`/batterie:publish`** from the repo's working tree — it bumps the version, commits, pushes, triggers `assemble.yml`, watches it green, and pulls this machine current (`scripts/publish.py` is the engine). Under the hood that is: edit, bump `.claude-plugin/plugin.json`, push — the daily bot does the rest (or trigger immediately with `gh workflow run assemble.yml -R spm1001/batterie`). A commit landing in spm1001/batterie is what makes clients re-resolve plugins — its commit stream is the suite's update bus.

Anyone who installed plugins as `<name>@batterie-de-savoir` before the cutover migrates by add + reinstall + remove (plugin keys change with the marketplace name; a plain repoint isn't enough).

### Repo visibility — deliberately PUBLIC (and what that costs)

`spm1001/batterie` is **public on purpose** (decided 2026-06-20, `bds-kanuve`): ITV + public users install via `claude plugin marketplace add spm1001/batterie`, and personal Desktop installs (Customize → Add marketplace) also accept a public repo. The cost, accepted knowingly: **org/Teams Directory marketplaces require a _private or internal_ repo** — public is rejected by Anthropic policy (error: *"Only private and internal repositories can be used for marketplaces"* on the org sync endpoint; documented at code.claude.com/docs/en/plugin-marketplaces). "Internal" isn't available here — it needs a GitHub Org/Enterprise, and `spm1001` is a personal account.

**So the Teams Directory one-click path is unavailable for this repo. Do NOT re-add the org marketplace (it errors on every sync), and do NOT flip the repo private to "fix Teams" — that breaks the CLI/personal path everyone actually uses.** Family-scale users will get a *separate private* Directory marketplace carrying a planetmodha-cred flavour — the missing planetmodha OAuth cred for mise (not distribution) was always the blocker; public plugins still come from here, and `/batterie:update` is now marketplace-aware (`bds-lodita`) so one update spans both the public and the private marketplace. Tracked under `bds-niluga`. (Separately, Desktop's *personal* marketplace can serve a stale pre-cutover snapshot — a server-side Anthropic cache bug tracked in `bds-hitoga`, not this visibility policy.)

### Debugging Desktop marketplace

- UI errors are opaque ("Marketplace sync failed")
- Real errors: `~/Library/Logs/Claude/claude.ai-web.log` — shows per-plugin validation results
- Sync status: `~/Library/Logs/Claude/main.log` — shows `failed_content` / `success` / `in_progress`

## Open outcomes

- `bds-lozeti` — Track Claude Office add-in bundle changes over time
