-- SOURCE_ERP — genuine flaw: excludes cancelled/backorder rows from OTD denominator (inflates OTD)
USE ROLE SUPPLY_CHAIN_ADMIN;
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SOURCE_ERP
    COMMENT = 'Fragmented raw ERP system-of-record for purchase orders and demand forecasts. Phase 0 (pre-governance) — do not query directly for reporting; use SEMANTIC_MODELS once available.';

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_ERP.orders (
    erp_order_number VARCHAR(50) COMMENT 'ERP natural key, format ERP-nnnnnn. Correlates 1:1 by row index with SOURCE_LOGISTICS_TMS.deliveries.pro_number and SOURCE_SUPPLIER_PORTAL.shipments.asn_number for the same physical shipment.',
    supplier_code VARCHAR(50) COMMENT 'ERP-internal supplier identifier, format SUP-nnnn.',
    part_sku VARCHAR(50) COMMENT 'ERP-internal part identifier, format PART-nnnnn.',
    requested_ship_date DATE COMMENT 'Date the order was requested to ship — the true, unbuffered reference date.',
    actual_ship_date DATE COMMENT 'Date the order actually shipped. NULL for CANCELLED/BACKORDER rows.',
    order_status VARCHAR(30) COMMENT 'COMPLETE / CANCELLED / BACKORDER.',
    quantity NUMBER COMMENT 'Units ordered.',
    load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() COMMENT 'Row load time.'
)
COMMENT = 'KNOWN DATA QUALITY ISSUE: legacy OTD query filters WHERE order_status = ''COMPLETE'', excluding cancelled/backorder rows from the denominator entirely — this inflates ERP-reported OTD% vs. the true rate. Resolved in Phase 2 Silver by counting backorders as late, not dropping them.';

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_ERP.demand_forecast (
    part_sku VARCHAR(50) COMMENT 'ERP-internal part identifier, joins to orders.part_sku.',
    forecast_month DATE COMMENT 'First day of the forecasted month.',
    forecasted_daily_demand NUMBER COMMENT 'Planning-team forecasted average daily demand (units) — optimism-bias risk vs. Finance/Warehouse actuals.'
)
COMMENT = 'Planning-team demand forecast. Feeds the "Days of Inventory" (DOI) methodology divergence: forecast-based (this table) vs. Finance COGS-based vs. Warehouse trailing-actuals — resolved canonically in Phase 4 semantic view.';

-- ── Synthetic data: ~800 orders correlated (by row index) with the other 3 sources.
-- Target: ERP OTD ~90% among COMPLETE rows (cancelled/backorder excluded — the bug itself).
INSERT INTO SUPPLY_CHAIN.SOURCE_ERP.orders (erp_order_number, supplier_code, part_sku, requested_ship_date, actual_ship_date, order_status, quantity)
WITH base AS (
  SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT=>800))
),
attrs AS (
  SELECT
    i,
    'ERP-' || LPAD(i,6,'0') AS erp_order_number,
    'SUP-' || LPAD(1+MOD(i,50),4,'0') AS supplier_code,
    'PART-' || LPAD(1+MOD(i,100),5,'0') AS part_sku,
    DATEADD(day, -MOD(i,180), CURRENT_DATE()) AS requested_ship_date,
    UNIFORM(0::FLOAT,1::FLOAT,RANDOM()) AS status_roll,
    UNIFORM(0::FLOAT,1::FLOAT,RANDOM()) AS ontime_roll,
    UNIFORM(1,5,RANDOM()) AS late_days,
    UNIFORM(10,500,RANDOM()) AS quantity
  FROM base
)
SELECT
  erp_order_number, supplier_code, part_sku, requested_ship_date,
  CASE
    WHEN status_roll < 0.85 AND ontime_roll < 0.90 THEN requested_ship_date
    WHEN status_roll < 0.85 THEN DATEADD(day, late_days, requested_ship_date)
    ELSE NULL
  END AS actual_ship_date,
  CASE WHEN status_roll < 0.85 THEN 'COMPLETE'
       WHEN status_roll < 0.95 THEN 'CANCELLED'
       ELSE 'BACKORDER' END AS order_status,
  quantity
FROM attrs;

-- Demand forecast: 100 parts x 6 months — feeds DOI (Planning methodology) divergence in Phase 3-4.
INSERT INTO SUPPLY_CHAIN.SOURCE_ERP.demand_forecast (part_sku, forecast_month, forecasted_daily_demand)
WITH parts AS (
  SELECT 'PART-' || LPAD(SEQ4()+1,5,'0') AS part_sku FROM TABLE(GENERATOR(ROWCOUNT=>100))
),
months AS (
  SELECT DATE_TRUNC(month, DATEADD(month, -SEQ4(), CURRENT_DATE())) AS forecast_month FROM TABLE(GENERATOR(ROWCOUNT=>6))
)
SELECT part_sku, forecast_month, UNIFORM(5,200,RANDOM()) AS forecasted_daily_demand
FROM parts CROSS JOIN months;

-- Legacy query — OTD as Planning/ERP sees it (excludes cancelled/backorder → inflated)
-- SELECT ROUND(SUM(CASE WHEN actual_ship_date <= requested_ship_date THEN 1 ELSE 0 END)
--        / NULLIF(COUNT(*),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_ERP.orders WHERE order_status = 'COMPLETE';
