# Batterie de Savoir — Agent Guide

This is the **documentation umbrella repo** for the Batterie de Savoir tool suite. It contains no runnable tools — just docs, a registry, and generation scripts.

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
- `/batterie-update` triggers when the installed plugin.json version is lower than the repo's — so bumping plugin.json is what drives updates

Repos aligned on this pattern: bon, passe, garde-manger, mise-en-space, trousse. If you add a new tool with a pyproject.toml, follow the same pattern.

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

This repo **stopped being a marketplace on 2026-06-10** (the bds-bajibo cutover — there is no `marketplace.json` here anymore). [`spm1001/batterie`](https://github.com/spm1001/batterie) is the single assembled marketplace for every surface — CLI, Desktop, and the claude.ai org. It vendors each plugin's content physically (Desktop's backend rejects external URL sources), reassembled daily by its GitHub Actions bot from the source repos.

This repo remains a **source repo**: the suite-level `batterie` plugin (`.claude-plugin/plugin.json`, `skills/`, `hooks/`, `instructions.md`) is vendored from here. To ship a change to it: edit, bump the version in `.claude-plugin/plugin.json`, push — the daily bot does the rest (or trigger immediately with `gh workflow run assemble.yml -R spm1001/batterie`). A commit landing in spm1001/batterie is what makes clients re-resolve plugins — its commit stream is the suite's update bus.

Anyone who installed plugins as `<name>@batterie-de-savoir` before the cutover migrates by add + reinstall + remove (plugin keys change with the marketplace name; a plain repoint isn't enough).

### Debugging Desktop marketplace

- UI errors are opaque ("Marketplace sync failed")
- Real errors: `~/Library/Logs/Claude/claude.ai-web.log` — shows per-plugin validation results
- Sync status: `~/Library/Logs/Claude/main.log` — shows `failed_content` / `success` / `in_progress`

## Open outcomes

- `bds-lozeti` — Track Claude Office add-in bundle changes over time
