---
name: mandoline
description: "MANDATORY BEFORE loading data into BigQuery — transforms SPSS files, CSVs, and spreadsheet dumps into self-documenting tables (respondent-level or pre-aggregated). Invoke FIRST when you see raw column names (S1, Q1r3), numeric codes, or empty BQ descriptions. 7-phase workflow: SPSS extraction, schema design, transformation, teaching descriptions with display-label pattern, metadata enrichment, verification. Triggers on 'make this data analysis-ready', 'build a clean BQ table', 'load this SPSS file', 'enrich this table', 'process this codebook'. (user)"
---

# Mandoline

The precision slicer. Takes irregular raw data and produces uniform, self-documenting BigQuery tables.

**Iron Law: Descriptions teach, they don't just define.** Every column description answers three questions: What is it? What are the values? What do I DO with it?

**Second Law: The first clause is the display label.** Every description starts with a short, clean phrase suitable as a chart axis label or column header — before the teaching detail begins.

## When to Use

- SPSS files (`.sav`) with survey data — the richest input source
- Raw survey data with opaque column names (`S1`, `Q1r1`, coded integers)
- CSV/spreadsheet dumps loaded into BQ without metadata
- Any BQ table where `INFORMATION_SCHEMA.COLUMNS` returns empty descriptions
- Pre-aggregated cross-tab exports that need reshaping
- When someone says "make this data a pleasure to analyse"
- Before pointing an LLM at a BQ table for the first time

## When NOT to Use

- Data already has rich column descriptions and metadata
- Quick exploratory queries on known-good tables (use consomme instead)
- One-off ad hoc analysis that doesn't need a persistent clean table
- Streaming/real-time data (mandoline is for snapshot tables)

## Input Sources — Choosing Your Starting Point

Survey data arrives in many forms. Each has different strengths:

| Source | Richness | Use for |
|--------|----------|---------|
| **SPSS (.sav)** | **Best** — column labels, value labels, question text, sentinels all embedded | Respondent-level tables. Start here when available. |
| **Codebook (DOCX/PDF)** | Good — full question wording, routing logic, display settings | Supplements SPSS. Essential when SPSS labels are truncated. |
| **Aggregate spreadsheet** | Variable — cross-tab export, often messy headers | Pre-aggregated tables. Each study needs bespoke parsing. |
| **Raw BQ table** | Minimal — just column names and types | When data is already in BQ but undocumented. |
| **CSV dump** | Minimal — column names only, no metadata | Lowest quality input. Needs codebook or SPSS alongside. |

**When you have multiple sources for the same study, use them in combination.** SPSS provides the systematic metadata; the codebook adds question context and routing; the aggregate sheet shows how the research agency structured their cross-tabs.

## The Workflow

Seven phases. The first is new — SPSS extraction — and feeds directly into the existing six.

### Phase 0: Extract SPSS Metadata (when .sav available)

SPSS files via `pyreadstat` are the single richest input. One file gives you column names, full question text, all value codes with labels, and sentinel values.

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyreadstat"]
# ///
import pyreadstat

df, meta = pyreadstat.read_sav("survey.sav", metadataonly=True)

