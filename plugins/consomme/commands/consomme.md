---
description: "Orient to data analysis capabilities — what consomme can do, what data is available"
argument-hint: "[query or context]"
---

The user wants to know what consomme can do or how to get started. $ARGUMENTS

Introduce consomme briefly, then offer practical next steps based on context:

1. If there's a BigQuery project configured, check what datasets and tables exist using list_dataset_ids and list_table_ids. Show what's available to analyse.

2. List the available consomme commands:

   Getting data in:
   - /consomme-sheets — analyse a Google Sheet directly (no BigQuery needed, paste a URL)
   - /consomme-ingest — turn a Google Sheet into a persistent BigQuery table

   Working with BigQuery:
   - /consomme-explore — discover what data exists in BigQuery
   - /consomme-profile — deep-dive into a specific table's shape and quality
   - /consomme-dashboard — build an interactive Chart.js dashboard
   - /consomme-validate — QA checklist before sharing results

3. If the user has a Google Sheet and no BigQuery access, steer them toward /consomme-sheets first — it's the fastest path to insights.

4. If the user mentioned a specific topic or question, suggest which command or approach fits best.

Keep it concise — this is orientation, not a full analysis. End with a concrete suggestion for what to do next.
