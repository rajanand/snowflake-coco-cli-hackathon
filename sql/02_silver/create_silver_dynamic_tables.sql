-- =============================================================================
-- Phase 2: Silver Layer — canonical/conformed layer (Dynamic Tables)
-- =============================================================================
-- Every Silver Dynamic Table reads from Bronze, type-casts where needed, and
-- deduplicates via QUALIFY ROW_NUMBER()...=1. TARGET_LAG = '5 MINUTES'.
--
-- Bronze tables now use typed columns (not VARIANT payloads) for all structured
-- sources — Silver reads them directly. Only tracking_events retains a VARIANT
-- EVENT_PAYLOAD for genuinely semi-structured IoT sensor JSON, and that
-- extraction happens in shipment_crosswalk.sql.
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;

CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SILVER
    COMMENT = 'Phase 2: canonical/conformed layer. Dynamic Tables that deduplicate Bronze typed columns, resolve cross-system entity identity (shipment_crosswalk), and apply the ONE governance-approved definition of on_time_flag (plant-dock receipt vs. planned receipt date; backorders count as late, not dropped; no artificial carrier buffers).';

ALTER SCHEMA SUPPLY_CHAIN.SILVER SET TAG SUPPLY_CHAIN.GOVERNANCE.LIFECYCLE = 'CANONICAL_SILVER';

USE SCHEMA SUPPLY_CHAIN.SILVER;

-- -----------------------------------------------------------------------------
-- Master data dimensions
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE parts
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical parts dimension. Deduplicated from BRONZE.parts.'
AS
SELECT
    part_id,
    part_name,
    category,
    unit_cost,
    uom
