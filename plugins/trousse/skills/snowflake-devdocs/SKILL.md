---
name: snowflake-devdocs
description: >
  Snowflake developer docs, fetched live — retrieves current pages as clean Markdown from
  docs.snowflake.com (no API key, no scraping; the official .md and llms.txt endpoints via
  curl). Provides a curated index across the Lantern exposure-lake decision surfaces (Iceberg
  tables, external volumes, Open Catalog/Polaris, Secure Data Sharing, cross-cloud egress cost,
  dynamic masking, clean rooms) and a discover→fetch→cite workflow that validates every pinned
  URL and ensures fetched docs beat stale training memory. Load this BEFORE answering any
  Snowflake question from memory, FIRST — Snowflake warns their Iceberg, Cortex, and pricing
  syntax drifts fast. Triggers on 'Snowflake docs', 'Iceberg on Snowflake', 'Snowflake data
  sharing', 'Snowflake cost', 'Open Catalog', 'Cortex Analyst'. (user)
allowed-tools: [Bash]
---

# Snowflake Developer Docs

Retrieve official Snowflake documentation as **Markdown**, straight from `docs.snowflake.com`.
No API key, no MCP server, no HTML scraping — every doc page is published as clean Markdown by
appending `.md` to its URL, and an `llms.txt` hierarchy indexes the whole corpus. Just `curl`.

Snowflake made their docs LLM-native on 15 April 2026, and wrote **notes for LLMs** into the
index that apply directly here:

> - Snowflake SQL syntax evolves frequently. **Always prefer fetched docs over syntax memorised
>   from training data**, especially for **Cortex AI functions, Dynamic Tables, and Iceberg Tables**.
> - Use the `<orgname>-<accountname>` identifier format in new code (the legacy
>   `<account>.snowflakecomputing.com` still works but is outdated).
> - Snowpark Python API method signatures change between versions — verify against the versioned
>   API reference.

**The whole point of this skill: on anything Snowflake, fetch before you assert.**

## When to use

- Any Snowflake architecture, SQL, pricing, or capability question — training memory is stale by default.
- Prepping or checking a claim for the **Lantern exposure-lake** work (see `references/lantern-index.md`).
- Troubleshooting a Snowflake error — fetch the relevant reference page and read it.

## When NOT to use

- Non-Snowflake docs (use web search or `mise fetch`).
- Operating a live Snowflake account (querying data, running Cortex) — that's the official Snowflake
  MCP server (`Snowflake-Labs/mcp`), a separate piece. This skill is docs-and-knowledge only.
- The user already pasted the relevant docs into the conversation.

## Workflow

### 1. Curated index first (the Lantern slice)

For exposure-lake questions, the authoritative page is almost certainly already pinned in
**`references/lantern-index.md`** — grouped by decision surface (storage / catalog / sharing /
cost & egress / governance / clean rooms / marketplace / Cortex), each with its verified `.md` URL
and a one-line "why this matters for Lantern". Start there, then fetch the page (step 3).

`references/lantern-frame.md` carries the durable architectural spine so you read whatever you
fetch through the right lens — load it alongside the index for any Lantern reasoning.

### 2. Discovery — when the page isn't in the curated index

The docs are a hierarchy of index files. Navigate top-down:

```bash
# Top-level index → lists every section + its own sub-index (with page counts)
curl -s https://docs.snowflake.com/llms.txt

# A section sub-index → lists every page in that section as a .md URL
curl -s https://docs.snowflake.com/en/user-guide/llms.txt | grep -i 'YOUR TOPIC'
```

`references/discovery.md` has the section → sub-index map pre-pinned (skip the first curl).
Grep the sub-index for your topic to get the exact page URL.

### 3. Retrieve — fetch the page as Markdown

```bash
curl -s https://docs.snowflake.com/en/user-guide/tables-iceberg.md
```

Read it, cite it. Pipe long pages to a file and read the section you need rather than dumping the
whole thing into context.

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Answering a Snowflake question from memory | Iceberg/Cortex/pricing syntax drifts; you'll be confidently wrong | Fetch first — Snowflake says so themselves |
| Scraping the HTML page | Fragile, huge, nav/script noise | Append `.md` to any doc URL |
| Fetching 15 pages "to be safe" | Context overload | Use the curated index / grep the sub-index; fetch the 1–3 that answer it |
| Guessing a `.md` slug | 404s, or worse a plausible-wrong page | Get the slug from a live sub-index, don't invent it |
| Trusting a pinned URL forever | Snowflake reorganises; slugs move | If a pinned URL 404s, re-discover via step 2 and update the index |

## Freshness

The pinned URLs in `references/` were verified live on **2026-07-17**. The docs themselves are
always current — that's the point. If a pinned slug 404s, re-fetch the section sub-index (step 2),
find the moved page, and fix the index entry. Don't fall back to training memory.

## Integration

- **With the Lantern notes:** `references/lantern-frame.md` points to the canonical synthesis in
  `~/notes/work/scaled-measurement/lantern/` (`understanding.md`, the two `snowflake-*`/`*-portability`
  notes) — that's the living source of truth; the frame here is a durable summary, not a fork of it.
- **With web search:** fall back to web search for Snowflake *pricing negotiation reality*, blog
  posts, or anything outside the official docs corpus.
- **With mise:** use mise for Google Workspace content, this skill for Snowflake docs.
