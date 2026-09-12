# SQL — Phase 0: Genuine Fragmentation

Implements Phase 0 of `.snowflake/cortex/plans/supply-chain-ontology-revised.plan.md`.
Layout follows the plan's "Repo Structure" section.

Run in order (each script is idempotent — safe to re-run for a clean rebuild):

1. `00_setup_role.sql` — creates the `SUPPLY_CHAIN_ADMIN` role (avoids using ACCOUNTADMIN)
   and the `SUPPLY_CHAIN` database. Replace `<YOUR_USER>` before running.
2. `source_erp.sql` — `SOURCE_ERP.orders`, `demand_forecast` + synthetic data
3. `source_logistics_tms.sql` — `SOURCE_LOGISTICS_TMS.deliveries`, `pick_operations`,
   `freight_invoices` + synthetic data
4. `source_supplier_portal.sql` — `SOURCE_SUPPLIER_PORTAL.shipments`, `purchase_orders`,
   `freight_quotes` + synthetic data
5. `source_iot_sensor.sql` — `SOURCE_IOT_SENSOR.tracking_events` + synthetic data
6. `source_finance.sql` — `SOURCE_FINANCE.daily_cogs`, `overhead_allocation` + synthetic data
7. `01_governance_tags.sql` — governance tag taxonomy (`SOURCE_SYSTEM`, `DATA_QUALITY_ISSUE`,
   `LIFECYCLE`) applied to schemas/tables
8. `02_classification.sql` — exploratory `SYSTEM$CLASSIFY` sensitive-data check (confirms no PII)
9. `03_data_quality_metrics.sql` — DMF deployment plan (**not yet applied** — deferred; run when
   ready for continuous quality monitoring). Requires the one-time grants documented at the top
   of the file.

## Snowflake best practices applied

- **Comments/descriptions**: every database, schema, table, and column has a `COMMENT` documenting
  its purpose. Tables that carry one of the plan's genuine data-quality bugs are marked
  `KNOWN DATA QUALITY ISSUE: ...` explaining exactly how and why the metric diverges there.
- **Tags**: `SUPPLY_CHAIN.GOVERNANCE` holds the tag taxonomy — `SOURCE_SYSTEM` (schema-level),
  `LIFECYCLE` (schema-level, `RAW_FRAGMENTED` for Phase 0), and `DATA_QUALITY_ISSUE` (table-level,
  one value per genuine flaw).
- **Classification**: `SYSTEM$CLASSIFY` was run against a representative table per source system —
  zero PII/sensitive-category recommendations, as expected for this synthetic business dataset.
- **Data quality metrics**: a full DMF plan (ROW_COUNT, NULL_COUNT, DUPLICATE_COUNT,
  ACCEPTED_VALUES, FRESHNESS) is scripted and ready in `03_data_quality_metrics.sql`, deferred
  pending a decision on monitoring scope/cost.
- **ID format**: all generated natural-key/identifier values use a dash separator between prefix
  and number, e.g. `SUP-0001`, `PART-00002`, `ERP-000001`, `PRO-000001`, `ASN-000001`,
  `PLANT-001`, `PO-000001`, `PICK-000001`, `CO-000001`, `INV-000001`, `CAT-01`.

Each source file generates ~800 rows correlated by row index with `SOURCE_ERP.orders`, tuned
so the commented-out legacy query in each file reproduces the plan's target divergent spread.
Validated results from the last run:

| Metric | Source | Result | Target |
|---|---|---|---|
| OTD | ERP | 89.4% | ~90% |
| OTD | TMS | 91.3% | ~93% |
| OTD | Supplier Portal | 78.6% | ~78% |
| OTD | IoT | 83.0% | ~84% |
| Fill Rate | Procurement (PO fill) | 86.3% | ~85% |
| Fill Rate | Warehouse (unit-level) | 87.7% | ~88% |

DOI and Landed Cost legacy queries are commented out in `source_erp.sql`/`source_finance.sql`/
`source_supplier_portal.sql` since they depend on `SILVER.parts` and `GOLD.fact_inventory_snapshot`,
built in later phases (`sql/01_bronze/`, `sql/02_silver/`, `sql/03_gold/`).
