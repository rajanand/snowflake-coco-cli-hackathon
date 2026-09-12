# SQL — Phase 4: The Ontology, Encoded as a Governed Semantic View

Implements Phase 4 of `.snowflake/cortex/plans/supply-chain-ontology-revised.plan.md`.

Run `supply_chain_ontology_semantic_view.sql` — creates the `SEMANTIC_MODELS` schema and the
native `SUPPLY_CHAIN_ONTOLOGY` semantic view over the `GOLD` dimensional model (a real, directly
queryable Snowflake object, not YAML-only).

## Coverage

| Entity (TABLES) | Backing Gold table | Synonyms |
|---|---|---|
| `supplier` | `dim_supplier` | vendor, seller |
| `part` | `dim_part` | sku, material, component |
| `plant` | `dim_plant` | facility, warehouse, distribution center |
| `customer` | `dim_customer` | account, client |
| `shipment` | `fact_shipment` | delivery, inbound shipment |
| `customer_order` | `fact_order_fulfillment` | order, sales order |
| `purchase_order` | `fact_purchase_order` | po |
| `inventory_snapshot` | `fact_inventory_snapshot` | inventory, stock |
| `landed_cost` | `fact_landed_cost` | true cost detail |

10 `RELATIONSHIPS` connect every fact table back to its dimensions (and `landed_cost` back to
`shipment`). All 4 headline metrics from Phase 0 are exposed as `METRICS`, each with a `COMMENT`
documenting the governance decision:

| Metric | Formula | Governance decision |
|---|---|---|
| `shipment.on_time_delivery_rate` | on-time shipments / total shipments | plant-dock receipt date, not carrier-buffered TMS date or ERP ship date; cancelled/overdue-in-transit count as late |
| `customer_order.customer_fill_rate` | complete orders / total orders | order-binary (`qty_shipped >= qty_ordered`) |
| `purchase_order.supplier_fill_rate` | received units / ordered units | supplier-facing, deliberately distinct from customer fill rate |
| `inventory_snapshot.days_of_inventory` | on-hand qty / 30-day trailing actual demand | actuals-based, not forecast, not $-based |
| `landed_cost.landed_cost_per_unit` | unit_cost + freight + customs + overhead per unit | full-stack, computed at shipment grain |

## Important syntax note: alias direction

In `FACTS`/`DIMENSIONS` clauses, Snowflake's `CREATE SEMANTIC VIEW` syntax is
`<table>.<new_semantic_name> AS <physical_column>` — the **new** semantic name comes first, the
underlying physical column comes after `AS`. This is the *opposite* direction from a normal SQL
`SELECT ... AS alias` and is easy to get backwards (it will fail with
`invalid identifier '<new_name>'` if reversed). Confirmed empirically against a throwaway test
view before writing the real one.

## Validated results (last run)

Querying all 5 canonical metrics together in a single `SEMANTIC_VIEW()` call:

| Metric | Value |
|---|---|
| `on_time_delivery_rate` | 64.875% |
| `customer_fill_rate` | 93.000% |
| `supplier_fill_rate` | 86.294% |
| `days_of_inventory` | 49.16 days |
| `landed_cost_per_unit` | $286.60 |

`on_time_delivery_rate` matches `GOLD.fact_shipment`'s direct `AVG(is_on_time)*100` exactly
(519/800 = 64.875%), confirming no fan-out distortion from combining metrics whose fact tables
sit at different grains — every metric's fact table has a clean many-to-one path back through the
relationship graph.

Dimensional breakdown (`DIMENSIONS supplier.tier_name, supplier.supplier_region`) also validated
— 12 rows (3 tiers x 4 regions), each a sensible OTD% between ~52% and ~72%.

## Structural validation

`DESCRIBE SEMANTIC VIEW SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY` confirms 9 tables, 10
relationships, 5 metrics, 5 dimensions, and 4 facts are all correctly registered with their
synonyms and comments intact.
