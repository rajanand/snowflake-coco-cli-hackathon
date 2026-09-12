-- =============================================================================
-- Phase 3: Gold Layer — dimensional model (Dynamic Tables)
-- =============================================================================
-- Star schema over Silver: dim_supplier (SCD2-shaped), dim_part, dim_plant,
-- dim_customer, dim_date; fact_shipment, fact_order_fulfillment,
-- fact_inventory_snapshot, fact_quality_event; bridge_supplier_part;
-- agg_supplier_performance. This is what the Phase 4 native SEMANTIC VIEW is
-- built on top of.
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;

CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.GOLD
    COMMENT = 'Phase 3: dimensional model. Dynamic Tables (TARGET_LAG=10 MINUTES) -- dim_supplier (SCD2-shaped), dim_part, dim_plant, dim_customer, dim_date; fact_shipment, fact_order_fulfillment, fact_inventory_snapshot, fact_quality_event; bridge_supplier_part; agg_supplier_performance (pre-aggregated, TARGET_LAG=15 MINUTES). This is what the Phase 4 native SEMANTIC VIEW is built on top of.';

ALTER SCHEMA SUPPLY_CHAIN.GOLD SET TAG SUPPLY_CHAIN.GOVERNANCE.LIFECYCLE = 'CANONICAL_GOLD';

USE SCHEMA SUPPLY_CHAIN.GOLD;

-- -----------------------------------------------------------------------------
-- Dimensions
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE dim_supplier
    TARGET_LAG = '10 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Supplier dimension, SCD2-shaped (valid_from/valid_to/is_current) for future change tracking. All current rows are open-ended (valid_to=NULL, is_current=TRUE) since Silver.suppliers recomputes attributes fresh each refresh in this demo -- the shape is ready for real history capture via a stream+task if supplier tier/region ever changes upstream.'
AS
SELECT
    HASH(supplier_id) AS supplier_key,
    supplier_id,
    supplier_name,
    tier_name,
    region,
    TRUE AS is_current,
    CURRENT_DATE() AS valid_from,
    NULL::DATE AS valid_to
FROM SUPPLY_CHAIN.SILVER.suppliers;

CREATE OR REPLACE DYNAMIC TABLE dim_part
    TARGET_LAG = '10 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Part dimension.'
AS
SELECT
    HASH(part_id) AS part_key,
    part_id,
    part_name,
    category,
    unit_cost,
    uom
FROM SUPPLY_CHAIN.SILVER.parts;

CREATE OR REPLACE DYNAMIC TABLE dim_plant
    TARGET_LAG = '10 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Plant/facility dimension.'
AS
SELECT
    HASH(plant_id) AS plant_key,
    plant_id,
    plant_name,
    region,
    plant_type
FROM SUPPLY_CHAIN.SILVER.plants;

CREATE OR REPLACE DYNAMIC TABLE dim_customer
    TARGET_LAG = '10 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Customer dimension.'
AS
SELECT
    HASH(customer_id) AS customer_key,
    customer_id,
    customer_name,
    customer_segment,
    region
FROM SUPPLY_CHAIN.SILVER.customers;

CREATE OR REPLACE TABLE dim_date
    COMMENT = 'Date dimension / calendar spine (Date->Week->Month->Quarter->Year hierarchy). Static table, not a Dynamic Table -- calendar days don''t need incremental refresh.'
AS
WITH d AS (
    SELECT DATEADD(day, SEQ4(), '2025-01-01'::DATE) AS date_day
    FROM TABLE(GENERATOR(ROWCOUNT => 1095))
)
SELECT
    date_day,
    YEAR(date_day) AS year,
    QUARTER(date_day) AS quarter,
    MONTH(date_day) AS month,
    MONTHNAME(date_day) AS month_name,
    WEEKOFYEAR(date_day) AS week_of_year,
    DAYOFWEEK(date_day) AS day_of_week,
    DAYNAME(date_day) AS day_name,
    IFF(DAYOFWEEK(date_day) IN (0,6), TRUE, FALSE) AS is_weekend
FROM d;

-- -----------------------------------------------------------------------------
-- Facts
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE fact_shipment
    TARGET_LAG = '10 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'CANONICAL shipment fact. One row per resolved shipment (SILVER.shipment_crosswalk). is_on_time is the single governance-approved OTD measure -- backs SEMANTIC_MODELS on_time_delivery_rate. value_usd approximates shipment value from part unit_cost x order_quantity for the landed_cost_per_unit metric.'
AS
SELECT
    cw.canonical_shipment_id AS shipment_id,
    sup.supplier_key,
    cw.resolved_supplier_id AS supplier_id,
    p.part_key,
    cw.resolved_part_id AS part_id,
    pl.plant_key,
    cw.resolved_plant_id AS plant_id,
    cw.erp_order_number,
    cw.pro_number,
    cw.asn_number,
    cw.requested_ship_date,
    cw.actual_ship_date,
    cw.promised_delivery_date,
    cw.planned_receipt_date,
    cw.actual_receipt_date,
    cw.order_status,
    cw.shipment_status,
    cw.order_quantity,
    cw.has_iot_tracking,
    cw.on_time_flag AS is_on_time,
    ROUND(p.unit_cost * cw.order_quantity, 2) AS value_usd
FROM SUPPLY_CHAIN.SILVER.shipment_crosswalk cw
LEFT JOIN dim_supplier sup ON sup.supplier_id = cw.resolved_supplier_id
LEFT JOIN dim_part p ON p.part_id = cw.resolved_part_id
LEFT JOIN dim_plant pl ON pl.plant_id = cw.resolved_plant_id;

