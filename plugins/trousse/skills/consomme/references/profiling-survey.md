# Profiling: Survey / Questionnaire Data

For wide, flat tables where each row is a respondent and columns are questions or attributes. Typical source: Google Sheets import, CSV upload, Google Forms export.

## When This Applies

- Single table (or very few tables) in the dataset
- Many columns relative to rows (wide, not tall)
- Column names are question text or abbreviated question codes
- No foreign keys — the table is self-contained
- Data is a snapshot, not a time series

## Common Sheets Import Artefacts

Check for these before profiling — they're almost always present in Sheets-sourced data:

- **Empty trailing rows**: Sheets exports rows beyond the data. Filter with `WHERE column_1 IS NOT NULL`
- **Header row in data**: First data row contains column headers from a second header row
- **Mixed types**: A "numeric" column has stray text ("N/A", "n/a", "-", "refused")
- **Inconsistent casing**: "Yes", "yes", "YES", "y" all meaning the same thing
- **Whitespace**: Leading/trailing spaces in string values. Use `TRIM()`
- **Merged cell artefacts**: Nulls where Sheets had merged cells (value only in first row of merge)
- **Date format chaos**: "01/02/2025" — is that Jan 2 or Feb 1? Check against known dates

**Quick cleanup check:**

```sql
-- Spot non-numeric values in a supposedly numeric column
SELECT DISTINCT response_column
FROM survey_table
WHERE SAFE_CAST(response_column AS FLOAT64) IS NULL
  AND response_column IS NOT NULL
ORDER BY response_column
```

## Datamaps and Codebooks

Survey data almost always arrives with **numeric codes** rather than labels (e.g., `S3=7` instead of `region='Scotland'`). The mapping lives in a **datamap** (also called codebook or data dictionary) — a separate document that defines what each code means.

**Where to find the datamap:**
- Second sheet/tab in the source spreadsheet (very common)
- Separate PDF or Word document from the research agency
- Column descriptions in BigQuery metadata (`get_table_info` may show these)
- Ask the user: "Do you have a datamap or codebook for this survey?"

**How to apply labels in SQL:**

```sql
-- Use CASE to decode numeric codes for readable output
SELECT
  CASE S3
    WHEN 1 THEN 'East England'
    WHEN 2 THEN 'London'
    WHEN 3 THEN 'Midlands'
    -- ...
  END AS region,
  COUNT(*) AS n
FROM survey_table
GROUP BY S3
ORDER BY n DESC
```

**Don't guess codes.** If no datamap is available, profile the distinct values and ask the user to confirm meanings before labelling. Wrong labels are worse than no labels.

## Phase 1: Structural Understanding

**Table-level questions:**
- How many respondents (rows)?
- How many questions (columns)?
- Is there a respondent ID column, or are rows anonymous?
- Is there a timestamp column (when the response was submitted)?
- Are there demographic/segmentation columns (age, region, role)?
- **Is there a datamap?** (see above — check before profiling)

**Column classification for surveys:**

| Type | Description | Examples |
|------|-------------|---------|
| **Respondent ID** | Unique identifier per respondent | respondent_id, email |
| **Demographic** | Segmentation attributes | age_group, region, department |
| **Likert** | Scaled responses (1–5, 1–7, 1–10) | satisfaction, likelihood_to_recommend |
| **Categorical** | Multiple-choice single-select | preferred_channel, role |
| **Multi-select** | Multiple-choice multi-select (often comma-separated) | products_used, channels |
| **Open-text** | Free-form text responses | comments, feedback |
| **Timestamp** | When the response was submitted | submitted_at |
| **Derived/Computed** | Calculated from other columns | nps_category, total_score |

## Phase 2: Column-Level Profiling

**All columns:**
- Null count and null rate (high nulls often mean the question was optional or conditional)
- Distinct count — very low distinct count = categorical; very high = open-text or ID

**Likert / numeric response columns:**
- Distribution as frequency table (how many gave each score)
- Mean, median, mode
- Whether the scale is consistent (all 1–5, or mixed 1–5 and 1–10?)
- Ceiling/floor effects (>50% giving max or min score)
- **Off-scale codes:** Watch for values outside the expected range (e.g., 6 = "prefer not to say" on a 1–5 scale, 99 = "don't know"). Exclude from mean/median calculations — filter with `WHERE score BETWEEN 1 AND 5`

```sql
-- Likert distribution
SELECT
  satisfaction_score,
  COUNT(*) AS n,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM survey_table
WHERE satisfaction_score IS NOT NULL
GROUP BY satisfaction_score
ORDER BY satisfaction_score
```