# What you get:
# meta.column_names          — ['A1', 'A3__1', 'A3__2', ...]
# meta.column_names_to_labels — {'A1': 'Which ONE of the following best describes...'}
# meta.variable_value_labels  — {'A1': {1.0: 'Stressed', 2.0: 'Frustrated', ...}}
# meta.original_variable_types — {'A1': 'F8.0', ...}
# meta.number_rows            — 2249
```

**What pyreadstat gives you automatically:**

| Metadata | Where | Example |
|----------|-------|---------|
| Question text | `column_names_to_labels` | `'Which ONE of the following best describes how you currently feel?'` |
| Response codes | `variable_value_labels` | `{1.0: 'Stressed', 2.0: 'Frustrated', ..., 977.0: "Don't know"}` |
| Sentinel values | Value labels with codes ≥ 900 | `{999.0: 'None of these', 9998.0: 'skipped', 9999.0: 'not asked'}` |
| Question grouping | Column name patterns | `A3__1` through `A3__16` = multi-select group |
| Data types | `original_variable_types` | `F8.0` = numeric, `A100` = string of width 100 |

**Interpreting SPSS column name patterns:**

| Pattern | Meaning | BQ type |
|---------|---------|---------|
| `A1` (standalone) | Single-select question | STRING (decode via value labels) |
| `A3__1` through `A3__16` (double underscore + number) | Multi-select group (binary per option) | BOOL (`1.0='selected'` → TRUE) |
| `A4__1` through `A4__13` (with Likert value labels) | Grid/matrix question | INT64 (keep scale for AVG) |
| `B1_1` through `B1_14` (single underscore) | Another multi-select or grid variant | Check value labels to distinguish |
| `profile_gender`, `age_cb1_1` | Demographics / panel variables | STRING (decode) or derived |
| `caseid`, `weight` | Structural | STRING (ID), FLOAT64 (weight) |

**Sentinel detection:** Values ≥ 900 in the value labels are almost always sentinels — but **binary multi-select columns use small sentinel codes** (typically 8='skipped', 9='not asked') because the valid range is only 1-2. Check value labels for any column where the response set includes 'selected'/'not selected'.

| Code | Context | Meaning | BQ treatment |
|------|---------|---------|-------------|
| `977` / `977.0` | Single/Likert | Don't know | See decision framework below |
| `995` | Single-select | Other (specify) | Usually has companion free-text column |
| `999` | Single-select | None of these | Keep as valid STRING response |
| `8` / `9` | Multi-select binary | Skipped / not asked | NULL the BOOL |
| `9998` | Any | Skipped (routing) | NULL |
| `9999` | Any | Not asked | NULL |

**"Don't know" decision framework:** DK is not always noise.
- **Feeling/mood questions** (A1 "how do you feel?"): DK is meaningful — people genuinely don't know. Keep as a valid STRING value.
- **Factual recall** (Q5 "have you seen this ad?"): DK adds nothing analytically. NULL it.
- **Likert agreement** (A4 "agree/disagree"): DK breaks the scale — exclude from means (NULL or filter with `WHERE col <= 5`).
- **When in doubt:** Keep as STRING in the clean table; analysts can filter later. NULLing is irreversible.

**Multi-select meta-options** (`A3__999` "None of these", `A3__977` "Don't know"): These are modelled as their own binary columns, not sentinel values within other columns. Keep as BOOL columns (`priority_none_of_these`, `priority_dont_know`). Note in the first-column description that `priority_none_of_these` is mutually exclusive with substantive options. Don't use them to NULL other columns — keep the data as recorded.

**SPSS labels may lack question stems.** Multi-select option labels (e.g. `A3__1: "Taking care of my mental health"`) only show the option text, not the question stem ("Which of the following have become more important over the past year?"). The stem lives in the codebook or can sometimes be inferred from the survey section header. If no codebook is available, note the gap in the first-column description: describe the group pattern and what you know, flag what's missing.

**Exit criterion:** You have a complete mapping of SPSS columns → clean column names, types, and value decodings. The codebook (if available) has filled any gaps in question stems or routing.

### Phase 0.5: Supplement with Codebook (when available)

Codebooks add what SPSS metadata sometimes lacks:

- **Full question stems** — SPSS labels may be truncated at 256 chars. The codebook has the complete wording.
- **Routing logic** — "Asked only if A1 ≠ 999" tells you why columns have NULLs (not missing data, just not asked).
- **Randomisation** — "order randomize($Rand14)" means response order was randomised per respondent; don't assume the code order implies importance.
- **Max selections** — "max 3" on multi-select tells you the response pattern is constrained.
- **Grid structure** — which rows share a common stem and response scale.

**Codebook formats vary wildly.** Survey platform exports (Decipher, Qualtrics, SurveyMonkey) each have their own layout. The key information is always: question code → question text → response codes → response labels. Everything else (chart settings, display options, filters) is platform noise.

**When SPSS + codebook disagree**, trust SPSS for codes and values (it's the data), trust the codebook for full question wording (it's the instrument).

### Phase 1: Inspect Raw Source

Before designing anything, understand what you have. This phase uses SPSS metadata (from Phase 0) as the primary source when available, falling back to direct BQ inspection.

**From SPSS (preferred):**
```python
# Automated inspection script
for name in meta.column_names:
    label = meta.column_names_to_labels.get(name, "")
    vals = meta.variable_value_labels.get(name, {})
    sentinels = {k: v for k, v in vals.items() if k >= 900}
    responses = {k: v for k, v in vals.items() if k < 900}
    print(f"{name}: {label[:80]}")
    print(f"  Responses: {len(responses)}, Sentinels: {list(sentinels.values())}")
