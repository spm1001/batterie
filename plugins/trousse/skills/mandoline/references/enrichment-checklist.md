# BQ Table Enrichment Checklist

The full inventory of BigQuery features that make a table self-documenting. Most people use 2-3 of these. Use all of them.

## Table-Level

| Feature | API | What it does | Example |
|---------|-----|-------------|---------|
| **Description** | `table.description` | Paragraph visible in BQ console, Data Catalog, INFORMATION_SCHEMA | Survey methodology: n, fieldwork dates, format, key usage notes, caveats |
| **Friendly name** | `table.friendly_name` | Short display name in BQ console UI | "OHID Mental Health Survey" |
| **Labels** | `table.labels` | Key-value metadata for filtering in Data Catalog and `__TABLES__` | `survey_org: ohid`, `data_shape: user-level`, `respondents: 1320` |
| **Expiration** | `table.expires` | Auto-delete date. Prevents orphan tables | 60-90 days for snapshots, None for production |

## Column-Level

| Feature | API | What it does |
|---------|-----|-------------|
| **Description** | `SchemaField.description` | Per-column text visible in BQ console, INFORMATION_SCHEMA, and LLM schema discovery |
| **Mode** | `SchemaField.mode` | NULLABLE, REQUIRED, REPEATED — communicates data contracts |

## Column Description Philosophy: Display Label First, Then Teach

The difference between a mediocre table and an excellent one is in the column descriptions.

Every description serves **dual duty**: it's both documentation for humans and a label source for charts. The first clause (before the first period) must work as a standalone display label.

### Bad (defines only)
```
gender: "Respondent gender"
pct: "Percentage value"
base_n: "Sample size"
```

### Better (teaches but no display label)
```
gender: "Respondent gender: Male, Female, Other gender identity, Prefer not to say.
         4 values. 'Other' and 'Prefer not to say' have small bases —
         flag n<30 as unreliable when cross-tabulating"
```

### Best (display label + teaches)
```
gender: "Gender. Male, Female, Other gender identity, Prefer not to say.
         4 values. 'Other' and 'Prefer not to say' have small bases —
         flag n<30 as unreliable when cross-tabulating"

pct: "Survey result (%). Pre-calculated weighted percentage as decimal (0.12 = 12%).
      NEVER use SUM() or COUNT() to recalculate — already computed.
      For weighted averages across segments: SAFE_DIVIDE(SUM(pct * base_n), SUM(base_n))."

base_n: "Sample size. Weighted base for this segment. Varies per segment —
         use for statistical reliability. Bases under 100 warrant a small-base caveat."
```

### The Pattern

Every description answers up to three questions, **starting with the display label:**

0. **Display label** — First clause, under ~40 chars, suitable as chart axis or column header
1. **What is it?** — Field definition (everyone does this)
2. **What are the values?** — Enumeration or range (most people skip this)
3. **What do I DO with it?** — Usage guidance, gotchas, relationships to other columns (almost nobody does this)

### Examples by Column Type

#### Respondent-Level Tables

**Identifiers:**
```
"Respondent ID. Unique identifier (UUID). Use COUNT(DISTINCT respondent_id) for sample sizes."
```

**Demographics (STRING):**
```
"Age group. 5 bands: 18-24, 25-34, 35-44, 45-54, 55-64.
 Under-18s and over-65s screened out. Use GROUP BY age_group for age analysis."
```

**Multi-select binary (BOOL) — first in group:**
```
"Physical activity. Q1 multi-select: 'Done physical activity (e.g. gone for a walk)'.
 TRUE = selected. COUNTIF/COUNT(*) for percentage.
 Percentages across action_ columns sum >100% (multiple selections allowed)."
```

**Multi-select binary (BOOL) — subsequent in group:**
```
"Talked to someone. Q1 multi-select: 'Talked to someone I trust'. TRUE = selected."
```

**Likert scale (INT64) — first in group:**
```
"Can imagine taking action. Q2 Likert: 'I can imagine myself taking action to protect my mental health'.
 1=Strongly disagree, 2=Somewhat disagree, 3=Neither, 4=Somewhat agree, 5=Strongly agree.
 6=Prefer not to say — EXCLUDE from means with WHERE col <= 5. Higher = more agreement."
```

**Likert scale (INT64) — subsequent in group:**
```
"Support feels relevant. Q2 Likert: 'Wellbeing support is relevant to me'.
 1-5 agreement scale (higher=more), 6=Prefer not to say (exclude from means)."
```

**Single-select (STRING):**
```
"Brand most likely to consider. Q4: 'Which are you most likely to consider?'
 One value per respondent: NHS Every Mind Matters, Catch It, CALM, Headspace, Change4Life, or None.
 GROUP BY for share of preference."
```