CREATE OR REPLACE DYNAMIC TABLE fact_order_fulfillment
    TARGET_LAG = '10 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'CANONICAL customer order fulfillment fact. One row per customer order (SILVER.customer_orders). Backs SEMANTIC_MODELS customer_fill_rate. This is the CustomerOrder->Part join path enabling at-risk-order queries in Phase 4-5.'
AS
SELECT
    co.customer_order_id,
    cust.customer_key,
    co.customer_id,
    p.part_key,
    co.part_id,
    co.order_date,
    co.requested_delivery_date,
    co.actual_delivery_date,
    co.qty_ordered,
    co.qty_shipped,
    co.order_status,
    co.on_time_flag,
    co.fill_flag
FROM SUPPLY_CHAIN.SILVER.customer_orders co
LEFT JOIN dim_customer cust ON cust.customer_id = co.customer_id
LEFT JOIN dim_part p ON p.part_id = co.part_id;

CREATE OR REPLACE DYNAMIC TABLE fact_inventory_snapshot
    TARGET_LAG = '10 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'CANONICAL part-plant-day inventory fact. Backs SEMANTIC_MODELS days_of_inventory using the Warehouse (30-day trailing ACTUAL demand) methodology -- not forecast, not $-based -- per governance decision. current_stock/inventory_value provided for the legacy DOI-Planning/DOI-Finance comparison queries in the Before tab.'
AS
SELECT
    inv.snapshot_id,
    pl.plant_key,
    inv.plant_id,
    p.part_key,
    inv.part_id,
    inv.snapshot_date,
    inv.on_hand_qty AS current_stock,
    inv.safety_stock_qty,
    inv.avg_daily_usage_qty AS trailing_30d_avg_actual_demand,
    ROUND(inv.on_hand_qty * p.unit_cost, 2) AS inventory_value,
    ROUND(inv.on_hand_qty / NULLIF(inv.avg_daily_usage_qty, 0), 1) AS days_of_inventory
FROM SUPPLY_CHAIN.SILVER.inventory_snapshots inv
LEFT JOIN dim_plant pl ON pl.plant_id = inv.plant_id
LEFT JOIN dim_part p ON p.part_id = inv.part_id;

CREATE OR REPLACE DYNAMIC TABLE fact_quality_event
    TARGET_LAG = '10 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'CANONICAL supplier quality defect event fact.'
AS
SELECT
    qe.quality_event_id,
    sup.supplier_key,
    qe.supplier_id,
    p.part_key,
    qe.part_id,
    pl.plant_key,
    qe.plant_id,
    qe.event_date,
    qe.defect_type,
    qe.severity,
    qe.qty_affected,
    qe.disposition
FROM SUPPLY_CHAIN.SILVER.quality_events qe
LEFT JOIN dim_supplier sup ON sup.supplier_id = qe.supplier_id
LEFT JOIN dim_part p ON p.part_id = qe.part_id
LEFT JOIN dim_plant pl ON pl.plant_id = qe.plant_id;

-- -----------------------------------------------------------------------------
-- Bridge + pre-aggregated scorecard
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE bridge_supplier_part
    TARGET_LAG = '10 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Many-to-many Supplier<->Part bridge, derived from observed shipments. relationship_shipment_count supports weighting/filtering in the semantic view.'
AS
SELECT
    sup.supplier_key,
    fs.supplier_id,
    p.part_key,
    fs.part_id,
    COUNT(*) AS relationship_shipment_count,
    MIN(fs.actual_ship_date) AS first_observed_date,
    MAX(fs.actual_ship_date) AS last_observed_date
FROM SUPPLY_CHAIN.GOLD.fact_shipment fs
LEFT JOIN dim_supplier sup ON sup.supplier_id = fs.supplier_id
LEFT JOIN dim_part p ON p.part_id = fs.part_id
GROUP BY sup.supplier_key, fs.supplier_id, p.part_key, fs.part_id;

CREATE OR REPLACE DYNAMIC TABLE agg_supplier_performance
    TARGET_LAG = '15 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Pre-aggregated supplier scorecard: on-time delivery rate, quality defect rate, shipment volume/value. One row per supplier. Powers fast supplier-performance dashboards without re-scanning fact_shipment/fact_quality_event at query time.'
AS
SELECT
    sup.supplier_key,
    sup.supplier_id,
    sup.supplier_name,
    sup.tier_name,
    sup.region,
    COUNT(fs.shipment_id) AS total_shipments,
    ROUND(AVG(fs.is_on_time) * 100, 1) AS on_time_delivery_rate,
    SUM(fs.value_usd) AS total_shipment_value_usd,
    COUNT(DISTINCT bsp.part_id) AS distinct_parts_supplied,
    COALESCE(qe.total_quality_events, 0) AS total_quality_events,
    ROUND(COALESCE(qe.total_quality_events, 0) / NULLIF(COUNT(fs.shipment_id), 0) * 100, 2) AS quality_defect_rate_pct
FROM dim_supplier sup
LEFT JOIN fact_shipment fs ON fs.supplier_key = sup.supplier_key
LEFT JOIN bridge_supplier_part bsp ON bsp.supplier_key = sup.supplier_key
LEFT JOIN (
    SELECT supplier_key, COUNT(*) AS total_quality_events
    FROM fact_quality_event
    GROUP BY supplier_key
) qe ON qe.supplier_key = sup.supplier_key
GROUP BY sup.supplier_key, sup.supplier_id, sup.supplier_name, sup.tier_name, sup.region, qe.total_quality_events;
