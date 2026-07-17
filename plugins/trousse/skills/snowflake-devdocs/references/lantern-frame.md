# The Lantern architectural frame — read fetched Snowflake docs through this

A durable summary so any Snowflake doc is read through the right lens. **The living source of truth
is the Lantern notes** (this is a summary, not a fork):

- `~/notes/work/scaled-measurement/lantern/understanding.md` — the whole programme
- `~/notes/work/scaled-measurement/lantern/snowflake-exposure-lake-adalyser-read-2026-07-16.md` — surfacing ladder + cost + ingest-vs-read
- `~/notes/work/scaled-measurement/lantern/exposure-lake-snowflake-portability-2026-06.md` — portability + procurement route
- `~/notes/work/scaled-measurement/lantern/adalyser-aws-footprint.md` — what Adalyser runs + the Style A/B engine fork

## The durable spine

- **Separate how data gets IN from how the partner reads it OUT.** IN = Snowflake's strength
  (Secure Data Sharing + external volumes, harmonised into one schema). OUT = the constraint
  (open Iceberg-on-S3, co-located, read in place). Snowflake earns its keep at the
  harmonisation / catalog / governance layer — **not by sitting in the partner's read path.**

- **Lock-in lives in custody and format, never in compute.** Unbundle Adalyser's four verbs —
  let them keep *collect* + *compute*, move *store* + *govern* to broadcaster-controlled
  open-format storage. Canonical impressions stay in each broadcaster's own bucket; Adalyser
  reads in place via a revocable cross-account grant and keeps no durable joined copy.

- **Snowflake composes only on open Iceberg + open catalog (Polaris) + written exit-in-place** —
  never native proprietary share. Take the cost-cover for storage; keep the join on swappable compute.

- **Materialise once to where the join happens; never re-query across clouds.** Per-query
  cross-cloud egress is uncapped — the cost nobody quotes.

- **The join's gravity is fixed:** it lands where the querying party's *immovable* dataset lives
  (Adalyser's advertiser outcome data, in their AWS). Move the lake to the data, not the data to
  the lake. **Co-location landmine:** don't put Snowflake-on-GCP if Adalyser hammers it from AWS.

- **Clean room (Rung 3) is OFF for Phase 2** (16 Jul) — blindness turned out not required; a plain
  logical union suffices, so the clean room demotes to optional governance-grade audit insurance.
  **Steer = Rung 1, catalog-mediated, co-located AWS eu-west-2.**

## Open questions (verify against reality, don't assume)

- Adalyser's actual DB engine — Style B (relational legacy tag pipeline) vs Style A (lakehouse BEL).
  Question sent to Adalyser 17 Jul; answer pending.
- Which broadcaster is on which cloud — sources disagree (Snowflake's paper vs Rupert's). Cost-critical
  for co-location. Pin with Alex (Snowflake) / Nathan Stamp (ITV) / Barry John (C4).