```

**From BQ (when data already loaded):**
```python
from google.cloud import bigquery
c = bigquery.Client(project=PROJECT)
t = c.get_table(f'{PROJECT}.{DATASET}.{TABLE}')
for f in t.schema:
    print(f'{f.name} ({f.field_type}) — {f.description or "(none)"}')
```

**Check:**
- Opaque column names needing rename
- Numeric codes needing decode to labels
- Junk rows to filter (terminated, non-consenting, `status ≠ 3`)
- Sentinel values (9998, 9999, 999999, -1) to NULL
- Whether it's Sheets-linked (fragile — snapshot to native)
- Fieldwork dates from timestamps or metadata
- Null counts, value ranges, distinct counts
- Weight column (present? what weighting scheme?)

**Exit criterion:** Every column's purpose, valid range, and transformation known.

### Phase 2: Design Clean Schema

| Decision | Guideline |
|----------|-----------|
| **Name** | Descriptive snake_case. Prefix groups: `action_`, `attitude_`, `awareness_`, `priority_` |
| **Type** | STRING for decoded categories, BOOL for binary multi-select, INT64 for Likert scales, FLOAT64 for weights/measurements |
| **Drop** | Constants, internal platform IDs, panel metadata, routing variables (unless needed for filtering) |
| **Decode** | Single-select → STRING labels. Multi-select binary → BOOL. Likert → keep as INT for AVG(). **Always note scale direction in description** — some studies use 1=Agree...5=Disagree (lower=more agreement), others reverse it. State it explicitly. |
| **Sentinels** | `9998`/`9999` → NULL (not asked/skipped). `977` (Don't know) → keep or NULL depending on whether DK is analytically meaningful. `999` (None of these) → keep as valid STRING. |
| **Weight** | Include as `weight` (FLOAT64) if the study is weighted. Note weighting scheme in table description. |
| **Nets** | For pre-aggregated tables with Likert scales, include `is_net` rows for top-2-box (e.g. "Net: Agree" = Strongly Agree + Somewhat Agree) and bottom-2-box. Label names should match the scale direction. Without these, downstream models have no path to stakeholder-friendly summary scores — the linter blocks SUM(pct). |

**Exit criterion:** Complete raw → clean mapping table.

### Phase 3: Write Transformation SQL

For SPSS → BQ, the build script loads via pyreadstat and uses the BQ client to create the table. For BQ-to-BQ transforms:

```sql
CREATE OR REPLACE TABLE `project.dataset.clean_table` AS
SELECT
  CAST(caseid AS STRING) AS respondent_id,
  CASE profile_gender
    WHEN 1 THEN 'Male' WHEN 2 THEN 'Female'
    WHEN 3 THEN 'Other gender identity' WHEN 4 THEN 'Prefer not to say'
  END AS gender,
  -- Multi-select: binary → BOOL, sentinels → NULL
  IF(A3__1 IN (8, 9), NULL, A3__1 = 1) AS priority_mental_health,
  -- Likert: keep as INT, sentinels → NULL
  IF(A4__1 IN (977, 8, 9), NULL, CAST(A4__1 AS INT64)) AS attitude_belonging,
  -- Single-select: decode to label
  CASE A1
    WHEN 1 THEN 'Stressed' WHEN 2 THEN 'Frustrated' ...
    WHEN 977 THEN NULL WHEN 9998 THEN NULL WHEN 9999 THEN NULL
  END AS current_feeling,
  weight,
FROM `project.dataset.raw_table`
WHERE status = 3  -- qualified only (or equivalent filter)
```

**For SPSS-first workflows**, the build script pattern is:

```python
# Load SPSS → pandas → BQ
df, meta = pyreadstat.read_sav("survey.sav")
# Apply transformations in pandas (decode, rename, cast)
# Load to BQ via client.load_table_from_dataframe()
# Then apply schema metadata in a separate step
```

### Phase 4: Write Teaching Descriptions

This is where the value lives. See `references/enrichment-checklist.md` for the full inventory.

**Three questions every description answers:**
1. **What is it?** — Field definition
2. **What are the values?** — Enumeration, range, encoding
3. **What do I DO with it?** — Usage guidance, gotchas, relationships

**The Display-Label Rule:** Every description starts with a short, clean phrase (under ~40 chars) that works as a chart axis label or UI column header. The teaching detail follows after a period or colon.

```python
# Pattern: "Display label. Teaching detail."
# The first sentence IS the chart label.

