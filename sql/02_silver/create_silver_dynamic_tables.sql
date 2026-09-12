-- =============================================================================
-- Phase 2: Silver Layer — canonical/conformed layer (Dynamic Tables)
-- =============================================================================
-- Every Silver Dynamic Table flattens a Bronze VARIANT payload, type-casts,
-- and deduplicates via QUALIFY ROW_NUMBER()...=1. TARGET_LAG = '5 MINUTES'.
--
-- IMPORTANT VARIANT key-casing note: the 11 tables ingested from Phase 0
-- SOURCE_* systems via OBJECT_CONSTRUCT(*) have UPPERCASE keys (Snowflake's
-- default unquoted identifier case) -- e.g. raw_payload:ERP_ORDER_NUMBER.
-- The 6 net-new tables generated directly into Bronze use explicit lowercase
-- keys -- e.g. raw_payload:part_id. Both are correct; VARIANT path notation
-- is case-sensitive, so each Silver table below matches whichever casing its
-- Bronze source actually used.
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;

CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SILVER
    COMMENT = 'Phase 2: canonical/conformed layer. Dynamic Tables that flatten Bronze VARIANT payloads, type-cast, deduplicate, resolve cross-system entity identity (shipment_crosswalk), and apply the ONE governance-approved definition of on_time_flag (plant-dock receipt vs. planned receipt date; backorders count as late, not dropped; no artificial carrier buffers).';

ALTER SCHEMA SUPPLY_CHAIN.SILVER SET TAG SUPPLY_CHAIN.GOVERNANCE.LIFECYCLE = 'CANONICAL_SILVER';

USE SCHEMA SUPPLY_CHAIN.SILVER;

-- -----------------------------------------------------------------------------
-- Master data dimensions
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE parts
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical parts dimension. Flattened, deduplicated from BRONZE.parts.'
AS
SELECT
    raw_payload:part_id::VARCHAR AS part_id,
    raw_payload:part_name::VARCHAR AS part_name,
    raw_payload:category::VARCHAR AS category,
    raw_payload:unit_cost::NUMBER(10,2) AS unit_cost,
    raw_payload:uom::VARCHAR AS uom
FROM SUPPLY_CHAIN.BRONZE.parts
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:part_id::VARCHAR ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE plants
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical plants/facilities dimension. Flattened, deduplicated from BRONZE.plants.'
AS
SELECT
    raw_payload:plant_id::VARCHAR AS plant_id,
    raw_payload:plant_name::VARCHAR AS plant_name,
    raw_payload:region::VARCHAR AS region,
    raw_payload:plant_type::VARCHAR AS plant_type
FROM SUPPLY_CHAIN.BRONZE.plants
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:plant_id::VARCHAR ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE customers
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical customers dimension. Flattened, deduplicated from BRONZE.customers.'
AS
SELECT
    raw_payload:customer_id::VARCHAR AS customer_id,
    raw_payload:customer_name::VARCHAR AS customer_name,
    raw_payload:segment::VARCHAR AS customer_segment,
    raw_payload:region::VARCHAR AS region
