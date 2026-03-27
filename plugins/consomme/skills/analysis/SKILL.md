---
name: consomme
description: BigQuery data analysis — BEFORE writing any BQ query, load this for methodology and dialect reference. Provides 5-stage workflow (discover → understand → analyse → validate → present) mapped to MCP tools (execute_sql, forecast, analyze_contribution, catalog search). Triggers on 'analyse this data', 'explore the dataset', 'what tables do we have', 'build a dashboard', 'query BigQuery', 'why did this metric change'. (user)
allowed-tools: [Bash, Read, Write, "mcp__*"]
---

<!-- Sources: Google BQ Data Analytics extension (Apache-2.0), Anthropic knowledge-work-plugins (Apache-2.0) -->

# BigQuery Data Analyst

Systematic methodology for exploring, querying, validating, and visualizing BigQuery data using MCP tools.

## When to Use

- Analysing data in BigQuery — exploring datasets, writing queries, building dashboards
- User asks about data, metrics, trends, or patterns and the data lives in BigQuery
- Building interactive HTML dashboards from query results
- Validating an analysis before sharing with stakeholders

## Small Datasets Without BigQuery

For Google Sheets under ~5K rows, use `/consomme-sheets <url>` to analyse directly in-context — no BigQuery access needed. The same profiling methodology applies (shape detection, quality assessment, distributions) but execution happens over the CSV data rather than via SQL. Requires the mise MCP server for Sheet fetching.

## When NOT to Use

- User is writing application code that happens to query BQ (they need a client library, not an analysis skill)
- Pure infrastructure tasks (creating datasets, managing IAM) — use GCP console or CLI directly

## 1. Workflow Overview

Every analysis follows five stages. Use the MCP tools mapped to each stage:

```
DISCOVER → UNDERSTAND → ANALYZE → VALIDATE → PRESENT
```

| Stage | Purpose | MCP Tools |
|-------|---------|-----------|
| **Discover** | Find relevant tables and datasets | `search_catalog`, `list_dataset_ids`, `list_table_ids` |
| **Understand** | Learn schema, shape, and quality | `get_dataset_info`, `get_table_info`, `execute_sql` |
| **Analyze** | Query, aggregate, model, test significance | `execute_sql`, `forecast`, `analyze_contribution` |
| **Validate** | Check results before sharing | `execute_sql` (cross-checks, spot-checks) |
| **Present** | Visualize and communicate | Results from above stages → charts, dashboards, tables |

**Start at Discover** unless the user names specific tables. Never skip Understand — always profile before analyzing.

When comparing groups or segments in the Analyze stage, check whether observed differences are statistically meaningful — see `references/statistical-analysis.md` for confidence intervals, significance tests, and minimum sample sizes. This is especially important for survey data where sample sizes per segment may be small.

## 2. Tool Reference

### Discovery Tools

**`search_catalog`** — Semantic search across tables, views, models, routines, and connections. The `prompt` parameter is a natural language description, not just keywords — "tables about advertiser campaign performance" works better than "advertiser campaign". Use first when the user describes data conceptually rather than naming specific tables.

**`list_dataset_ids`** — List all datasets in the project. Use to orient when entering an unfamiliar project.

**`list_table_ids`** — List all tables in a specific dataset. Use after identifying a relevant dataset to see what's available.

### Schema Tools

**`get_dataset_info`** — Get dataset-level metadata (description, labels, location, default expiration). Use to understand dataset purpose and organization.

**`get_table_info`** — Get table metadata including schema (column names and types), partitioning configuration, clustering fields, and row count. Use before writing any query against a table.

### `execute_sql` — The Workhorse

Execute SQL statements against BigQuery. Used for profiling, analysis, and validation.

**Cost awareness:** BigQuery bills per byte scanned. Before running expensive queries on large tables:
- Use `dry_run: true` to preview query cost without executing
- Always filter on partition columns
- Avoid `SELECT *` — select only the columns you need
- Use `APPROX_COUNT_DISTINCT()` instead of `COUNT(DISTINCT)` on large tables

**Result set management:** Results come back as one JSON object per row. To avoid overwhelming the context:
- Always use `LIMIT` for exploratory queries (LIMIT 20–50)
- Aggregate before selecting — `GROUP BY` to reduce rows, not `LIMIT` on raw data
- For large tables, profile with aggregation queries, don't dump rows
- If you need to see sample rows, use `LIMIT 10` explicitly

### `forecast` — Time Series Forecasting

Forecast future values based on historical patterns.

**Required parameters:**
- `history_data` — a SQL query (not just a table name) returning the time series
- `timestamp_col` — name of the date/timestamp column in the query results
- `data_col` — name of the numeric metric column to forecast
- `horizon` — number of future periods to predict (default: 10)

