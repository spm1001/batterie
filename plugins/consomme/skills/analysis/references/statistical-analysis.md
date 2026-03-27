# Statistical Analysis Reference

Techniques for determining whether observed differences are real or noise. Essential for survey analysis and segment comparison.

## When to Read This

- Comparing metrics across segments ("is Region A really worse?")
- Evaluating whether a change over time is meaningful
- User asks "is this significant?" or "is this difference real?"
- Presenting findings to stakeholders who will ask "how confident are we?"

## Descriptive Statistics

Always compute these before any comparative analysis:

### Central Tendency

```sql
SELECT
  segment,
  COUNT(*) AS n,
  AVG(score) AS mean_score,
  APPROX_QUANTILES(score, 100)[OFFSET(50)] AS median_score,
  -- Mode: most frequent value
  (SELECT val FROM (
    SELECT score AS val, COUNT(*) AS freq
    FROM table GROUP BY score ORDER BY freq DESC LIMIT 1
  )) AS mode_score
FROM table
GROUP BY segment
```

**When to use which:**
- **Mean** — when data is roughly symmetric, no extreme outliers
- **Median** — when data is skewed or has outliers (revenue, response times)
- **Mode** — for categorical data or Likert scales ("most common response")

### Spread

```sql
SELECT
  segment,
  STDDEV(score) AS std_dev,
  APPROX_QUANTILES(score, 100)[OFFSET(75)] - APPROX_QUANTILES(score, 100)[OFFSET(25)] AS iqr,
  MAX(score) - MIN(score) AS range,
  ROUND(STDDEV(score) / NULLIF(AVG(score), 0), 3) AS coefficient_of_variation
FROM table
GROUP BY segment
```

**Coefficient of variation (CV)** — standard deviation as a proportion of the mean. Useful for comparing spread across segments with different means. CV > 1.0 indicates very high variability.

### Percentiles

```sql
SELECT
  segment,
  APPROX_QUANTILES(score, 100)[OFFSET(5)] AS p5,
  APPROX_QUANTILES(score, 100)[OFFSET(25)] AS p25,
  APPROX_QUANTILES(score, 100)[OFFSET(50)] AS p50,
  APPROX_QUANTILES(score, 100)[OFFSET(75)] AS p75,
  APPROX_QUANTILES(score, 100)[OFFSET(95)] AS p95
FROM table
GROUP BY segment
```

## Comparing Two Groups

### Is This Difference Real?

When you see different averages between groups, three things determine whether the difference is meaningful:

1. **Effect size** — how large is the difference relative to the variability?
2. **Sample size** — do we have enough data to be confident?
3. **Practical significance** — even if statistically real, does the difference matter?

### Confidence Intervals (Preferred Approach)

More informative than yes/no significance tests. Compute in BigQuery:

```sql
-- 95% confidence interval for the mean of each segment
SELECT
  segment,
  COUNT(*) AS n,
  AVG(score) AS mean_score,
  STDDEV(score) AS std_dev,
  AVG(score) - 1.96 * STDDEV(score) / SQRT(COUNT(*)) AS ci_lower,
  AVG(score) + 1.96 * STDDEV(score) / SQRT(COUNT(*)) AS ci_upper
FROM table
GROUP BY segment
```

**Interpreting:** If the confidence intervals for two groups don't overlap, the difference is likely real. If they overlap substantially, it's probably noise.

**Caution:** Non-overlapping CIs is a conservative test — intervals can slightly overlap and the difference can still be statistically significant. But it's a good quick check.

### Z-Test for Proportions

For comparing rates or percentages between groups (e.g., "is the satisfaction rate different?"):

```sql
-- Compare proportion of "satisfied" (score >= 4) between two segments
WITH stats AS (
  SELECT
    segment,
    COUNT(*) AS n,
    COUNTIF(score >= 4) AS successes,
    COUNTIF(score >= 4) / COUNT(*) AS proportion
  FROM table
  WHERE segment IN ('A', 'B')
  GROUP BY segment
)
SELECT
  a.proportion AS prop_a,
  b.proportion AS prop_b,
  a.proportion - b.proportion AS difference,
  -- Pooled proportion under null hypothesis
  (a.successes + b.successes) / (a.n + b.n) AS pooled_prop,
  -- Z-statistic
  (a.proportion - b.proportion) /
    SQRT(((a.successes + b.successes) / (a.n + b.n)) *
         (1 - (a.successes + b.successes) / (a.n + b.n)) *
         (1.0/a.n + 1.0/b.n)) AS z_score
FROM stats a, stats b
WHERE a.segment = 'A' AND b.segment = 'B'
```

**Interpreting the z-score:**
- |z| > 1.96 → significant at 95% confidence (p < 0.05)
- |z| > 2.58 → significant at 99% confidence (p < 0.01)
- |z| < 1.96 → difference is not statistically significant

### Minimum Sample Size Rules of Thumb

Before comparing groups, check you have enough data:

| Analysis Type | Minimum Per Group | Why |
|--------------|-------------------|-----|
| Proportions (rates) | 30+ | Central limit theorem |
| Means (continuous) | 30+ | Normality assumption |
| Cross-tabulation cells | 5+ per cell | Chi-squared validity |
| Subgroup comparisons | 100+ | Practical precision |

**If a segment has fewer than 30 responses, flag it as unreliable and don't draw conclusions from it.**

## Comparing Multiple Groups

### Chi-Squared Test for Independence

For categorical × categorical comparison (e.g., "does preferred channel vary by region?"):

```sql
-- Observed vs expected frequencies for chi-squared
WITH observed AS (
  SELECT
    region,
    preferred_channel,
    COUNT(*) AS observed_count
  FROM table
  GROUP BY region, preferred_channel
),
row_totals AS (
  SELECT region, SUM(observed_count) AS row_total FROM observed GROUP BY region
),
col_totals AS (
  SELECT preferred_channel, SUM(observed_count) AS col_total FROM observed GROUP BY preferred_channel
),
grand_total AS (
  SELECT SUM(observed_count) AS total FROM observed
)
SELECT
  o.region,
  o.preferred_channel,
  o.observed_count,
  ROUND(r.row_total * c.col_total / g.total, 1) AS expected_count,
  ROUND(POW(o.observed_count - r.row_total * c.col_total / g.total, 2)
        / (r.row_total * c.col_total / g.total), 3) AS chi_sq_component
FROM observed o
JOIN row_totals r ON o.region = r.region
JOIN col_totals c ON o.preferred_channel = c.preferred_channel
CROSS JOIN grand_total g
ORDER BY chi_sq_component DESC
```

Sum the `chi_sq_component` values for the overall chi-squared statistic. Large components show which region-channel combinations deviate most from expected — these are the interesting findings.

## Outlier Detection

### Z-Score Method

Flag values more than 2 or 3 standard deviations from the mean:

```sql
WITH stats AS (
  SELECT AVG(metric) AS mean_val, STDDEV(metric) AS std_val
  FROM table
)
SELECT t.*, (t.metric - s.mean_val) / NULLIF(s.std_val, 0) AS z_score
FROM table t
CROSS JOIN stats s
WHERE ABS((t.metric - s.mean_val) / NULLIF(s.std_val, 0)) > 3
```

### IQR Method (More Robust)

Less sensitive to the outliers themselves:

```sql
WITH quartiles AS (
  SELECT
    APPROX_QUANTILES(metric, 100)[OFFSET(25)] AS q1,
    APPROX_QUANTILES(metric, 100)[OFFSET(75)] AS q3
  FROM table
)
SELECT t.*
FROM table t
CROSS JOIN quartiles q
WHERE t.metric < q.q1 - 1.5 * (q.q3 - q.q1)
   OR t.metric > q.q3 + 1.5 * (q.q3 - q.q1)
```

**What to do with outliers:**
- **Investigate first** — outliers are often the most interesting data points
- **Don't remove automatically** — only exclude if they're data errors, not real extremes
- **Report both** — "with and without outliers" shows the impact

## Common Statistical Traps

### Simpson's Paradox

A trend that appears in several groups reverses when the groups are combined. Classic example: treatment A looks better in every age group, but treatment B looks better overall — because B is used more on younger (healthier) patients.

**How to detect:** Always check overall results AND segment-level results. If they disagree, look at segment sizes.

### Multiple Comparisons Problem

Testing 20 segments means one will appear "significant" by chance (at p < 0.05). The more comparisons you make, the more likely you'll find false positives.

**Mitigation:** Apply Bonferroni correction — divide your significance threshold by the number of comparisons. Testing 10 segments? Use p < 0.005 instead of p < 0.05.

### Correlation ≠ Causation

Two metrics moving together doesn't mean one causes the other. They might both be caused by a third factor, or the correlation might be coincidental.

**Before claiming causation, ask:**
- Is there a plausible mechanism?
- Does the timing make sense (cause precedes effect)?
- Is there a confounding variable that explains both?
- Has an experiment (not just observation) been done?

### Ecological Fallacy

Conclusions about groups don't apply to individuals. "Regions with higher average income have higher satisfaction" doesn't mean rich individuals are more satisfied — it might be driven by other regional factors.

### Regression to the Mean

Extreme values tend to move toward the average on remeasurement. A region with unusually low satisfaction this quarter will likely look better next quarter — even without intervention. Don't claim credit for natural regression.

## Presenting Statistical Results

### For Non-Technical Stakeholders

- Lead with the finding, not the method: "Region A's satisfaction is significantly lower (3.2 vs 4.1)"
- Use confidence intervals, not p-values: "we're 95% confident the true difference is between 0.5 and 1.3 points"
- State sample sizes: "based on 450 responses from Region A and 820 from Region B"
- Flag uncertainty: "Region C had only 18 responses — too few to draw conclusions"
- Compare to benchmarks they know: "this is similar to the drop we saw in Q3 last year"

### What NOT to Say

- "Statistically significant" without explaining what it means
- "Proves that X causes Y" (observational data can't prove causation)
- Precise percentages from tiny samples ("66.7% of the 3 respondents...")
- P-values to non-technical audiences