# BAD — no usable display label:
"Q1 multi-select: 'Done physical activity (e.g. gone for a walk etc.)'. TRUE = selected."

# GOOD — display label first, then teaching:
"Physical activity. Q1 multi-select: 'Done physical activity (e.g. gone for a walk)'. TRUE = selected. COUNTIF/COUNT(*) for percentage."

# BAD — generic column name restated:
"Percentage value"

# GOOD — contextual display label:
"Survey result (%). Pre-calculated weighted percentage as decimal (0.12 = 12%). NEVER SUM or AVG — already computed."
```

**First-column rule:** First description in each question group is richest — it teaches the pattern. Subsequent columns in the same group can be shorter since the reader has context.

```python
# First in group — full teaching:
"priority_mental_health": (
    "Taking care of mental health. Q3 multi-select: 'Which have become more important "
    "over the past year?' TRUE = selected (up to 3 choices). "
    "COUNTIF/COUNT(*) for percentage. Percentages across priority_ columns sum >100%."
),
# Subsequent in group — shorter, pattern established:
"priority_physical_health": "Taking care of physical health. Q3 multi-select. TRUE = selected.",
"priority_relationships": "Finding/improving romantic relationships. Q3 multi-select. TRUE = selected.",
```

**Why the display-label rule matters:** Plongeur (and any LLM consuming the table) uses column descriptions as fallback axis labels when the model doesn't alias columns in SQL. If the first clause is a clean display phrase, the chart layer can extract it automatically — no hardcoded `AXIS_LABEL_FALLBACKS` dict needed. The description serves double duty: teaching the LLM AND labelling the output.

### Phase 5: Enrich Table Metadata

```python
table.description = TABLE_DESCRIPTION      # Methodology paragraph
table.friendly_name = "Short Display Name"  # BQ console
table.labels = {                            # Data Catalog / programmatic filtering
    "survey_org": "itv",
    "data_shape": "user-level",             # or "pre-aggregated"
    "respondents": "2249",
    "fieldwork_year": "2025",
    "wave": "motn-2025",                    # study identifier
    "pipeline": "mandoline",
}
client.update_table(table, ["schema", "description", "friendly_name", "labels"])
```

**Table description template:**

```
{Study name} ({data level}). {Panel type} (n={sample size}).
Fieldwork: {dates}. Covers {topic summary}.
{Format description — one row per what}.
{Key usage notes — the things that trip people up}.
{Weighting: weighted/unweighted and scheme if applicable}.
{Caveats — small bases, multi-select behavior, sentinel handling}.
All column descriptions start with a display-ready label followed by usage guidance.
```

**Why table.labels matter for Plongeur:** The `data_shape` label can drive data-shape detection programmatically instead of Plongeur's current heuristic (counting signals like `has_pct`, `has_is_net`). The `wave` label enables cross-study filtering. The `pipeline: mandoline` label marks tables built by this process.

### Phase 6: Verify

Two layers: **structural checks** (built into the builder) and **cross-validation** (RLD vs AGG when both shapes exist).

#### Structural checks (always run)

The `spss_bq_builder.py` framework runs these automatically:

```python
CHECKS = [
    ("Row count", sql, lambda r: r["n"] == expected),
    ("No duplicate respondent IDs", ...),
    ("All columns have descriptions", schema_check),
    ("Table description present", ...),
    ("Friendly name present", ...),
    ("Labels include data_shape and pipeline", ...),
    ("Display labels ≤40 chars", ...),
    ("Weight column has no NULLs", ...),
]
```

#### Five failure modes (cross-validation)

Run these after building any RLD table. They catch the transformation bugs that structural checks miss:

| # | Failure mode | What to test | How it manifests |
|---|---|---|---|
| 1 | **Sentinel leakage** | Single-select: no numeric strings. Likert/bipolar: range 1-5 only. Multi-select: only TRUE/FALSE/NULL. | Sentinel codes (8, 9, 977, 9998) appear as real values instead of NULL |
| 2 | **Multi-select polarity** | Compare RLD `COUNTIF(col)/COUNT(*)` against AGG `pct` for same question | If 1/2 mapping inverted, percentages are complements (~66% instead of ~34%) |
| 3 | **Weight distortion** | Weights sum to n, all positive, no NULLs, max < 5 | Wrong weights inflate/deflate percentages; outliers suggest misparse |
| 4 | **Value label gaps** | No `SAFE_CAST(col AS FLOAT64) IS NOT NULL` on decoded STRING columns | Unmapped codes appear as raw numbers ("1" instead of "Male") |
| 5 | **Demographic derivation** | Derived columns (age_group, social_grade) have no NULLs, correct distinct values | Wrong source flags → mismatched segments or missing respondents |

When both RLD and AGG exist for the same study, do spot-check percentage comparisons: pick 3-4 questions across types (single-select, multi-select, demographic cross-tab) and verify within 2pp (AGG tables typically round to whole percentages).

**Metadata completeness.** After enrichment, verify that every column has a non-empty description and that the table has a description, friendly_name, and labels. An undocumented column is a bug.

## Data Shapes

### Respondent-Level Data (RLD)

One row per respondent. Columns are demographics + survey questions. Built from SPSS files using `spss_bq_builder.py` (see Script Pattern above).

**Key patterns:**
- Demographics as decoded STRING columns (gender, age_group, region)
- Derived convenience demographics (age_group, social_grade, generation) from binary panel flags — additions, not replacements
- Multi-select questions as BOOL columns (one per option), with companion long-format VIEWs
- Likert scales as INT64 (keep numeric for AVG)
- Bipolar semantic differentials as INT64 (1=left pole, 5=right pole)
- Single-select as decoded STRING
- Sentinels (skipped, not asked) as NULL
- Weight column (FLOAT64) — apply to all analyses

**Column counts are high** (200-350 for typical surveys). All columns get descriptions — the builder auto-generates from SPSS metadata, with codebook supplement providing question stems and display labels for battery items.

**Companion tables and views:**
- **Dictionary table** (`{table}_dictionary`) — maps column names to display labels, battery themes, and ordinals. Gemini uses UNPIVOT + JOIN for battery analysis with clean chart labels and survey ordering. Every column gets a row; battery columns get a `theme` (e.g. `priority_self_*`) and `ordinal`; non-battery columns get `theme = 'demographic'`.
- **Numeric companion columns** (`{col}_num`) — pre-calculated FLOAT64 midpoints for categorical string ranges (e.g. TV viewing hours). Eliminates CASE WHEN in queries. Added via `numeric_companions` parameter in the builder.
- **Long-format VIEWs** (`{table}_multiselect`) — for multi-select questions, simpler than UNION ALL over BOOL columns.

**Consumption:** Gemini aggregates freely — `COUNT`, `AVG`, `GROUP BY`. For battery analysis, UNPIVOT + JOIN the dictionary for labels and ordering.

### Pre-Aggregated Data

One row per question × response × demographic segment. Columns include `pct`, `base_n`, `label`, `label_order`, `segment`, `segment_value`, and optionally `is_net`.

**Key patterns:**
- `pct` is pre-calculated (weighted). NEVER `SUM` or `AVG` it.
- `base_n` varies per segment (different group sizes).
- `label_order` controls chart axis ordering — never sort alphabetically.
- `is_net` marks summary rows (e.g. "Net: Agree") that shouldn't be summed with constituent rows.
- Each segment has independent percentages that sum to 100% within a question.

**Column description patterns for pre-aggregated tables:**

```python
COLUMN_DESCRIPTIONS = {
    "question_code": "Question identifier. Maps to sections (A=mood, B=society, C=media). Use for filtering.",
    "question_text": "Full question wording. Display in chart titles or analysis headers.",
    "section": "Survey section. Groups related questions thematically.",
    "response_type": "Response format. Values: single_select, multi_select, likert, grid. Determines aggregation rules.",
    "label": "Response option. The answer text for this row (e.g. 'Stressed', 'Somewhat agree'). Use as chart category axis.",
    "label_order": "Display sequence (1-based). ORDER BY label_order for charts — never alphabetically. Preserves scale direction.",
    "pct": "Survey result (%). Pre-calculated weighted percentage as decimal (0.35 = 35%). NEVER use SUM() or COUNT() — already computed. For cross-segment comparison use SAFE_DIVIDE(SUM(pct * base_n), SUM(base_n)).",
    "base_n": "Weighted base (sample size). Varies per segment — use for reliability checks. Flag base_n < 100 as potentially unreliable.",
    "segment": "Demographic break variable (e.g. 'gender', 'age_group', 'region'). Use WHERE segment = '...' AND segment_value = '...' to filter.",
    "segment_value": "Demographic break value (e.g. 'Male', '18-24', 'London'). The specific group within the segment.",
    "is_net": "Summary row flag. TRUE for aggregate rows like 'Net: Agree' (= Strongly Agree + Somewhat Agree). These summarise other responses — do not sum with constituent rows.",
    "question_stem": "Shared stem for grid questions. When multiple items share a stem, this is the common prefix.",
}
```

**Consumption:** Gemini selects and filters but doesn't re-aggregate. The system prompt teaches `WHERE segment = '...'` patterns and forbids `SUM(pct)`.

### Dual-Table Strategy

When both RLD and pre-aggregated data exist for the same study:

| Aspect | Convention |
|--------|-----------|
| **Dataset** | Same BQ dataset (e.g. `survey_data`) |
| **Table naming** | `{study}_rld` and `{study}_agg` (e.g. `motn_2025_rld`, `motn_2025_agg`) |
| **Shared labels** | Same `wave` label value, same `survey_org` |
| **Cross-references** | Table descriptions reference each other: "See also `motn_2025_agg` for pre-aggregated cross-tabs" |
| **Column naming** | RLD column names should appear in agg `question_code` where possible |
| **Use case guidance** | Table descriptions say when to use which: RLD for custom aggregation, agg for quick cross-tab lookup |

## Messy Aggregate Sheets

Pre-aggregated data from research agencies arrives as cross-tab exports — each one structured differently. There is no universal parser.

**Common patterns to expect:**
- Header rows with segment group names spanning multiple columns
- Sub-header rows with segment values
- Base/universe/weighting metadata in the first few rows
- Question text as row headers
- Response labels as sub-rows
- Percentages in the body cells
- "NET" rows summarising groups of responses

**Approach:**
1. Read the sheet headers to understand the segment layout
2. Identify where question blocks start and end
3. Parse into the standard shape: `question_code, question_text, label, label_order, pct, base_n, segment, segment_value, is_net`
4. Each study gets its own parsing logic — don't try to generalise

**The WUAK table in Plongeur was built this way.** It took considerable thought. New aggregate sheets will be similarly bespoke. Budget time accordingly.

## Script Pattern

Two approaches depending on table complexity:

### Builder framework (for SPSS → RLD, 100+ columns)

`scripts/spss_bq_builder.py` automates 90% of RLD table construction. Study-specific scripts provide configuration:

```python
# scripts/build_study_2025.py
from spss_bq_builder import SpssTableBuilder