**Optional:** `id_cols` — array of column names for parallel series (e.g., forecast per region)

**Prerequisites — check before using:**
- Data must have a genuine time dimension (not synthetic or static)
- Series should have at least 2× the horizon in historical data points
- Pre-aggregate to one row per time period before passing to forecast
- Exclude the current incomplete period

**Example: forecast daily revenue for the next 30 days**

```
history_data: "SELECT event_date, SUM(revenue) AS daily_revenue
              FROM sales WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
              AND event_date < CURRENT_DATE()
              GROUP BY event_date ORDER BY event_date"
timestamp_col: "event_date"
data_col: "daily_revenue"
horizon: 30
```

See `references/profiling-timeseries.md` for preparing data for forecasting.

### `analyze_contribution` — What's Driving the Change?

Analyze which dimensions contribute most to a change in a key metric between two groups.

**When to use:** User asks "why did X change?", "what's driving the increase?", or "how do these groups differ?"

**Required parameters:**
- `input_data` — a SQL query returning both populations, with columns for dimensions, the metric, and a boolean test/control column
- `contribution_metric` — an expression in one of these forms:
  - `SUM(metric_column)` for summable metrics
  - `SUM(numerator)/SUM(denominator)` for ratio metrics
  - `SUM(metric)/COUNT(DISTINCT category)` for per-category metrics
- `is_test_col` — name of the boolean column that splits test vs control

**Optional:** `dimension_id_cols` — array of dimension columns to analyze as drivers

**Example: why is satisfaction lower in Region A vs Region B?**

```
input_data: "SELECT region, age_group, product_line, satisfaction_score,
             region = 'A' AS is_test
             FROM survey_results
             WHERE region IN ('A', 'B')"
contribution_metric: "SUM(satisfaction_score)"
is_test_col: "is_test"
dimension_id_cols: ["age_group", "product_line"]
```

The tool returns ranked contributors — dimensions (or combinations) that explain the difference, with magnitude and support metrics.

**Survey data note:** For binary 0/1 response columns (e.g., brand awareness), use `SUM(column)` as the metric — this gives the count of positive responses, which the tool can decompose by dimension. Cast dimension columns to STRING for clean output.

### Setup Requirements

- **Gemini CLI**: Authentication is automatic via `gemini auth login`. Set `BIGQUERY_PROJECT` environment variable to your GCP project ID.
- **Claude Code / Amp**: Requires a BigQuery MCP server (e.g., `bq-toolbox`) configured with Application Default Credentials or service account credentials. The project is set in the MCP server configuration.
- **Permissions**: `roles/bigquery.user` for read access. Additionally `roles/bigquery.dataEditor` for creating tables/views.

## 3. Data Shape Detection

Before profiling, identify the data shape to pick the right methodology. Look at table count, column count, and naming patterns — then confirm with the user.

| Signal | Likely Shape | Profiling Reference |
|--------|-------------|-------------------|
| Multiple tables, ID columns, FK relationships | **Warehouse** — normalised star/snowflake schema | `references/profiling-warehouse.md` |
| Single wide table, many columns, column names are questions or codes | **Survey** — questionnaire responses from Sheets | `references/profiling-survey.md` |
| Date/timestamp column drives the analysis, questions about trends or forecasts | **Time series** — events or periodic metrics | `references/profiling-timeseries.md` |

**Ask the user:** "This looks like [survey/warehouse/time series] data — is that right?" Don't assume.

**Mixed shapes are common.** A warehouse might have a survey responses fact table, or time series data in a star schema. Use the reference that matches the analytical question, not just the table structure.

## 4. SQL Reference and Patterns

BigQuery-specific functions (date/time, string, arrays/structs), performance tips, and common analytical patterns (window functions, CTEs, cohort retention, funnels, deduplication) are in `references/sql-reference.md`.

Read that reference when writing or reviewing any SQL query. Key points to always remember:

- **No `ILIKE`** in BigQuery — use `LOWER(col) LIKE '%pattern%'`
- **`DATE_TRUNC(col, MONTH)`** not `DATE_TRUNC('month', col)` — the period is an identifier, not a string
- **`APPROX_COUNT_DISTINCT()`** for large-scale cardinality — much cheaper than `COUNT(DISTINCT)`
- **Always filter on partition columns** — BigQuery bills per byte scanned
- **Avoid `SELECT *`** — select only the columns you need

## 5. Validation Framework

Run through these checks before sharing any analysis.

### Pre-Delivery QA Checklist

