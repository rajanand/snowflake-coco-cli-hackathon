# SQL — Phase 2: Silver Layer

Implements Phase 2 of `.snowflake/cortex/plans/supply-chain-ontology-revised.plan.md`
("Medallion Layers for Remaining Entities"). Layout follows the plan's "Repo Structure" section.

Run in order (each script is idempotent — safe to re-run for a clean rebuild):

1. `create_silver_dynamic_tables.sql` — creates the `SILVER` schema and 14 Dynamic Tables
   (`TARGET_LAG = '5 MINUTES'`, `WAREHOUSE = COMPUTE_WH`): master data dimensions (`suppliers`,
   `parts`, `plants`, `customers`) and canonical entity tables for every metric feed
   (`customer_orders`, `purchase_orders`, `pick_operations`, `demand_forecast`, `daily_cogs`,
   `inventory_snapshots`, `freight_invoices`, `overhead_allocation`, `freight_quotes`,
   `quality_events`).
2. `shipment_crosswalk.sql` — the entity-resolution centerpiece Dynamic Table, kept in its own
   file per the plan.

## Design

- **VARIANT key casing**: the 11 Bronze tables ingested from Phase 0 `SOURCE_*` systems via
  `OBJECT_CONSTRUCT(*)` have **UPPERCASE** keys (Snowflake's default unquoted identifier case),
  e.g. `raw_payload:ERP_ORDER_NUMBER`. The 6 net-new Bronze tables used explicit **lowercase**
  keys, e.g. `raw_payload:part_id`. VARIANT path notation is case-sensitive, so every Silver
  table below matches whichever casing its specific Bronze source actually used.
- **Dedup pattern**: every Dynamic Table uses `QUALIFY ROW_NUMBER() OVER (PARTITION BY <natural
  key> ORDER BY load_timestamp DESC) = 1`.
- **shipment_crosswalk** resolves the same physical shipment across ERP order, TMS delivery,
  Supplier Portal ASN, and IoT tracking device into one `canonical_shipment_id`:
  - Join strategy: correlates the numeric sequence embedded in each system's own ID format
    (`ERP-000001` / `PRO-000001` / `ASN-000001`) — deterministic, more robust than fuzzy
    `EDITDISTANCE` when the noise is confined to prefix/suffix/casing around a stable numeric
    core.
  - `resolved_supplier_id` trusts `SOURCE_ERP.orders.supplier_code` as the system of record.
    `resolved_supplier_from_tms` independently regex-normalizes the free-text TMS supplier name
    (handles `"Supplier-002 Corp."` / `"SUPPLIER-002"` / `"Supplier-002"` spelling variants).
    `supplier_identity_matches_across_systems` is `TRUE` for all 800 rows — proof that the noisy
    free-text name always resolves back to the same canonical supplier as the structured code.
  - `on_time_flag` encodes the **ONE governance decision**: actual date = plant-dock receipt
    (`shipments.actual_receipt_date`), not the TMS carrier-buffered `first_delivery_attempt_date`
    and not the ERP ship date. Cancelled orders count as late (`0`), never dropped. Shipments
    still `IN_TRANSIT` past their `planned_receipt_date` also count as late (`0`) — the genuine
    "drops in-transit/currently-late shipments" flaw the Supplier Portal legacy query has. Only
    shipments still in-transit and **not yet** past their planned date are excluded (delivery
    hasn't concluded yet, so it can't be judged).
  - `has_iot_tracking` is `FALSE` for ~30% of rows — the IoT system's genuine 70% sensor
    coverage gap, carried through rather than hidden.

## Validated results (last run)

| Check | Result |
|---|---|
| `shipment_crosswalk` rows | 800 (100% of orders matched to a delivery and a shipment) |
| IoT tracking match rate | 560 / 800 = 70.0% (matches the plan's ~70% sensor coverage target) |
| Supplier identity cross-system match | 800 / 800 = 100% |
| CANONICAL on-time delivery rate | 64.9% |
| CANONICAL customer fill rate | 93.0% |
| Supplier-facing PO fill rate | 86.3% |
| Warehouse unit-level fill rate | 87.7% |

The three fill-rate numbers are genuinely different measures (order-binary customer-facing vs.
unit-level supplier-facing vs. continuous warehouse-level) — this is the plan's point: Silver
doesn't collapse them into one number, it makes each one canonical and separately queryable.
