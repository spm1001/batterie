---
description: "Turn a Google Sheet into a queryable BigQuery table — paste a URL, get a table"
argument-hint: "[query or context]"
---

The user wants to make a Google Sheet available as a BigQuery table: $ARGUMENTS

TRIAGE FIRST: If the user just wants to explore a small Sheet (<5K rows) and doesn't need BigQuery specifically, suggest /consomme-sheets instead — it analyses directly with no BQ permissions needed. Only proceed with BQ ingestion if they need persistent querying, joins with other BQ data, or the dataset is large.

Guide them through this step by step:

1. EXTRACT the Sheet ID from the URL. If they pasted a full URL like https://docs.google.com/spreadsheets/d/ABC123/edit#gid=0, the ID is ABC123.

2. ASK only what's missing:
   - Which tab/sheet to use (if not specified, assume the first)
   - What to call the table (suggest a sensible snake_case name from context)
   - Which dataset to put it in (default to a scratchpad or sandbox dataset if one exists)

3. GENERATE and RUN the DDL:
   ```sql
   CREATE OR REPLACE EXTERNAL TABLE `project.dataset.table_name`
   OPTIONS (
       format = 'GOOGLE_SHEETS',
       uris = ['https://docs.google.com/spreadsheets/d/SHEET_ID'],
       skip_leading_rows = 1
   );
   ```
   Add sheet_range if a specific tab was requested.

4. VERIFY by running a quick profile:
   - SELECT * LIMIT 5 to check the data looks right
   - Check column types — flag any that BQ auto-detected as STRING when they look numeric or date-like
   - Count rows to confirm data loaded

5. FLAG permissions: Remind the user that anyone querying this table needs BOTH:
   - BigQuery access (roles/bigquery.dataViewer + roles/bigquery.user)
   - The Google Sheet shared with their Google account
   If colleagues will use this, the Sheet must be shared with them too.

6. SUGGEST next steps: "Your data is ready. Try /consomme-profile project.dataset.table_name to understand the shape and quality."

Keep the tone helpful and non-technical. The user may not know SQL or BQ concepts — explain what you're doing as you go.