**Data quality:**
- [ ] Source tables verified — are they the right ones for this question?
- [ ] Data is fresh enough — noted the "as of" date
- [ ] No unexpected gaps in time series or missing segments
- [ ] Null rates checked in key columns — nulls handled appropriately
- [ ] No double-counting from bad joins or duplicate source records
- [ ] All WHERE clauses and filters are correct — no unintended exclusions

**Calculation checks:**
- [ ] GROUP BY includes all non-aggregated columns
- [ ] Rate/percentage denominators are correct and non-zero
- [ ] Date comparisons use same period length — partial periods excluded or noted
- [ ] JOIN types are appropriate — many-to-many joins haven't inflated counts
- [ ] Metric definitions match how stakeholders define them

**Reasonableness:**
- [ ] Numbers are in a plausible range (revenue not negative, percentages 0–100%)
- [ ] No unexplained jumps or drops in time series
- [ ] Key numbers match other known sources (dashboards, prior reports, finance data)
- [ ] Edge cases considered (empty segments, zero-activity periods, new entities)

**Presentation:**
- [ ] Bar charts start at zero, axes labelled, scales consistent
- [ ] Appropriate precision and formatting (currency, percentages, thousands separators)
- [ ] Titles state the insight, not just the metric — date ranges specified
- [ ] Known limitations and assumptions stated explicitly

### Common Pitfalls

**Join explosion** — A many-to-many join silently multiplies rows, inflating counts and sums. Always check row counts after joins. Use `COUNT(DISTINCT a.id)` instead of `COUNT(*)` when counting entities through joins.

**Survivorship bias** — Analyzing only entities that exist today ignores those that were deleted, churned, or failed. Always ask: "who is NOT in this dataset?"

**Incomplete period comparison** — Comparing a partial month to a full month. Always filter to complete periods, or compare same-number-of-days.

**Denominator shifting** — The denominator changes between periods (e.g., "eligible" users redefined), making rates incomparable. Use consistent definitions across all compared periods.

**Average of averages** — Averaging pre-computed averages gives wrong results when group sizes differ. Always aggregate from raw data.

**Timezone mismatches** — Different sources use different timezones, causing misalignment. Standardize to a single timezone (UTC recommended) before analysis.

**Selection bias in segmentation** — Defining segments by the outcome being measured creates circular logic ("power users generate more revenue" — they became power users BY generating revenue). Define segments based on pre-treatment characteristics, not outcomes.

### Result Sanity Checking

**Magnitude checks:**

| Metric Type | Sanity Check |
|-------------|-------------|
| User counts | Match known MAU/DAU figures? |
| Revenue | Right order of magnitude vs. known ARR? |
| Conversion rates | Between 0% and 100%? Match dashboard figures? |
| Growth rates | Is 50%+ MoM realistic, or a data issue? |
| Averages | Reasonable given the distribution? |
| Percentages | Segment percentages sum to ~100%? |

**Cross-validation techniques:**
1. Calculate the same metric two different ways — verify they match
2. Spot-check individual records — pick a few entities and trace manually
3. Compare to known benchmarks — dashboards, finance reports, prior analyses
4. Reverse engineer — if total revenue is X, does per-user × user count ≈ X?
5. Boundary checks — filter to a single day, user, or category — are micro-results sensible?

**Statistical validity:**
- Segment comparisons have adequate sample sizes (n ≥ 30 per group)
- Differences are tested for significance, not just eyeballed
- Multiple comparisons are accounted for (Bonferroni correction if testing many segments)
- See `references/statistical-analysis.md` for methods

**Red flags that warrant investigation:**
- Any metric changing >50% period-over-period without obvious cause
- Counts or sums that are exact round numbers
- Rates exactly at 0% or 100%
- Results that perfectly confirm the hypothesis
- Identical values across time periods or segments

### Documentation Template

Every non-trivial analysis should record:

```
## Analysis: [Title]
Question: [What's being answered]
Sources: [Tables used, as-of dates]
Definitions: [How key metrics are calculated]
Methodology: [Steps taken]
Assumptions: [What's assumed and why]
Limitations: [Known gaps and their impact]
Key Findings: [Results with supporting evidence]
```

## 6. Visualization

### Chart Selection Guide

| What You're Showing | Best Chart | Alternatives |
|---------------------|-----------|--------------|
| Trend over time | Line chart | Area chart (cumulative/composition) |
| Comparison across categories | Vertical bar | Horizontal bar (many categories) |
| Ranking | Horizontal bar | Dot plot, slope chart (two periods) |
| Part-to-whole composition | Stacked bar | Treemap (hierarchical) |
| Composition over time | Stacked area | 100% stacked bar (proportion focus) |
| Distribution | Histogram | Box plot (comparing groups) |
| Correlation (2 variables) | Scatter plot | Bubble chart (add 3rd variable as size) |
| Correlation (many variables) | Heatmap | Pair plot |
| Flow / process | Sankey diagram | Funnel chart (sequential stages) |
| Performance vs. target | Bullet chart | Gauge (single KPI only) |
| Multiple KPIs at once | Small multiples | Dashboard with separate charts |

