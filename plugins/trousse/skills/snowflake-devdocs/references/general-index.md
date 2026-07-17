# General Snowflake index — beyond the Lantern slice

For Snowflake questions *not* about the exposure-lake decision (that's `lantern-index.md`).
A curated map of the high-traffic surfaces + Cortex/CoCo. For anything not here, use
`discovery.md` to grep a section sub-index. Every URL fetches Markdown (`curl <url>`).

**Verified live 2026-07-17.** If a slug 404s, re-discover via `discovery.md`.

---

## A. Core SQL & types
- SQL command reference — https://docs.snowflake.com/en/sql-reference-commands.md
- Function & stored-procedure reference — https://docs.snowflake.com/en/sql-reference-functions.md
- Snowflake data types — https://docs.snowflake.com/en/data-types.md
- Snowflake Scripting (stored-proc language) — https://docs.snowflake.com/en/sql-reference-snowflake-scripting.md
- (For a specific command/function, grep the section sub-index in `discovery.md` — SQL Commands 683 pages, SQL Functions 999.)

## B. Cortex — AI & ML
- Snowflake AI & ML (overview) — https://docs.snowflake.com/en/guides-overview-ai-features.md
- **Cortex AISQL** (AI/LLM functions in SQL) — https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql.md
- Cortex Search (semantic retrieval) — https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview.md
- Cortex Analyst (NL→SQL over semantic views) — https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst.md
- Cortex Agents (invoke an agent as a tool) — https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents.md
- (Full section: `snowflake-cortex/llms.txt`, 103 pages.)

## C. Data loading & pipelines
- Load data into Snowflake (overview) — https://docs.snowflake.com/en/guides-overview-loading-data.md
- Continuous load w/ Snowpipe (cloud messaging) — https://docs.snowflake.com/en/user-guide/data-load-snowpipe-auto.md
- Dynamic Tables (declarative pipelines) — https://docs.snowflake.com/en/user-guide/dynamic-tables/overview.md

## D. Query & performance
- Query data (overview) — https://docs.snowflake.com/en/guides-overview-queries.md
- Optimizing performance (overview) — https://docs.snowflake.com/en/guides-overview-performance.md
- Overview of warehouses (compute) — https://docs.snowflake.com/en/user-guide/warehouses-overview.md

## E. Editions & cost
- Snowflake editions (Standard / Enterprise / Business Critical) — https://docs.snowflake.com/en/user-guide/intro-editions.md
- Cost & billing (overview) — https://docs.snowflake.com/en/guides-overview-cost.md
- (Detailed cost/egress pages live in `lantern-index.md` §D.)

## F. CoCo (Cortex Code) — Snowflake's agentic coding CLI

CoCo (rebranded from **Cortex Code** at Summit, 2 Jun 2026; CLI GA 2 Feb 2026) is Snowflake's
data-native AI coding agent — "Claude Code for Snowflake." It knows your schemas / RBAC / lineage
and writes+runs SQL, dbt, and pipelines. Three surfaces: Snowsight, a desktop IDE, and a local CLI.

- CoCo (overview) — https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code.md
- CoCo CLI — https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli.md
- **CoCo CLI bundled skills** (50+, listed) — https://docs.snowflake.com/en/user-guide/cortex-code/bundled-skills.md
- CoCo CLI extensibility (skills/hooks/subagents) — https://docs.snowflake.com/en/user-guide/cortex-code/extensibility.md
- CoCo CLI MCP support — https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-mcp.md
- CoCo CLI plugins — https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-plugins.md
- CoCo CLI Agent Client Protocol (ACP) support — https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-acp.md
- (Full section: `cortex-code/llms.txt`, 56 pages.)

### Portability — the "use it outside Snowflake" question (honest read)

- **The Skill *format* is fully portable.** CoCo Skills ARE standard Agent Skills (`SKILL.md`) —
  Snowflake ships a *shared skill layer*: a skill authored for Claude Code works in CoCo and vice
  versa (`Snowflake-Labs/coco-skills`; `npx skills add …` installs across "universal" agents). So a
  CoCo data-analysis skill can be dropped into Claude Code / trousse mechanically.
- **But the *content* is overwhelmingly Snowflake-bound.** The 50+ bundled skills are about Snowflake
  surfaces (Streamlit-on-Snowflake, warehouse tuning, SPCS deploy, Openflow, Dynamic Tables,
  dbt-on-Snowflake, Iceberg-on-Snowflake). Lifted outside Snowflake they reference objects you don't
  have — limited direct value.
- **CoCo itself runs outside a full Snowflake shop** (standalone subscription; plugin for Claude Code
  / ACP / 30+ editors) — but its differentiation *is* Snowflake-awareness; outside Snowflake it's
  just another coding agent.
- **The reusable takeaway** isn't lifting the skills wholesale — it's (a) the *pattern* of how they
  structure data-analysis skills (a reference for trousse's own data skills — consomme/mandoline
  cousins), and (b) that the Agent-Skills standard is becoming portable across agents. If Lantern
  goes Snowflake, CoCo becomes directly relevant as the native agent.
