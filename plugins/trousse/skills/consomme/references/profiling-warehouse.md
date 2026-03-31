# Profiling: Warehouse / Multi-Table Data

For normalised or star-schema datasets with multiple related tables, foreign keys, and clear dimensional modelling. Typical sources: existing BigQuery tables, ETL pipelines, data warehouse layers.

## When This Applies

- Multiple tables in the dataset (fact + dimension pattern)
- Column names are tidy field names (snake_case, abbreviated)
- Tables have obvious primary/foreign key relationships
- Data has temporal depth (historical records over time)

## Phase 1: Structural Understanding

Establish the basics before touching the data:

**Table-level questions (answer all before proceeding):**
- How many rows and columns?
- What is the grain — one row per what?
- What is the primary key? Is it unique?
- When was the data last updated?
- How far back does the data go?

**Column classification** — categorize every column as one of:

| Type | Description | Examples |
|------|-------------|---------|
| **Identifier** | Unique keys, foreign keys | user_id, order_id |
| **Dimension** | Categorical attributes for grouping | status, region, category |
| **Metric** | Quantitative values for measurement | revenue, count, duration |
| **Temporal** | Dates and timestamps | created_at, event_date |
| **Text** | Free-form text fields | description, notes |
| **Boolean** | True/false flags | is_active, has_purchased |
| **Structural** | JSON, arrays, nested structures | metadata, tags |

## Phase 2: Column-Level Profiling

Profile every column with `execute_sql`. Compute:

**All columns:**
- Null count and null rate
- Distinct count and cardinality ratio (distinct / total)
- Most common values (top 5–10 with frequencies)
- Least common values (bottom 5 — to spot anomalies)

**Numeric columns (metrics):**
- min, max, mean, median (APPROX_QUANTILES for p50)
- Standard deviation
- Percentiles: p1, p5, p25, p75, p95, p99
- Zero count, negative count (if unexpected)

**String columns (dimensions, text):**
- Min/max/avg length
- Empty string count
- Pattern analysis (do values follow a format?)
- Case consistency (all upper, all lower, mixed?)

**Date/timestamp columns:**
- Min date, max date
- Null dates, future dates (if unexpected)
- Distribution by month/week
- Gaps in time series

**Boolean columns:**
- True count, false count, null count
- True rate

## Phase 3: Relationship Discovery

After profiling individual columns:

- **Foreign key candidates**: ID columns that might link to other tables
- **Hierarchies**: Columns forming natural drill-down paths (country → region → city)
- **Correlations**: Numeric columns that move together (use CORR function)
- **Derived columns**: Columns computed from others
- **Redundant columns**: Columns with identical or near-identical information

**Quick validation query for FK integrity:**

```sql
-- Check for orphan records (FK with no parent)
SELECT COUNT(*) AS orphans
FROM child_table c
LEFT JOIN parent_table p ON c.parent_id = p.id
WHERE p.id IS NULL
```

## Quality Assessment

### Completeness Score

Rate each column:

| Rating | Non-null rate | Action |
|--------|--------------|--------|
| 🟢 Complete | >99% | Good to use |
| 🟡 Mostly complete | 95–99% | Investigate the nulls |
| 🟠 Incomplete | 80–95% | Understand why, assess impact |
| 🔴 Sparse | <80% | May need imputation or exclusion |

### Consistency Checks

Look for:
- **Value format inconsistency**: "USA", "US", "United States", "us"
- **Type inconsistency**: Numbers stored as strings, dates in various formats
- **Referential integrity**: Foreign keys with no matching parent record
- **Business rule violations**: Negative quantities, end dates before start dates, percentages > 100
- **Cross-column consistency**: Status = "completed" but completed_at is null

### Accuracy Indicators

Red flags for accuracy issues:
- **Placeholder values**: 0, -1, 999999, "N/A", "TBD", "test"
- **Default value dominance**: Suspiciously high frequency of a single value
- **Stale data**: updated_at shows no recent changes in an active system
- **Impossible values**: Ages > 150, dates in the far future, negative durations
- **Round number bias**: All values ending in 0 or 5 (suggests estimation)

### Timeliness

- When was the table last updated?
- What is the expected update frequency?
- Is there a lag between event time and load time?
- Are there gaps in the time series?
