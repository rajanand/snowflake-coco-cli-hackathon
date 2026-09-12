# SQL — Phase 1: Bronze Layer

Implements Phase 1 of `.snowflake/cortex/plans/supply-chain-ontology-revised.plan.md`
("Medallion Layers for Remaining Entities"). Layout follows the plan's "Repo Structure" section.

Run in order (each script is idempotent — safe to re-run for a clean rebuild):

1. `create_bronze_tables.sql` — creates the `BRONZE` schema and all 17 tables (unified
   `RAW_PAYLOAD` VARIANT + `_METADATA` OBJECT envelope), plus governance tags.
2. `load_bronze_from_sources.sql` — ingests the 11 Phase 0 `SOURCE_*` tables into Bronze via
   `OBJECT_CONSTRUCT(*)` (source-shaped, no cleansing — that happens in Silver).
3. `generate_bronze_netnew_data.sql` — generates synthetic data directly into Bronze for the 6
   entities that have no Phase 0 fragmented-source equivalent: `parts`, `plants`, `customers`,
   `customer_orders`, `inventory_snapshots`, `quality_events`.

## Design

- **Unified envelope**: every Bronze table has the same 3 columns — `RAW_PAYLOAD` (VARIANT),
  `_METADATA` (OBJECT: `source_system`, `source_table`, `ingested_at`), `LOAD_TIMESTAMP`. This
  is what makes "unified raw landing" real: Silver can process any Bronze table with the same
  flattening pattern regardless of which fragmented source system (or none) it came from.
- **Net-new entities generated directly into Bronze**: `parts`, `plants`, `customers` have no
  Phase 0 fragmented-source story to tell (no cross-team disagreement to demonstrate), so they're
  generated with one consistent schema straight into Bronze rather than through a `SOURCE_*`
  detour. `customer_orders` is calibrated to reproduce a ~91% customer-facing fill rate and a
  correlated on-time-delivery rate, consistent with the divergent-metrics story from Phase 0.
- **Governance**: `LIFECYCLE='BRONZE'` tag on the schema, `SOURCE_SYSTEM='MULTI'` tag per table
  (since Bronze tables land rows from potentially many upstream systems over time), mirroring the
  Phase 0 governance taxonomy in `SUPPLY_CHAIN.GOVERNANCE`.

## Row counts (last run)

| Table | Rows | Origin |
|---|---|---|
| orders | 800 | SOURCE_ERP |
| deliveries | 800 | SOURCE_LOGISTICS_TMS |
| shipments | 800 | SOURCE_SUPPLIER_PORTAL |
| tracking_events | 560 | SOURCE_IOT_SENSOR |
| purchase_orders | 300 | SOURCE_SUPPLIER_PORTAL |
| pick_operations | 300 | SOURCE_LOGISTICS_TMS |
| demand_forecast | 600 | SOURCE_ERP |
| daily_cogs | 9000 | SOURCE_FINANCE |
| freight_invoices | 700 | SOURCE_LOGISTICS_TMS |
| overhead_allocation | 60 | SOURCE_FINANCE |
| freight_quotes | 100 | SOURCE_SUPPLIER_PORTAL |
| parts | 100 | net-new |
| plants | 20 | net-new (PLANT-001..020, matches shipments.plant_code range) |
| customers | 50 | net-new |
| customer_orders | 500 | net-new |
| inventory_snapshots | 20000 | net-new (10 days x 100 parts x 20 plants) |
| quality_events | 150 | net-new |

Row counts for the 11 ingested tables match their Phase 0 `SOURCE_*` origin exactly (Bronze is a
pass-through landing, not a transformation).

**Cross-entity ID consistency note**: `plants` was generated with 3-digit `PLANT-0XX` codes
(`PLANT-001`..`PLANT-020`) specifically to match the plant code range already emitted by
`SOURCE_SUPPLIER_PORTAL.shipments.plant_code` in Phase 0 — otherwise Silver/Gold would have an
unresolvable dimension gap for 15 of the 20 plants actually referenced by shipment data.
