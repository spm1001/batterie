# BigQuery SQL Reference

BigQuery-specific functions, syntax, and performance tips. All examples use GoogleSQL (BigQuery's standard SQL dialect).

## Date and Time Functions

```sql
-- Current date/time
CURRENT_DATE(), CURRENT_TIMESTAMP()

-- Date arithmetic
DATE_ADD(date_column, INTERVAL 7 DAY)
DATE_SUB(date_column, INTERVAL 1 MONTH)
DATE_DIFF(end_date, start_date, DAY)
TIMESTAMP_DIFF(end_ts, start_ts, HOUR)

-- Truncate to period
DATE_TRUNC(created_at, MONTH)
TIMESTAMP_TRUNC(created_at, HOUR)

-- Extract parts
EXTRACT(YEAR FROM created_at)
EXTRACT(DAYOFWEEK FROM created_at)  -- 1=Sunday

-- Format
FORMAT_DATE('%Y-%m-%d', date_column)
FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', ts_column)
```

## String Functions

```sql
-- Case-insensitive matching (no ILIKE in BigQuery)
LOWER(column) LIKE '%pattern%'

-- Regex
REGEXP_CONTAINS(column, r'pattern')
REGEXP_EXTRACT(column, r'pattern')

-- Splitting and joining
SPLIT(str, delimiter)              -- returns ARRAY
ARRAY_TO_STRING(array, delimiter)  -- joins ARRAY back to STRING
```

## Arrays and Structs

```sql
-- Array operations
ARRAY_AGG(column)                  -- aggregate into array
UNNEST(array_column)               -- expand array to rows
ARRAY_LENGTH(array_column)         -- count elements
value IN UNNEST(array_column)      -- membership test

-- Struct access
struct_column.field_name
```

## Performance Tips

| Tip | Why |
|-----|-----|
| **Filter on partition columns** | Reduces bytes scanned (= cost). Usually a date column. |
| **Use clustering columns in WHERE/ORDER BY** | Speeds up queries within partitions. |
| **Use `APPROX_COUNT_DISTINCT()`** | Much faster than `COUNT(DISTINCT)` on large tables. Accurate within ~1%. |
| **Avoid `SELECT *`** | BigQuery bills per byte scanned. Select only needed columns. |
| **Use `DECLARE` and `SET`** | Parameterize scripts to avoid repetition and enable reuse. |
| **Dry run before executing** | Preview query cost before running expensive queries. |

## Common SQL Patterns

### Window Functions

```sql
-- Ranking
ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC)
RANK() OVER (PARTITION BY category ORDER BY revenue DESC)
DENSE_RANK() OVER (ORDER BY score DESC)

-- Running totals and moving averages
SUM(revenue) OVER (
    ORDER BY date_col
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) AS running_total

AVG(revenue) OVER (
    ORDER BY date_col
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
) AS moving_avg_7d

-- Previous/next values
LAG(value, 1) OVER (PARTITION BY entity ORDER BY date_col) AS prev_value
LEAD(value, 1) OVER (PARTITION BY entity ORDER BY date_col) AS next_value

-- First/last in window
FIRST_VALUE(status) OVER (
    PARTITION BY user_id ORDER BY created_at
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
)
LAST_VALUE(status) OVER (
    PARTITION BY user_id ORDER BY created_at
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
)

-- Percent of total
revenue / SUM(revenue) OVER () AS pct_of_total
revenue / SUM(revenue) OVER (PARTITION BY category) AS pct_of_category
```

### CTEs for Readability

Structure complex queries as a chain of named steps:

```sql
WITH
-- Step 1: Define the base population
base_users AS (
    SELECT user_id, created_at, plan_type
    FROM users
    WHERE created_at >= '2024-01-01'
      AND status = 'active'
),

-- Step 2: Calculate user-level metrics
user_metrics AS (
    SELECT
        u.user_id,
        u.plan_type,
        COUNT(DISTINCT e.session_id) AS session_count,
        SUM(e.revenue) AS total_revenue
    FROM base_users u
    LEFT JOIN events e ON u.user_id = e.user_id
    GROUP BY u.user_id, u.plan_type
),

-- Step 3: Aggregate to summary
summary AS (
    SELECT
        plan_type,
        COUNT(*) AS user_count,
        AVG(session_count) AS avg_sessions,
        SUM(total_revenue) AS total_revenue
    FROM user_metrics
    GROUP BY plan_type
)

SELECT * FROM summary ORDER BY total_revenue DESC;
```

### Cohort Retention

```sql
WITH cohorts AS (
    SELECT
        user_id,
        DATE_TRUNC(first_activity_date, MONTH) AS cohort_month
    FROM users
),
activity AS (
    SELECT
        user_id,
        DATE_TRUNC(activity_date, MONTH) AS activity_month
    FROM user_activity
)
SELECT
    c.cohort_month,
    COUNT(DISTINCT c.user_id) AS cohort_size,
    COUNT(DISTINCT CASE
        WHEN a.activity_month = c.cohort_month THEN a.user_id
    END) AS month_0,
    COUNT(DISTINCT CASE
        WHEN a.activity_month = DATE_ADD(c.cohort_month, INTERVAL 1 MONTH) THEN a.user_id
    END) AS month_1,
    COUNT(DISTINCT CASE
        WHEN a.activity_month = DATE_ADD(c.cohort_month, INTERVAL 3 MONTH) THEN a.user_id
    END) AS month_3
FROM cohorts c
LEFT JOIN activity a ON c.user_id = a.user_id
GROUP BY c.cohort_month
ORDER BY c.cohort_month
```

### Funnel Analysis

```sql
WITH funnel AS (
    SELECT
        user_id,
        MAX(CASE WHEN event = 'page_view' THEN 1 ELSE 0 END) AS step_1_view,
        MAX(CASE WHEN event = 'signup_start' THEN 1 ELSE 0 END) AS step_2_start,
        MAX(CASE WHEN event = 'signup_complete' THEN 1 ELSE 0 END) AS step_3_complete,
        MAX(CASE WHEN event = 'first_purchase' THEN 1 ELSE 0 END) AS step_4_purchase
    FROM events
    WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY user_id
)
SELECT
    COUNT(*) AS total_users,
    SUM(step_1_view) AS viewed,
    SUM(step_2_start) AS started_signup,
    SUM(step_3_complete) AS completed_signup,
    SUM(step_4_purchase) AS purchased,
    ROUND(100.0 * SUM(step_2_start) / NULLIF(SUM(step_1_view), 0), 1) AS view_to_start_pct,
    ROUND(100.0 * SUM(step_3_complete) / NULLIF(SUM(step_2_start), 0), 1) AS start_to_complete_pct,
    ROUND(100.0 * SUM(step_4_purchase) / NULLIF(SUM(step_3_complete), 0), 1) AS complete_to_purchase_pct
FROM funnel
```

### Deduplication

```sql
-- Keep the most recent record per key
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY updated_at DESC
        ) AS rn
    FROM source_table
)
SELECT * FROM ranked WHERE rn = 1
```

### External Tables (Google Sheets → BigQuery)

Link a Google Sheet as a queryable BQ table. Data stays in the Sheet — BQ reads it live on every query.

```sql
-- Create external table from a Google Sheet
CREATE EXTERNAL TABLE `project.dataset.table_name`
OPTIONS (
    format = 'GOOGLE_SHEETS',
    uris = ['https://docs.google.com/spreadsheets/d/SHEET_ID'],
    skip_leading_rows = 1
);

-- Target a specific tab by name
CREATE EXTERNAL TABLE `project.dataset.table_name`
OPTIONS (
    format = 'GOOGLE_SHEETS',
    uris = ['https://docs.google.com/spreadsheets/d/SHEET_ID'],
    sheet_range = 'Sheet2!A:Z',
    skip_leading_rows = 1
);
```

**Permissions (double-lock):** Users need both BQ access (`roles/bigquery.dataViewer` + `roles/bigquery.user` on the project) AND the Google Sheet shared with their Google account. Missing either lock = query fails.

**Gotchas:**
- BQ auto-detects column types from Sheet data — messy columns become STRING
- Schema changes in the Sheet (adding/removing columns) can break queries
- Performance is slower than native BQ tables — fine for small datasets, avoid for >100K rows
- Use `CREATE OR REPLACE EXTERNAL TABLE` to update the link without dropping first