builder = SpssTableBuilder(
    spss_path="~/Taildrive/study.sav",
    project="project", dataset="survey_data", table_name="study_2025_rld",
    table_description="...", friendly_name="...", table_labels={...},
    codebook_supplement={                    # What SPSS metadata doesn't carry
        "A3": {"stem": "Which priorities?", "max_select": 3},
        "A4__1": {"display_label": "Belonging in local area"},
        "B3__1": {"display_label": "Angry vs tolerant", "note": "Left: angry. Right: tolerant."},
    },
    derived_demographics=[                   # Clean columns from binary flags
        {"name": "age_group", "source_map": {"age_cb1_1": "18-24", ...}},
    ],
    numeric_companions=[                     # Pre-calculated midpoints for categorical ranges
        {"source": "tv_hours_bbc_total", "target": "tv_hours_bbc_num",
         "label": "BBC (hours/week)",
         "map": {"Less than 1 hour per week": 0.5, "1-2 hours per week": 1.5, ...}},
    ],
)
builder.run()  # or builder.run(dry_run=True) to test without BQ
```

The builder auto-classifies columns (multi-select, Likert, bipolar, single-select, binary flag, structural), handles sentinel codes per detected pattern, decodes value labels, generates Mandoline descriptions from SPSS metadata + codebook supplement, and runs verification checks. Study scripts add the 10% that needs human judgment: question stems, display labels, derived demographics, numeric companions.

**Key design decisions in the builder:**
- Bipolar scales detected via `(1)` suffix in value labels (right-pole indicator)
- Battery items with identical SPSS labels get `"{prefix} item {n}"` display labels unless overridden
- Codebook supplement matched by column name, group name, or prefix (`A4__1` → tries `A4__1`, then `A4`)
- `pd.DataFrame(dict)` construction instead of column-by-column to avoid fragmentation warnings
- **Dictionary themes:** Multi-word prefixes (e.g. `unites_community`, `priority_self`) must be in the `_battery_note()` prefix list — otherwise they collapse to the first word. Non-battery columns get `theme = 'demographic'` (never NULL).
- **Numeric companions** run after rename (Phase 4.5) so specs use final column names, not SPSS codes
- **Prefix list sync:** `_battery_note()` in `spss_bq_builder.py` and `MULTI_WORD_PREFIXES` in `data.py` must match — add new prefixes to both when adding columns

### Manual scripts (for agg tables, simple transforms, <30 columns)

Standalone PEP 723 script. Run with `uv run --script scripts/build_X_table.py`. Idempotent.

```
# /// script
# requires-python = ">=3.11"
# dependencies = ["google-cloud-bigquery", "pyreadstat"]
# ///

