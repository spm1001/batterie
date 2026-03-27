# consommé — Project Context

BQ data analysis skill ("consommé") for Claude Code and Amp. Combines Google's BQ Data Analytics MCP tools with systematic profiling methodology.

## Skill Location

The skill source lives at `skills/analysis/` in this repo. It's installed via the plugin system:

```bash
claude plugin install spm1001/consomme
```

For local development, the plugin resolves to this repo. Editing the source files here updates the installed skill immediately.

## Test Data

- **Project:** `mit-consomme-test`
- **Dataset:** `survey_data`
- **Table:** `ohid_survey_raw` — 1,320 rows, 39 columns, OHID mental health survey
- **Datamap:** `test-data/ohid-datamap.md` — full question text and value labels for all columns
- **MCP tools:** Pass `project=mit-consomme-test` to every BQ MCP tool call

## Key Files

| File | Purpose |
|------|---------|
| `skills/analysis/SKILL.md` | Main skill (352 lines, lint 100/100) |
| `skills/analysis/references/` | 6 reference files (profiling, stats, SQL, dashboard) |
| `docs/TESTING.md` | Test plan and results (Rounds 1-2 complete) |
| `test-data/ohid-datamap.md` | Survey codebook with value labels |
| `.bon/` | Work tracking — `bon list` for outstanding items |

## Testing Status

- **Round 1 (SQL validation):** PASSED — all SQL snippets execute correctly
- **Round 2 (workflow testing):** PASSED — shape detection, survey profiling, analyze_contribution, Chart.js dashboard, search_catalog
- **Round 3 (timeseries + warehouse):** PENDING — needs temporal and multi-table datasets
- **Round 4 (Claude Code parity):** PENDING

## Dependencies

- BQ MCP server (`bq-toolbox`) configured in `~/.config/amp/settings.json` (Amp) or Claude Code MCP config
- Application Default Credentials for BQ auth
- `skill-forge` skill for linting and CSO scoring