FROM SUPPLY_CHAIN.BRONZE.customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:customer_id::VARCHAR ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE suppliers
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical suppliers dimension. No master data source exists (genuine gap) -- resolved from the set of distinct supplier_code values referenced in BRONZE.orders (SOURCE_ERP is treated as the system of record for supplier identity), enriched with deterministic tier/region since no source carries them. shipment_crosswalk separately proves that TMS free-text supplier names (e.g. "Supplier-002 Corp.") resolve back to the same canonical supplier_id via regex-normalized entity resolution.'
AS
WITH distinct_suppliers AS (
    SELECT DISTINCT raw_payload:SUPPLIER_CODE::VARCHAR AS supplier_id
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
    COMMENT = 'Canonical customer order fulfillment. Flattened from BRONZE.customer_orders (net-new, lowercase VARIANT keys). on_time_flag: actual_delivery_date <= requested_delivery_date. fill_flag: qty_shipped >= qty_ordered (CANONICAL customer-facing fill rate -- distinct from supplier-facing PO fill and warehouse unit-level fill).'
AS
SELECT
    raw_payload:customer_order_id::VARCHAR AS customer_order_id,
    raw_payload:customer_id::VARCHAR AS customer_id,
    raw_payload:part_id::VARCHAR AS part_id,
    raw_payload:order_date::DATE AS order_date,
    raw_payload:requested_delivery_date::DATE AS requested_delivery_date,
    raw_payload:actual_delivery_date::DATE AS actual_delivery_date,
    raw_payload:qty_ordered::NUMBER AS qty_ordered,
    raw_payload:qty_shipped::NUMBER AS qty_shipped,
    raw_payload:order_status::VARCHAR AS order_status,
    IFF(raw_payload:actual_delivery_date::DATE <= raw_payload:requested_delivery_date::DATE, 1, 0) AS on_time_flag,
    IFF(raw_payload:qty_shipped::NUMBER >= raw_payload:qty_ordered::NUMBER, 1, 0) AS fill_flag
FROM SUPPLY_CHAIN.BRONZE.customer_orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:customer_order_id::VARCHAR ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE purchase_orders
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical supplier-facing purchase orders. Flattened from BRONZE.purchase_orders (SOURCE_SUPPLIER_PORTAL, uppercase VARIANT keys). Feeds CANONICAL supplier_fill_rate = SUM(qty_received)/SUM(qty_ordered) -- deliberately a different measure from customer_order.fill_flag.'
AS
SELECT
    raw_payload:PO_NUMBER::VARCHAR AS po_number,
    raw_payload:SUPPLIER_ID_PORTAL::VARCHAR AS supplier_id,
    raw_payload:PART_NUMBER_PORTAL::VARCHAR AS part_id,
    raw_payload:QTY_ORDERED::NUMBER AS qty_ordered,
    raw_payload:QTY_RECEIVED::NUMBER AS qty_received,
    raw_payload:PO_STATUS::VARCHAR AS po_status
FROM SUPPLY_CHAIN.BRONZE.purchase_orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:PO_NUMBER::VARCHAR ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE pick_operations
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical warehouse pick operations. Flattened from BRONZE.pick_operations (SOURCE_LOGISTICS_TMS, uppercase VARIANT keys). Feeds unit-level warehouse fill rate = SUM(units_picked)/SUM(units_ordered) -- continuous, not order-binary; a third distinct fill-rate concept alongside customer_order.fill_flag and purchase_orders supplier fill.'
AS
SELECT
    raw_payload:PICK_ID::VARCHAR AS pick_id,
    raw_payload:CUSTOMER_ORDER_REF::VARCHAR AS customer_order_ref,
    raw_payload:UNITS_ORDERED::NUMBER AS units_ordered,
    raw_payload:UNITS_PICKED::NUMBER AS units_picked
FROM SUPPLY_CHAIN.BRONZE.pick_operations
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:PICK_ID::VARCHAR ORDER BY load_timestamp DESC) = 1;

-- -----------------------------------------------------------------------------
-- DOI feeds (3 deliberately distinct methodologies)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE demand_forecast
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical demand forecast (Planning methodology). Flattened from BRONZE.demand_forecast (SOURCE_ERP, uppercase VARIANT keys). Feeds DOI-Planning = current_stock / forecasted_daily_demand -- deliberately forecast-based (optimism-bias risk), distinct from Finance (COGS-based) and Warehouse (trailing-actuals) DOI methodologies.'
AS
SELECT
    raw_payload:PART_SKU::VARCHAR AS part_id,
    raw_payload:FORECAST_MONTH::DATE AS forecast_month,
    raw_payload:FORECASTED_DAILY_DEMAND::NUMBER AS forecasted_daily_demand
FROM SUPPLY_CHAIN.BRONZE.demand_forecast
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:PART_SKU::VARCHAR, raw_payload:FORECAST_MONTH::DATE ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE daily_cogs
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical daily cost-of-goods-sold (Finance methodology). Flattened from BRONZE.daily_cogs (SOURCE_FINANCE, uppercase VARIANT keys). Feeds DOI-Finance = inventory_value / daily_cogs -- deliberately dollar-based, not unit-based.'
AS
SELECT
    raw_payload:PART_ID::VARCHAR AS part_id,
    raw_payload:COGS_DATE::DATE AS cogs_date,
    raw_payload:DAILY_COGS::NUMBER AS daily_cogs
