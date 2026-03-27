# Profiling: Time Series Data

For datasets where the primary structure is measurements over time. Typical sources: event logs, daily metrics tables, sensor data, financial data.

## When This Applies

- Table has a clear timestamp or date column that drives the analysis
- Rows represent events or periodic measurements
- Questions are about trends, seasonality, anomalies, or forecasts
- The `forecast` tool is likely to be useful

## Phase 1: Structural Understanding

**Table-level questions:**
- What is the time grain? (second, minute, hour, day, week, month)
- What is the time range? (min date to max date)
- Is the series regular (one row per period) or irregular (event-driven)?
- What entities does the series cover? (one global series, or per-user/per-product/per-region?)
- Is this raw events or pre-aggregated metrics?

```sql
-- Time range and grain detection
SELECT
  MIN(event_date) AS earliest,
  MAX(event_date) AS latest,
  COUNT(*) AS total_rows,
  COUNT(DISTINCT event_date) AS distinct_dates,
  ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT event_date), 1) AS avg_rows_per_date
FROM metrics_table
```

## Phase 2: Continuity and Gaps

Time series analysis breaks when there are gaps. Check before analysing:

```sql
-- Find gaps in a daily series
WITH dates AS (
  SELECT DISTINCT event_date FROM metrics_table
),
expected AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY(
    (SELECT MIN(event_date) FROM metrics_table),
    (SELECT MAX(event_date) FROM metrics_table)
  )) AS date
)
SELECT e.date AS missing_date
FROM expected e
LEFT JOIN dates d ON e.date = d.event_date
WHERE d.event_date IS NULL
ORDER BY e.date
```

**What gaps mean:**
- No data collected (system was down, no activity)
- Data pipeline failed (missing loads)
- Weekends/holidays (expected for business metrics)

Decide whether to fill gaps (with zeros, interpolation, or carry-forward) or exclude them.

## Phase 3: Distribution Over Time

```sql
-- Daily volume and metric summary
SELECT
  event_date,
  COUNT(*) AS event_count,
  SUM(metric_value) AS total,
  AVG(metric_value) AS average
FROM metrics_table
GROUP BY event_date
ORDER BY event_date
```

**What to look for:**
- **Trend**: Is the metric going up, down, or flat?
- **Seasonality**: Weekly patterns (weekday vs weekend)? Monthly patterns?
- **Anomalies**: Sudden spikes or drops — are they real events or data issues?
- **Level shifts**: Permanent step-changes (new product launch, policy change)

## Quality Assessment

### Time-Series-Specific Issues

| Issue | How to Detect | Impact |
|-------|--------------|--------|
| **Missing periods** | Gap detection query above | Breaks moving averages, misleads trend lines |
| **Timezone inconsistency** | Events at midnight cluster or shift by hour | Daily aggregations are wrong |
| **Late-arriving data** | Recent dates have lower counts than older dates | Most recent period looks like a drop |
| **Duplicate events** | Same entity + timestamp appears multiple times | Inflates counts and sums |
| **Partial periods** | Current month/week is incomplete | Misleading comparisons to prior full periods |

**Always exclude the current incomplete period when comparing to prior periods.**

## Preparing Data for the `forecast` Tool

The `forecast` tool requires:
- A **timestamp column** (DATE or TIMESTAMP type)
- A **data column** (numeric — the metric to forecast)
- Optionally, **id columns** (for multiple parallel series, e.g., per-region forecasts)

**Pre-aggregation is usually needed.** The tool expects one row per time period (per entity if using id_cols). If your source is raw events, aggregate first:

```sql
-- Prepare daily series for forecasting
SELECT
  event_date AS date,
  region,
  SUM(revenue) AS daily_revenue
FROM events_table
WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
  AND event_date < CURRENT_DATE()  -- exclude incomplete today
GROUP BY event_date, region
ORDER BY event_date
```

Pass this as the `history_data` parameter (the tool accepts SQL queries, not just table names).

**Minimum history:** Aim for at least 2× the forecast horizon in historical data points. Forecasting 30 days ahead? Provide at least 60 days of history. More is better — 1 year captures seasonality.