**Categorical columns:**
- Frequency table with percentages
- Unexpected categories (typos, "Other" variants)
- Whether categories are balanced or skewed

```sql
-- Categorical frequency
SELECT
  preferred_channel,
  COUNT(*) AS n,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM survey_table
GROUP BY preferred_channel
ORDER BY n DESC
```

**Multi-select columns — two common encodings:**

**Comma-separated (single column):**

```sql
-- Explode and count multi-select responses
SELECT
  TRIM(option) AS option,
  COUNT(*) AS n
FROM survey_table,
UNNEST(SPLIT(products_used, ',')) AS option
WHERE products_used IS NOT NULL
GROUP BY option
ORDER BY n DESC
```

**Binary columns (one 0/1 column per option):**

```sql
-- Profile binary-encoded multi-select (e.g., Q1r1, Q1r2, ... Q1r12)
SELECT
  'Q1r1' AS item, SUM(Q1r1) AS selected,
  ROUND(100.0 * SUM(Q1r1) / COUNT(*), 1) AS pct
FROM survey_table
UNION ALL
SELECT 'Q1r2', SUM(Q1r2), ROUND(100.0 * SUM(Q1r2) / COUNT(*), 1)
FROM survey_table
-- ... repeat for each item column
ORDER BY pct DESC
```

**Open-text columns:**
- Response rate (what % actually wrote something?)
- Average length (short answers vs paragraphs)
- Don't try to analyse content in SQL — flag for separate text analysis

**Demographic columns:**
- Distribution of respondents across segments
- Whether segments have enough respondents for meaningful comparison (n > 30 rule of thumb)

## Phase 3: Cross-Tabulation

The key analytical move for survey data. Compare responses across segments:

```sql
-- Cross-tab: satisfaction by region
SELECT
  region,
  COUNT(*) AS n,
  ROUND(AVG(satisfaction_score), 2) AS avg_satisfaction,
  ROUND(APPROX_QUANTILES(satisfaction_score, 100)[OFFSET(50)], 1) AS median_satisfaction,
  COUNTIF(satisfaction_score >= 4) AS promoters,
  ROUND(100.0 * COUNTIF(satisfaction_score >= 4) / COUNT(*), 1) AS pct_promoters
FROM survey_table
WHERE region IS NOT NULL
GROUP BY region
HAVING COUNT(*) >= 30  -- minimum sample size
ORDER BY avg_satisfaction DESC
```

**What to look for:**
- Segments with notably different response patterns
- Segments with low base sizes (flag as unreliable)
- Whether observed differences are meaningful or just noise (large gaps in small samples are suspect)

**When differences look interesting, test significance.** See `references/statistical-analysis.md` for confidence intervals, z-tests for proportions, and chi-squared tests — especially important for survey data where segment sample sizes can be small.

## Quality Assessment

### Survey-Specific Quality Issues

| Issue | How to Detect | Impact |
|-------|--------------|--------|
| **Low response rate** | Many nulls in non-demographic columns | Results may not represent population |
| **Straight-lining** | Same answer for every Likert question per respondent | Inflate scores, reduce variance |
| **Acquiescence bias** | Disproportionate "agree" responses | Scores skew positive |
| **Incomplete responses** | Respondent answered first few questions only | Later questions have higher null rates |
| **Duplicate submissions** | Same respondent ID or identical response patterns | Inflates counts |

**Detect straight-lining:**

```sql
-- Respondents who gave identical scores across all Likert questions
SELECT respondent_id, q1, q2, q3, q4, q5
FROM survey_table
WHERE q1 = q2 AND q2 = q3 AND q3 = q4 AND q4 = q5
```

**Straight-liner thresholds:** <10% is typical, 10–20% warrants a note, >20% is a red flag that may bias aggregate scores. Consider excluding straight-liners from Likert analysis or reporting results both with and without them.

**Detect incomplete responses:**

```sql
-- Completion rate by question position
SELECT
  'q1' AS question, COUNTIF(q1 IS NOT NULL) AS answered,
  ROUND(100.0 * COUNTIF(q1 IS NOT NULL) / COUNT(*), 1) AS pct
FROM survey_table
UNION ALL
SELECT 'q2', COUNTIF(q2 IS NOT NULL), ROUND(100.0 * COUNTIF(q2 IS NOT NULL) / COUNT(*), 1)
FROM survey_table
-- ... repeat for each question
ORDER BY pct DESC
```
