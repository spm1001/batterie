---
description: "Profile a BigQuery table — schema, shape detection, quality assessment"
argument-hint: "[query or context]"
---

Profile this BigQuery table: $ARGUMENTS

Follow the consomme methodology:

1. DISCOVER: get_table_info for schema, get_dataset_info for context
2. SHAPE DETECTION: Classify as warehouse/survey/time-series based on column patterns. State your classification and proceed.
3. UNDERSTAND: Run profiling queries from the matching reference — row count, null rates, cardinality, distributions, sample values
4. QUALITY: Flag issues — high null rates, suspicious cardinality, duplicates, type mismatches
5. SUMMARY: Table overview, shape classification, column-by-column summary, quality flags, suggested next steps