**Weight (FLOAT64):**
```
"Survey weight. Rim-weighted to match UK population on age, gender, region.
 Use with weighted calculations. Unweighted base = COUNT(*); weighted base = SUM(weight)."
```

**Mutually exclusive indicators:**
```
"None of the above. TRUE = took no listed action.
 Mutually exclusive with other action_ columns in practice."
```

#### Pre-Aggregated Tables

**Response label:**
```
"Response option. Answer text for this row (e.g. 'Stressed', 'Somewhat agree').
 Use as chart category axis."
```

**Label order:**
```
"Display sequence. 1-based sort order within the question.
 ORDER BY label_order for charts — never alphabetically. Preserves scale direction."
```

**Percentage:**
```
"Survey result (%). Pre-calculated weighted percentage as decimal (0.35 = 35%).
 NEVER use SUM() or COUNT() — already computed.
 Cross-segment weighted average: SAFE_DIVIDE(SUM(pct * base_n), SUM(base_n))."
```

**Base:**
```
"Sample size. Weighted base for this segment. Varies per segment —
 flag base_n < 100 as potentially unreliable."
```

**Segment:**
```
"Demographic variable. Break variable name (e.g. 'gender', 'age_group', 'region').
 Use WHERE segment = '...' AND segment_value = '...' to filter."
```

**Segment value:**
```
"Demographic group. Specific value within the segment (e.g. 'Male', '18-24', 'London')."
```

**Net flag:**
```
"Summary row flag. TRUE for aggregate rows like 'Net: Agree' (= Strongly Agree + Somewhat Agree).
 Do not sum with constituent rows."
```

**Question code:**
```
"Question identifier. Maps to survey sections (A=mood, B=society, C=media).
 Use for filtering and grouping related questions."
```

**Question text:**
```
"Full question wording. Display in chart titles or analysis headers."
```

**Response type:**
```
"Response format. Values: single_select, multi_select, likert, grid.
 Determines valid aggregation patterns."
```

### First-Column Rule

The first description for each question group should be the richest — it teaches the pattern. Subsequent columns in the same group can be shorter since the reader has context.

```python
# First in group — full teaching description with display label
"priority_mental_health": (
    "Taking care of mental health. Q3 multi-select: 'Which have become more important "
    "over the past year?' (up to 3 choices). TRUE = selected. "
    "COUNTIF/COUNT(*) for percentage. Percentages across priority_ columns sum >100%."
),
# Subsequent — display label + minimal context
"priority_physical_health": "Taking care of physical health. Q3 multi-select. TRUE = selected.",
"priority_relationships": "Finding/improving relationships. Q3 multi-select. TRUE = selected.",
```

## Label Conventions

Labels are key-value strings (lowercase, hyphens allowed). Use for:

| Key | Purpose | Example values |
|-----|---------|---------------|
| `survey_org` | Data provider / commissioner | `ohid`, `itv`, `yougov` |
| `data_shape` | Processing level | `user-level`, `pre-aggregated`, `raw` |
| `respondents` | Sample size | `1320`, `2249` |
| `fieldwork_year` | When collected | `2023`, `2025` |
| `wave` | Study identifier | `motn-2025`, `wuv-2024`, `ohid-2023` |
| `pipeline` | How it was built | `mandoline`, `manual` |
| `study` | Study series name | `mood-of-the-nation`, `what-unites-voters` |

## Table Description Template

```
{Study name} ({data level}). {Panel type} (n={sample size}).
Fieldwork: {dates}. Covers {topic summary}.
{Format description — one row per what}.
{Key usage notes — the things that trip people up}.
{Weighting: weighted/unweighted and scheme if applicable}.
{Caveats — small bases, multi-select behavior, sentinel handling}.
All column descriptions start with a display-ready label followed by usage guidance.
{For dual-table studies: "See also {other_table} for {other shape}"}
```

## Verification Checks

Every built table needs automated verification. Patterns:

| Check | SQL pattern | Why |
|-------|------------|-----|
| Row count | `COUNT(*) = expected` | Transformation didn't drop/duplicate |
| No NULL demographics | `COUNTIF(col IS NULL) = 0` | Decoding covered all codes |
| Distinct value counts | `COUNT(DISTINCT col) = expected` | All categories decoded |
| Value ranges | `MIN(col) >= low AND MAX(col) <= high` | No out-of-range values |
| Unique IDs | `COUNT(*) = COUNT(DISTINCT id)` | No duplicates |
| Decoded values work | `COUNTIF(col IS NULL) = 0` for decoded columns | CASE covered all inputs |
| Placeholder handling | `COUNTIF(col IS NULL) = expected_nulls` | Sentinels converted to NULL |
| **Metadata completeness** | `all(f.description for f in table.schema)` | Every column has a description |
| **Table metadata present** | `table.description and table.friendly_name and table.labels` | Table is self-documenting |
| **Display label extractable** | First sentence of each description is ≤40 chars | Labels work in charts |