Constants → COLUMN_DESCRIPTIONS dict → TRANSFORM (SQL or pandas) → CHECKS → main()
```

Use for: pre-aggregated tables parsed from messy sheets, BQ-to-BQ transforms, enrichment-only updates.

## Multi-Select Long-Format VIEWs

Wide RLD tables store multi-select questions as BOOL columns (one per option). This forces Gemini to write N-arm UNION ALL queries to aggregate — the #1 friction point.

**Solution:** Companion BQ VIEWs that unpivot multi-select groups into rows.

```
-- Wide (hard for Gemini):
SELECT 'Mental health' AS priority, COUNTIF(A3__1) FROM t
UNION ALL SELECT 'Physical health', COUNTIF(A3__2) FROM t  -- 16 more

-- Long-format VIEW (easy):
SELECT response_label, SUM(IF(is_selected, weight, 0)) / SUM(weight) AS pct
FROM study_multiselect WHERE question_group = 'A3'
GROUP BY response_label ORDER BY pct DESC
```

**Build VIEWs for double-underscore groups** (`A3__1`, `C1__19`) — these are the classic multi-select batteries where the UNION ALL pain is worst. Single-underscore binary batteries (`B1_1`, `B2_3`) have descriptive labels and are less problematic, but monitor Gemini logs for struggles and extend if needed.

**VIEW schema:** `caseid, weight, question_group, response_label, is_selected`

**Naming:** `{study}_multiselect` (e.g., `wuak_2025_multiselect`). One VIEW per study containing all double-underscore groups. Sentinel rows (skipped/not asked) excluded via `WHERE col IS NOT NULL`.

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| "Column: description of column" | Circular | Answer three questions, display label first |
| Empty BQ descriptions | LLMs fly blind | Every column described |
| Numeric codes in clean table | Codebook lookup every query | Decode to labels |
| No verification | Silent bugs | Automated checks including metadata completeness |
| External datamap as prompt | Token-hungry, fragile | Bake into schema |
| Sheets-linked external table | Breaks on edit | Snapshot to native |
| Description starts with internal code | Unusable as display label | Start with human-readable phrase |
| Hardcoded axis label fallbacks in app | Couples app to specific tables | Use description first-clause as label source |
| Same `pct` description for RLD and agg | Misleading | RLD has no `pct`; describe per data shape |
| Ignoring SPSS when available | Reinventing metadata by hand | SPSS → pyreadstat → automated extraction |
| Trusting SPSS labels completely | Labels may be truncated at 256 chars | Cross-check with codebook for long questions |

## Integration

- **Consomme** analyses what mandoline produces
- **Plongeur** auto-discovers mandoline tables via INFORMATION_SCHEMA; uses `table.labels` for data-shape detection; extracts first clause of descriptions as chart axis labels
- **pyreadstat** reads SPSS files — `uv run --with pyreadstat` for one-off scripts
- Build scripts live alongside consuming app (e.g. `plongeur/scripts/`)
