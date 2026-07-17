# Discovery — Snowflake docs section map

Skip the top-level `curl` — the section → sub-index map, pinned **2026-07-17** from
`https://docs.snowflake.com/llms.txt`. To find a page not in the curated Lantern index:

```bash
curl -s <sub-index URL> | grep -i 'your topic'   # → the page's .md URL
```

Then fetch the page: `curl -s <page.md>`.

| Section | Pages | Sub-index (`llms.txt`) |
|---|---:|---|
| General (overview pages, direct in top index) | — | `https://docs.snowflake.com/llms.txt` (§ General) |
| Loading & Unloading Data | 684 | `https://docs.snowflake.com/en/user-guide/data-integration/llms.txt` |
| Snowflake Cortex (AI & ML) | 103 | `https://docs.snowflake.com/en/user-guide/snowflake-cortex/llms.txt` |
| Cortex Code | 56 | `https://docs.snowflake.com/en/user-guide/cortex-code/llms.txt` |
| Clean Rooms | 113 | `https://docs.snowflake.com/en/user-guide/cleanrooms/llms.txt` |
| Snowsight UI | 47 | `https://docs.snowflake.com/en/user-guide/ui-snowsight/llms.txt` |
| Snowflake Postgres | 26 | `https://docs.snowflake.com/en/user-guide/snowflake-postgres/llms.txt` |
| **User Guide** (Iceberg, sharing, cost, security, warehouses) | 890 | `https://docs.snowflake.com/en/user-guide/llms.txt` |
| Snowflake CLI | 245 | `https://docs.snowflake.com/en/developer-guide/snowflake-cli/llms.txt` |
| Native Apps Framework | 143 | `https://docs.snowflake.com/en/developer-guide/native-apps/llms.txt` |
| Snowpark | 67 | `https://docs.snowflake.com/en/developer-guide/snowpark/llms.txt` |
| Snowflake ML | 90 | `https://docs.snowflake.com/en/developer-guide/snowflake-ml/llms.txt` |
| Streamlit in Snowflake | 34 | `https://docs.snowflake.com/en/developer-guide/streamlit/llms.txt` |
| Snowpark Container Services | 34 | `https://docs.snowflake.com/en/developer-guide/snowpark-container-services/llms.txt` |
| Snowflake REST API | 52 | `https://docs.snowflake.com/en/developer-guide/snowflake-rest-api/llms.txt` |
| Developer Guide | 318 | `https://docs.snowflake.com/en/developer-guide/llms.txt` |
| SQL Functions | 999 | `https://docs.snowflake.com/en/sql-reference/functions/llms.txt` |
| **SQL Commands** (CREATE ICEBERG TABLE, EXTERNAL VOLUME, SHARE) | 683 | `https://docs.snowflake.com/en/sql-reference/sql/llms.txt` |
| Account Usage | 175 | `https://docs.snowflake.com/en/sql-reference/account-usage/llms.txt` |
| Organization Usage | 95 | `https://docs.snowflake.com/en/sql-reference/organization-usage/llms.txt` |
| Information Schema | 60 | `https://docs.snowflake.com/en/sql-reference/info-schema/llms.txt` |
| SQL Classes | 118 | `https://docs.snowflake.com/en/sql-reference/classes/llms.txt` |
| SQL General Reference | 242 | `https://docs.snowflake.com/en/sql-reference/llms.txt` |
| Connectors & Drivers | 107 | `https://docs.snowflake.com/en/connectors/llms.txt` |
| **Collaboration & Marketplace** (listings, auto-fulfilment, egress) | 73 | `https://docs.snowflake.com/en/collaboration/llms.txt` |
| Migrations | 962 | `https://docs.snowflake.com/en/migrations/llms.txt` |
| Programmatic Access | 3 | `https://docs.snowflake.com/en/progaccess/llms.txt` |
| Release Notes | 1687 | `https://docs.snowflake.com/en/release-notes/llms.txt` |

**Any doc page → Markdown:** append `.md` to its URL. E.g. the HTML page
`.../user-guide/tables-iceberg` → `.../user-guide/tables-iceberg.md`.

If a section is missing here, re-fetch the top-level `llms.txt` (it gains sections over time).
