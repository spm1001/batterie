---
description: "Explore a BigQuery project or dataset — list tables, catalog search"
argument-hint: "[query or context]"
---

Explore: $ARGUMENTS

Follow the consomme Discover stage:
- Dataset specified → list_table_ids + get_dataset_info
- Project only → list_dataset_ids, drill into relevant datasets
- Conceptual description → search_catalog with natural language

For each interesting table, get a quick summary via get_table_info. Present as a structured inventory with row counts and brief schema summaries.
