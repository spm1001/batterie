# Lantern exposure-lake slice — curated Snowflake docs index

The pages that matter for the Lantern exposure-lake architecture and the Snowflake procurement
conversation. Grouped by decision surface. Every URL fetches clean Markdown (`curl <url>`).

**Pinned live from the Snowflake section sub-indexes on 2026-07-17.** If a slug 404s, re-discover
via `references/discovery.md` and fix the entry.

Read these through `references/lantern-frame.md` — the durable architectural spine.

---

## A. Iceberg tables + external volumes — the storage layer
*Canonical impressions live in each broadcaster's own bucket, open format (Parquet→Iceberg). This is where "custody and format" lock-in is won or lost.*

- Apache Iceberg™ tables (overview) — https://docs.snowflake.com/en/user-guide/tables-iceberg.md
- Create an Iceberg table in Snowflake — https://docs.snowflake.com/en/user-guide/tables-iceberg-create.md
- Storage for Iceberg tables (managed vs external) — https://docs.snowflake.com/en/user-guide/tables-iceberg-storage.md
- Configure an external volume — https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-external-volume.md
- External volume for **Amazon S3** — https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-external-volume-s3.md
- External volume for **Google Cloud Storage** — https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-external-volume-gcs.md
- Write support for **externally managed** Iceberg tables — https://docs.snowflake.com/en/user-guide/tables-iceberg-externally-managed-writes.md
- Configure replication for Snowflake-managed Iceberg — https://docs.snowflake.com/en/user-guide/tables-iceberg-replication.md
- Iceberg best practices — https://docs.snowflake.com/en/user-guide/tables-iceberg-best-practices.md

## B. Catalog — Open Catalog (Polaris) / catalog integration
*Catalog-mediated reads = the "Rung 1" steer. Adalyser reads in place via a revocable grant; the catalog is the governance seam, not the read path.*

- Snowflake Open Catalog (Polaris) overview — https://docs.snowflake.com/en/user-guide/opencatalog/overview.md
- Snowflake Horizon Catalog — https://docs.snowflake.com/en/user-guide/snowflake-horizon.md
- Configure a catalog integration — https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration.md
- Catalog integration for Open Catalog — https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-open-catalog.md
- **Use an external query engine** with Iceberg tables — https://docs.snowflake.com/en/user-guide/tables-iceberg-use-external-query-engine.md
- Catalog-linked database — https://docs.snowflake.com/en/user-guide/tables-iceberg-catalog-linked-database.md
- Catalog-vended credentials — https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-vended-credentials.md

## C. Secure Data Sharing — how data gets IN
*Sky/C4 native Snowflake shares harmonise into one Lantern schema. Watch the "zero-copy" terminology trap: Snowflake=Data Sharing (in-account), not federation.*

- About Secure Data Sharing — https://docs.snowflake.com/en/user-guide/data-sharing-intro.md
- Create and configure shares (provider) — https://docs.snowflake.com/en/user-guide/data-sharing-provider.md
- Consume imported data (consumer) — https://docs.snowflake.com/en/user-guide/data-share-consumers.md
- **Share across regions & cloud platforms** — https://docs.snowflake.com/en/user-guide/secure-data-sharing-across-regions-platforms.md
- Share data protected by a policy (masking on shares) — https://docs.snowflake.com/en/user-guide/data-sharing-policy-protected-data.md
- Open Data Sharing (*Preview*, Iceberg-based) — https://docs.snowflake.com/en/user-guide/open-data-sharing.md
- Data sharing & collaboration (overview) — https://docs.snowflake.com/en/guides-overview-sharing.md

## D. Cost & egress — the two taps
*Intrinsic Snowflake compute (credits) + co-location-dependent egress. Per-query cross-cloud egress is UNCAPPED — the cost nobody quotes.*

- Cost & billing (overview) — https://docs.snowflake.com/en/guides-overview-cost.md
- Understanding **compute cost** (credits) — https://docs.snowflake.com/en/user-guide/cost-understanding-compute.md
- Understanding **data transfer cost** (egress) — https://docs.snowflake.com/en/user-guide/cost-understanding-data-transfer.md
- Exploring data transfer cost (ACCOUNT_USAGE) — https://docs.snowflake.com/en/user-guide/cost-exploring-data-transfer.md
- Understanding **replication cost** — https://docs.snowflake.com/en/user-guide/account-replication-cost.md
- Understanding storage cost — https://docs.snowflake.com/en/user-guide/cost-understanding-data-storage.md
- Overview of warehouses (compute sizing) — https://docs.snowflake.com/en/user-guide/warehouses-overview.md
- Auto-fulfillment costs (cross-region share egress) — https://docs.snowflake.com/en/collaboration/provider-understand-cost-auto-fulfillment.md
- Egress Cost Optimizer — https://docs.snowflake.com/en/collaboration/provider-listings-auto-fulfillment-eco.md

## E. Governance & security — Layer-B raw-IP masking, RBAC, DPA
*Layer A (broadcaster analysts): hashed ID, no channel. Layer B (Switzerland): raw IP under DPA. Masking + RBAC is how the two-layer design is enforced.*

- Data Governance (overview) — https://docs.snowflake.com/en/guides-overview-govern.md
- Securing Snowflake (overview) — https://docs.snowflake.com/en/guides-overview-secure.md
- Overview of Access Control (RBAC) — https://docs.snowflake.com/en/user-guide/security-access-control-overview.md
- Understanding **Dynamic Data Masking** — https://docs.snowflake.com/en/user-guide/security-column-ddm-intro.md
- Tag-based masking policies — https://docs.snowflake.com/en/user-guide/tag-based-masking-policies.md
- Row access policies — https://docs.snowflake.com/en/user-guide/security-row-intro.md

## F. Clean Rooms — optional governance-grade audit insurance
*Decision (16 Jul): clean room OFF for Phase 2 (blindness turned out not required). Keep for reference — it demotes to optional audit insurance, not a necessity.*

- Overview of Snowflake Data Clean Rooms — https://docs.snowflake.com/en/user-guide/cleanrooms/overview.md
- About Snowflake Data Clean Rooms — https://docs.snowflake.com/en/user-guide/cleanrooms/introduction.md

## G. Marketplace & procurement — the Q-597774 order-form context
*The clean GCP-Marketplace clickthrough is private-offer-only; Snowflake pushed a direct capacity order form. Useful for reading what the order shapes actually commit to.*

- About listings — https://docs.snowflake.com/en/collaboration/collaboration-listings-about.md
- Paid listings pricing models — https://docs.snowflake.com/en/collaboration/provider-listings-pricing-model.md

## H. Cortex — secondary (downstream analytical uses)
*Not on the Phase-2 critical path (clean room off), but relevant to the "right-hand side of the diagram" — what analysts do once the lake exists.*

- Snowflake AI and ML (overview) — https://docs.snowflake.com/en/guides-overview-ai-features.md
- Cortex Analyst (NL→SQL over semantic views) — https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst.md