**When NOT to use:**
- **Pie charts**: Avoid unless <6 categories. Humans compare angles poorly — use bar charts instead.
- **3D charts**: Never. They distort perception and add no information.
- **Dual-axis charts**: Use cautiously — they can imply false correlation. Label both axes clearly.
- **Stacked bar (many categories)**: Hard to compare middle segments. Use small multiples or grouped bars.

### Choosing a Presentation Target

| Target | Best For | Agent Can Build? |
|--------|----------|-----------------|
| **Chart.js HTML** | Quick analysis, one-off exploration, email attachment | ✅ Yes — fully autonomous |
| **Google Sheets + BQ connector** | Non-technical users, ad-hoc filtering/pivoting, familiar interface | ⚡ Partially — agent creates the BQ view, user connects it in Sheets |
| **Looker Studio** | Production dashboards, auto-refreshing, team-wide sharing | ❌ No API — agent prepares the data layer, user builds in GUI |

**Start with Chart.js HTML** for exploratory analysis and quick answers. **Graduate to Sheets or Looker Studio** when the analysis needs to be refreshed, shared with a team, or maintained over time.

### Chart.js HTML Dashboards

For self-contained interactive dashboards the agent builds directly, see `references/dashboard-patterns.md`. Covers Chart.js CDN setup, KPI cards, line/bar/doughnut charts, filters, sortable tables, CSS design system, and performance guidelines by data size.

### Google Sheets with BigQuery Connector

The most accessible output for non-technical team members. Two patterns:

**Connected Sheets (recommended):** Sheets connects directly to BQ — data stays in BigQuery, Sheets is just the interface. Users can pivot, chart, and filter BQ data in a familiar environment without writing SQL.

Agent's role — prepare the data layer:
1. Create a BQ view that pre-joins, filters, and aggregates the data into a simple flat shape
2. Add column descriptions (Sheets picks these up as headers)
3. Name columns clearly — "Total Revenue" not "sum_rev_amt"
4. Keep the view under 10 columns where possible — wide views are overwhelming in Sheets
5. Tell the user: "Connect this view in Sheets: Data → Data connectors → BigQuery → select `project.dataset.view_name`"

**Scheduled query → table → Sheets extract:** For data that needs to be refreshed on a schedule. Agent creates:
1. A BQ scheduled query that materialises results to a destination table
2. A Sheets-friendly table shape (flat, clear column names, reasonable row count)
3. User connects via BQ connector or sets up a Sheets data import

### Looker Studio

For production dashboards that auto-refresh and are shared across a team. The agent cannot build Looker Studio dashboards (no creation API), but can prepare everything needed:

1. **Create BQ views** optimised for Looker Studio — pre-aggregated, well-named, with column descriptions
2. **Partition and cluster** views for query performance (Looker Studio queries BQ on every page view)
3. **Generate a dashboard spec** the user can follow in the Looker Studio UI:
   - Which metrics and dimensions to add
   - Which chart types to use (with rationale from the chart selection guide above)
   - Suggested filters and date range controls
   - KPI card definitions with comparison periods
4. **Keep views simple** — Looker Studio works best with flat, wide views rather than complex joins at query time

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Skip Understand stage | Query wrong table, wrong grain, wrong types | Always `get_table_info` + profile before analysing |
| `SELECT *` on large tables | Expensive scan, context overflow | Select only needed columns, aggregate first |
| No `LIMIT` on exploratory queries | Hundreds of JSON rows flood context | Always `LIMIT 20-50` for exploration |
| Eyeball significance | "Region A is lower" without testing | Use confidence intervals or z-test from `references/statistical-analysis.md` |
| Average of averages | Wrong result when group sizes differ | Aggregate from raw data, not pre-computed averages |
| Assume survey codes | Label `S3=7` as "Scotland" without checking | Ask for the datamap/codebook first — see `references/profiling-survey.md` |
| Ignore straight-liners | Biased Likert scores | Detect and quantify before reporting — >20% is a red flag |
| Compare incomplete periods | Current month vs last full month | Exclude current incomplete period |
| Pie charts for many categories | Unreadable, angles hard to compare | Use horizontal bar charts instead |
| Build Looker Studio directly | No creation API exists | Prepare BQ views + dashboard spec for user to build |
