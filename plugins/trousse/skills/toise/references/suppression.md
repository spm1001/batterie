# Suppression List

What the architecture reviewer should NOT flag. Organised by principle.

## General

- **Generated files.** If a generated-files manifest exists, skip those files entirely. If no manifest exists but files contain `@generated` or "do not edit" headers, skip them.
- **Vendored/third-party code.** Anything under `vendor/`, `third_party/`, `node_modules/`, or similar directories.
- **One-off scripts.** Files explicitly in a `scripts/` directory that are clearly utility scripts, not core architecture.
- **Config files.** `.toml`, `.yaml`, `.yml`, `.json` config files don't need first-breath documentation.
- **Lock files.** `uv.lock`, `Cargo.lock`, `package-lock.json`, etc.

## Principle 1: Self-Documenting Files

- **`__init__.py`** — empty init files are idiomatic Python; don't penalise.
- **Tiny files** (under 10 lines) — too small to need a header comment.
- **Test files** — test function names are self-documenting; a module docstring is nice but not required.
- **Shebang-only scripts** — a shebang + one comment line is sufficient for shell scripts.
- **`mod.rs` / `index.ts`** — re-export modules don't need extensive documentation if the module name is descriptive.

## Principle 2: One Shape, Everywhere

- **Justified deviations** documented in CLAUDE.md or with inline comments explaining why.
- **Different languages** in a polyglot repo — each language should be internally consistent, but Python modules don't need to match Rust modules.
- **Test utilities** vs production code — test helpers may follow different patterns.

## Principle 3: Boundaries

- **Single-crate/single-package repos** — boundary artefacts are less critical when the whole project is one module. Don't penalise the absence of a module map for a repo with 5 files.
- **Missing `AGENTS.md`** if `CLAUDE.md` is comprehensive — one is sufficient.
- **Missing generated-files manifest** if the project has no code generation.
- **Missing `understanding.md`** — its absence is neutral, not negative. It grows through use; new projects won't have one.

## Principle 4: Small, Pure, Explicit

- **Test files** may exceed 500 lines — test suites that group related cases in one file are fine.
- **Generated files** — size doesn't matter for files no one reads.
- **CLI entry points** — a `cli.py` or `main.rs` that dispatches commands may be long; check whether it could be split, but don't auto-flag.
- **Data files** — SQL schema dumps, migration files, fixture data.

## Principle 5: Extension Recipes

- **Repos that don't need extension.** A finished tool with no expected extension points doesn't need recipes. Only flag if the project is actively maintained and growing.
- **Small repos** (under 10 source files) — the code IS the recipe at this scale.
- **Recipes in `understanding.md` or inline comments** — not only CLAUDE.md. If extension guidance exists somewhere discoverable, that counts.

## Confidence Calibration

Suppress findings below 0.60 confidence. The reviewer should only report issues it can trace to specific files and evidence.

- **High confidence (0.80+):** Full evidence chain — specific files, specific lines, specific principle violation.
- **Moderate (0.60-0.79):** Pattern is present but depends on context not fully visible.
- **Low (below 0.60):** Suppress. Gut feeling without evidence is not a finding.

Exception: if a critical artefact is missing (no CLAUDE.md in a repo with 50+ source files), report at 0.50+ confidence.
