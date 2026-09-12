# SQL — Phase 3: Gold Layer

Implements Phase 3 of `.snowflake/cortex/plans/supply-chain-ontology-revised.plan.md`
("Medallion Layers for Remaining Entities"). Layout follows the plan's "Repo Structure" section.

Run `create_gold_dynamic_tables.sql` — creates the `GOLD` schema and the full dimensional model
(all Dynamic Tables except `dim_date`, which is a static calendar spine):

- **Dimensions**: `dim_supplier` (SCD2-shaped), `dim_part`, `dim_plant`, `dim_customer`, `dim_date`
- **Facts**: `fact_shipment`, `fact_order_fulfillment`, `fact_inventory_snapshot`,
  `fact_quality_event`, `fact_purchase_order`, `fact_pick_operation`, `fact_landed_cost`
- **Bridge**: `bridge_supplier_part` (many-to-many, derived from observed shipments)
- **Aggregate**: `agg_supplier_performance` (pre-aggregated scorecard, `TARGET_LAG='15 MINUTES'`)

## Design

- **`dim_supplier` is SCD2-shaped**, not SCD2-tracked: it carries `valid_from`/`valid_to`/
  `is_current` columns, but since `SILVER.suppliers` recomputes attributes fresh on every
  Dynamic Table refresh (no upstream change history to preserve in this demo), every row is
  currently open-ended (`valid_to = NULL`, `is_current = TRUE`). The shape is ready for real
  history capture via a stream+task if supplier tier/region ever starts changing upstream.
- **`fact_shipment`** is the canonical shipment fact built directly on `SILVER.shipment_crosswalk`
  — `is_on_time` is the single governance-approved OTD measure that backs
  `SEMANTIC_MODELS.on_time_delivery_rate` in Phase 4.
- **`fact_inventory_snapshot`** exposes `days_of_inventory` using the Warehouse (30-day trailing
  actual demand) methodology — the CANONICAL DOI definition per governance — while also carrying
  `current_stock`/`inventory_value` so the Streamlit "Before" tab can still run the legacy
  DOI-Planning/DOI-Finance comparison queries against Gold.
- **`agg_supplier_performance`** joins `fact_shipment`, `bridge_supplier_part`, and
  `fact_quality_event` into a one-row-per-supplier scorecard (on-time rate, shipment value,
  distinct parts supplied, quality defect rate) so dashboards don't re-scan facts at query time.
- **`fact_purchase_order`**, **`fact_pick_operation`**, and **`fact_landed_cost`** complete
  coverage of the plan's four headline metrics: supplier-facing PO fill rate, warehouse
  unit-level fill rate, and full-stack landed cost per unit (`unit_cost` + `freight_cost_per_unit`
  + `customs_duty_per_unit` + `handling_fee_per_unit`), computed at shipment grain.

## Validated row counts (last run)

| Table | Rows |
|---|---|
| dim_supplier | 50 |
| dim_part | 100 |
| dim_plant | 20 |
| dim_customer | 50 |
| dim_date | 1095 (3 calendar years) |
| fact_shipment | 800 |
| fact_order_fulfillment | 500 |
| fact_inventory_snapshot | 20000 |
| fact_quality_event | 150 |
| bridge_supplier_part | 100 |
| agg_supplier_performance | 50 |
| fact_purchase_order | 300 |
| fact_pick_operation | 300 |
| fact_landed_cost | 800 |

Canonical on-time delivery rate at the Gold layer: **64.9%** — matches the Silver
`shipment_crosswalk` result exactly, since `fact_shipment` is a pure pass-through with dimension
keys attached, not a re-derivation.