FROM SUPPLY_CHAIN.BRONZE.daily_cogs
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:PART_ID::VARCHAR, raw_payload:COGS_DATE::DATE ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE inventory_snapshots
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical part-plant-day inventory snapshots. Flattened from BRONZE.inventory_snapshots (net-new, lowercase VARIANT keys). Feeds DOI-Warehouse = on_hand_qty / trailing-30d-avg-actual-demand (avg_daily_usage_qty here) -- deliberately actuals-based, not forecast, not $-based; the CANONICAL DOI methodology per governance.'
AS
SELECT
    raw_payload:snapshot_id::VARCHAR AS snapshot_id,
    raw_payload:plant_id::VARCHAR AS plant_id,
    raw_payload:part_id::VARCHAR AS part_id,
    raw_payload:snapshot_date::DATE AS snapshot_date,
    raw_payload:on_hand_qty::NUMBER AS on_hand_qty,
    raw_payload:safety_stock_qty::NUMBER AS safety_stock_qty,
    raw_payload:avg_daily_usage_qty::NUMBER AS avg_daily_usage_qty
FROM SUPPLY_CHAIN.BRONZE.inventory_snapshots
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:snapshot_id::VARCHAR ORDER BY load_timestamp DESC) = 1;

-- -----------------------------------------------------------------------------
-- Landed Cost feeds (3 deliberately incomplete cost-assembly views)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE freight_invoices
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical freight invoices (Logistics landed-cost methodology). Flattened from BRONZE.freight_invoices (SOURCE_LOGISTICS_TMS, uppercase VARIANT keys). Feeds LandedCost-Logistics = freight_cost + customs_duty per shipment -- deliberately per-shipment not per-unit, no purchase price included.'
AS
SELECT
    raw_payload:INVOICE_NUMBER::VARCHAR AS invoice_number,
    raw_payload:PRO_NUMBER::VARCHAR AS pro_number,
    raw_payload:FREIGHT_COST::NUMBER AS freight_cost,
    raw_payload:CUSTOMS_DUTY::NUMBER AS customs_duty,
    raw_payload:INVOICE_DATE::DATE AS invoice_date
FROM SUPPLY_CHAIN.BRONZE.freight_invoices
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:INVOICE_NUMBER::VARCHAR ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE overhead_allocation
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical overhead allocation by part category/month (Finance full-stack landed-cost methodology). Flattened from BRONZE.overhead_allocation (SOURCE_FINANCE, uppercase VARIANT keys). Feeds LandedCost-Finance = unit_cost + freight + customs + overhead -- the full-stack view, ~1 month stale.'
AS
SELECT
    raw_payload:PART_CATEGORY::VARCHAR AS part_category,
    raw_payload:MONTH::DATE AS month,
    raw_payload:ALLOCATED_OVERHEAD_PER_UNIT::NUMBER AS allocated_overhead_per_unit
FROM SUPPLY_CHAIN.BRONZE.overhead_allocation
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:PART_CATEGORY::VARCHAR, raw_payload:MONTH::DATE ORDER BY load_timestamp DESC) = 1;

CREATE OR REPLACE DYNAMIC TABLE freight_quotes
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical procurement freight quotes (Procurement landed-cost methodology). Flattened from BRONZE.freight_quotes (SOURCE_SUPPLIER_PORTAL, uppercase VARIANT keys). Feeds LandedCost-Procurement = unit_cost + quoted_freight_estimate -- deliberately understates true cost (no customs/overhead).'
AS
SELECT
    raw_payload:PART_ID::VARCHAR AS part_id,
    raw_payload:FREIGHT_ESTIMATE::NUMBER AS freight_estimate
FROM SUPPLY_CHAIN.BRONZE.freight_quotes
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:PART_ID::VARCHAR ORDER BY load_timestamp DESC) = 1;

-- -----------------------------------------------------------------------------
-- Quality
-- -----------------------------------------------------------------------------

CREATE OR REPLACE DYNAMIC TABLE quality_events
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'Canonical supplier quality defect events. Flattened from BRONZE.quality_events (net-new, lowercase VARIANT keys).'
AS
SELECT
    raw_payload:quality_event_id::VARCHAR AS quality_event_id,
    raw_payload:part_id::VARCHAR AS part_id,
    raw_payload:supplier_id::VARCHAR AS supplier_id,
    raw_payload:plant_id::VARCHAR AS plant_id,
    raw_payload:event_date::DATE AS event_date,
    raw_payload:defect_type::VARCHAR AS defect_type,
    raw_payload:severity::VARCHAR AS severity,
    raw_payload:qty_affected::NUMBER AS qty_affected,
    raw_payload:disposition::VARCHAR AS disposition
FROM SUPPLY_CHAIN.BRONZE.quality_events
QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:quality_event_id::VARCHAR ORDER BY load_timestamp DESC) = 1;
