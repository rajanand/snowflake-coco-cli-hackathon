# SQL — Phase 1: Bronze Layer

Implements Phase 1 of `.snowflake/cortex/plans/supply-chain-ontology-revised.plan.md`
("Medallion Layers for Remaining Entities"). Layout follows the plan's "Repo Structure" section.

Run in order (each script is idempotent — safe to re-run for a clean rebuild):

1. `create_bronze_tables.sql` — creates the `BRONZE` schema and all 17 tables, plus governance tags.
2. `load_bronze_from_sources.sql` — ingests the 11 Phase 0 `SOURCE_*` tables into Bronze via
   explicit typed-column `INSERT ... SELECT` (1:1 column mapping, no cleansing — that happens in
   Silver). `tracking_events` passes `EVENT_PAYLOAD` through as VARIANT.
3. `generate_bronze_netnew_data.sql` — generates synthetic data directly into Bronze for the 6
   entities that have no Phase 0 fragmented-source equivalent: `parts`, `plants`, `customers`,
   `customer_orders`, `inventory_snapshots`, `quality_events`.

## Design

- **Two landing patterns**:
  - **Structured** (16 tables): typed columns mapped 1:1 from source. Source data is clean,
    relational data from ERP, TMS, Supplier Portal, and Finance systems — wrapping it in VARIANT
    would lose type safety for no gain. This covers `orders`, `deliveries`, `shipments`,
    `purchase_orders`, `pick_operations`, `demand_forecast`, `daily_cogs`, `freight_invoices`,
    `overhead_allocation`, `freight_quotes`, `parts`, `plants`, `customers`, `customer_orders`,
    `inventory_snapshots`, `quality_events`.
  - **Semi-structured** (1 table: `tracking_events`): `DEVICE_TAG` as a typed column (stable
    identifier) + `EVENT_PAYLOAD` as VARIANT (genuinely nested/variable sensor JSON with epoch_ms,
    expected_epoch_ms, sensor_battery_pct, noise_flag). This is what VARIANT is designed for — IoT
    sensor data with variable payloads and noise fields.
- **`_METADATA` OBJECT on every table**: records `source_system`, `source_table`, `ingested_at`
  regardless of landing pattern — genuinely useful lineage metadata that lets Silver's
  shipment_crosswalk (entity resolution) trace a canonical shipment back to its originating
  fragmented record.
- **Net-new entities generated directly into Bronze**: `parts`, `plants`, `customers` have no
  Phase 0 fragmented-source story to tell (no cross-team disagreement to demonstrate), so they're
  generated with one consistent schema straight into Bronze rather than through a `SOURCE_*`
  detour. `customer_orders` is calibrated to reproduce a ~91% customer-facing fill rate and a
  correlated on-time-delivery rate, consistent with the divergent-metrics story from Phase 0.
- **Governance**: `LIFECYCLE='BRONZE'` tag on the schema, mirroring the Phase 0 governance taxonomy
  in `SUPPLY_CHAIN.GOVERNANCE`.

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
