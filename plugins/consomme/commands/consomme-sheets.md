---
description: "Analyse a Google Sheet directly — no BigQuery needed. Paste a URL, get insights."
argument-hint: "[query or context]"
---

The user wants to analyse a Google Sheet without BigQuery: $ARGUMENTS

Follow this workflow:

1. FETCH the Sheet data using the mise MCP fetch tool. Call it with the Google Sheet URL. It will deposit clean CSV data to a local file.

2. READ the deposited CSV file to get the data into context.

3. SIZE CHECK: Count the rows and columns.
   - Up to ~3,000 rows: proceed with full in-context analysis
   - 3,000–5,000 rows: proceed but note that exact aggregations may be approximate
   - Over 5,000 rows: stop and suggest /consomme-ingest to load into BigQuery instead — in-context analysis won't be reliable at this scale

4. SHAPE DETECTION: Look at the data and classify it:
   - Survey: columns are question codes, Likert scales, demographic splits
   - Time series: a date/time column drives the analysis, rows are temporal observations
   - Tabular: general structured data (customers, transactions, inventory, etc.)
   State your classification and proceed.

5. PROFILE the data following consomme methodology:
   - Column types (numeric, categorical, date, text, boolean)
   - Missing/blank values per column
   - Unique value counts and cardinality
   - For numeric columns: min, max, mean, notable outliers
   - For categorical columns: value frequency (top 10)
   - For date columns: range, gaps, grain
   - Quality flags: duplicates, inconsistent formats, suspicious values

6. PRESENT findings as a structured summary:
   - Dataset overview (rows, columns, shape classification)
   - Column-by-column profile
   - Quality issues found
   - Key patterns or insights spotted
   - Suggested next steps ("Ask me to build a dashboard, cross-tabulate, or dig into a specific column")

IMPORTANT: You are analysing the data directly in context — do NOT generate SQL or reference BigQuery tools. Work with the CSV data as-is. Your analysis should be approximate but useful — "good enough for a first look" is the goal.

If the mise fetch tool is not available, tell the user: "I need the mise MCP server to fetch Google Sheets. Ask your admin to configure it, or export the Sheet as CSV and share the file path instead."