FROM SUPPLY_CHAIN.BRONZE.parts
QUALIFY ROW_NUMBER() OVER (PARTITION BY part_id ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE plants
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical plants/facilities dimension. Deduplicated from BRONZE.plants.'
AS
SELECT
    plant_id,
    plant_name,
    region,
    plant_type
FROM SUPPLY_CHAIN.BRONZE.plants
QUALIFY ROW_NUMBER() OVER (PARTITION BY plant_id ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE customers
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical customers dimension. Deduplicated from BRONZE.customers.'
AS
SELECT
    customer_id,
    customer_name,
    segment AS customer_segment,
    region
FROM SUPPLY_CHAIN.BRONZE.customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE suppliers
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical suppliers dimension. No master data source exists (genuine gap) -- resolved from the set of distinct supplier_code values referenced in BRONZE.orders (SOURCE_ERP is treated as the system of record for supplier identity), enriched with deterministic tier/region since no source carries them. shipment_crosswalk separately proves that TMS free-text supplier names (e.g. "Supplier-002 Corp.") resolve back to the same canonical supplier_id via regex-normalized entity resolution.'
AS
WITH distinct_suppliers AS (
    SELECT DISTINCT supplier_code AS supplier_id
    FROM SUPPLY_CHAIN.BRONZE.orders
)
SELECT
    supplier_id,
    'Supplier ' || REGEXP_SUBSTR(supplier_id, '[0-9]+') AS supplier_name,
    CASE
        WHEN MOD(REGEXP_SUBSTR(supplier_id, '[0-9]+')::INT, 5) = 0 THEN 'TIER_1_STRATEGIC'
        WHEN MOD(REGEXP_SUBSTR(supplier_id, '[0-9]+')::INT, 3) = 0 THEN 'TIER_2_PREFERRED'
        ELSE 'TIER_3_STANDARD'
    END AS tier_name,
    CASE MOD(REGEXP_SUBSTR(supplier_id, '[0-9]+')::INT, 4)
        WHEN 0 THEN 'NORTH_AMERICA'
        WHEN 1 THEN 'EMEA'
        WHEN 2 THEN 'APAC'
        ELSE 'LATAM'
    END AS region
FROM distinct_suppliers;

-- -----------------------------------------------------------------------------
-- shipment_crosswalk -- see shipment_crosswalk.sql (the entity-resolution
-- centerpiece; kept in its own file per the plan's repo structure)
-- -----------------------------------------------------------------------------

-- -----------------------------------------------------------------------------
-- Fill Rate feeds (3 deliberately distinct concepts)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE customer_orders
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical customer order fulfillment. Deduplicated from BRONZE.customer_orders. on_time_flag: actual_delivery_date <= requested_delivery_date. fill_flag: qty_shipped >= qty_ordered (CANONICAL customer-facing fill rate -- distinct from supplier-facing PO fill and warehouse unit-level fill).'
AS
SELECT
    customer_order_id,
    customer_id,
    part_id,
    order_date,
    requested_delivery_date,
    actual_delivery_date,
    qty_ordered,
    qty_shipped,
    order_status,
    IFF(actual_delivery_date <= requested_delivery_date, 1, 0) AS on_time_flag,
    IFF(qty_shipped >= qty_ordered, 1, 0) AS fill_flag
FROM SUPPLY_CHAIN.BRONZE.customer_orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_order_id ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE purchase_orders
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical supplier-facing purchase orders. Deduplicated from BRONZE.purchase_orders (SOURCE_SUPPLIER_PORTAL). Feeds CANONICAL supplier_fill_rate = SUM(qty_received)/SUM(qty_ordered) -- deliberately a different measure from customer_order.fill_flag.'
AS
SELECT
    po_number,
    supplier_id_portal AS supplier_id,
    part_number_portal AS part_id,
    qty_ordered,
    qty_received,
    po_status
FROM SUPPLY_CHAIN.BRONZE.purchase_orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY po_number ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE pick_operations
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical warehouse pick operations. Deduplicated from BRONZE.pick_operations (SOURCE_LOGISTICS_TMS). Feeds unit-level warehouse fill rate = SUM(units_picked)/SUM(units_ordered) -- continuous, not order-binary; a third distinct fill-rate concept alongside customer_order.fill_flag and purchase_orders supplier fill.'
AS
SELECT
    pick_id,
    customer_order_ref,
    units_ordered,
    units_picked
FROM SUPPLY_CHAIN.BRONZE.pick_operations
QUALIFY ROW_NUMBER() OVER (PARTITION BY pick_id ORDER BY load_timestamp DESC) = 1;

-- -----------------------------------------------------------------------------
-- DOI feeds (3 deliberately distinct methodologies)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE demand_forecast
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical demand forecast (Planning methodology). Deduplicated from BRONZE.demand_forecast (SOURCE_ERP). Feeds DOI-Planning = current_stock / forecasted_daily_demand -- deliberately forecast-based (optimism-bias risk), distinct from Finance (COGS-based) and Warehouse (trailing-actuals) DOI methodologies.'
AS
SELECT
    part_sku AS part_id,
    forecast_month,
    forecasted_daily_demand
FROM SUPPLY_CHAIN.BRONZE.demand_forecast
QUALIFY ROW_NUMBER() OVER (PARTITION BY part_sku, forecast_month ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE daily_cogs
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical daily cost-of-goods-sold (Finance methodology). Deduplicated from BRONZE.daily_cogs (SOURCE_FINANCE). Feeds DOI-Finance = inventory_value / daily_cogs -- deliberately dollar-based, not unit-based.'
AS
SELECT
    part_id,
    cogs_date,
    daily_cogs
FROM SUPPLY_CHAIN.BRONZE.daily_cogs
QUALIFY ROW_NUMBER() OVER (PARTITION BY part_id, cogs_date ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE inventory_snapshots
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical part-plant-day inventory snapshots. Deduplicated from BRONZE.inventory_snapshots. Feeds DOI-Warehouse = on_hand_qty / trailing-30d-avg-actual-demand (avg_daily_usage_qty here) -- deliberately actuals-based, not forecast, not $-based; the CANONICAL DOI methodology per governance.'
AS
SELECT
    snapshot_id,
    plant_id,
    part_id,
    snapshot_date,
    on_hand_qty,
    safety_stock_qty,
    avg_daily_usage_qty
FROM SUPPLY_CHAIN.BRONZE.inventory_snapshots
QUALIFY ROW_NUMBER() OVER (PARTITION BY snapshot_id ORDER BY load_timestamp DESC) = 1;

-- -----------------------------------------------------------------------------
-- Landed Cost feeds (3 deliberately incomplete cost-assembly views)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE freight_invoices
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical freight invoices (Logistics landed-cost methodology). Deduplicated from BRONZE.freight_invoices (SOURCE_LOGISTICS_TMS). Feeds LandedCost-Logistics = freight_cost + customs_duty per shipment -- deliberately per-shipment not per-unit, no purchase price included.'
AS
SELECT
    invoice_number,
    pro_number,
    freight_cost,
    customs_duty,
    invoice_date
FROM SUPPLY_CHAIN.BRONZE.freight_invoices
QUALIFY ROW_NUMBER() OVER (PARTITION BY invoice_number ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE overhead_allocation
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical overhead allocation by part category/month (Finance full-stack landed-cost methodology). Deduplicated from BRONZE.overhead_allocation (SOURCE_FINANCE). Feeds LandedCost-Finance = unit_cost + freight + customs + overhead -- the full-stack view, ~1 month stale.'
AS
SELECT
    part_category,
    month,
    allocated_overhead_per_unit
FROM SUPPLY_CHAIN.BRONZE.overhead_allocation
QUALIFY ROW_NUMBER() OVER (PARTITION BY part_category, month ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE freight_quotes
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical procurement freight quotes (Procurement landed-cost methodology). Deduplicated from BRONZE.freight_quotes (SOURCE_SUPPLIER_PORTAL). Feeds LandedCost-Procurement = unit_cost + quoted_freight_estimate -- deliberately understates true cost (no customs/overhead).'
AS
SELECT
    part_id,
    freight_estimate
FROM SUPPLY_CHAIN.BRONZE.freight_quotes
QUALIFY ROW_NUMBER() OVER (PARTITION BY part_id ORDER BY load_timestamp DESC) = 1;

-- -----------------------------------------------------------------------------
-- Quality
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE quality_events
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical supplier quality defect events. Deduplicated from BRONZE.quality_events.'
AS
SELECT
    quality_event_id,
    part_id,
    supplier_id,
    plant_id,
    event_date,
    defect_type,
    severity,
    qty_affected,
    disposition
FROM SUPPLY_CHAIN.BRONZE.quality_events
QUALIFY ROW_NUMBER() OVER (PARTITION BY quality_event_id ORDER BY load_timestamp DESC) = 1;
