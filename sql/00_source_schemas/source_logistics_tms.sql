-- SOURCE_LOGISTICS_TMS — genuine flaws:
--   1) 2-day carrier buffer baked into "promised date" (more lenient OTD)
--   2) free-text supplier names with spelling variants (entity-resolution problem for Silver crosswalk)
USE ROLE SUPPLY_CHAIN_ADMIN;
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS
    COMMENT = 'Fragmented raw Transportation Management System (carrier deliveries, warehouse picks, freight invoices). Phase 0 (pre-governance).';

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.deliveries (
    pro_number VARCHAR(50) COMMENT 'TMS natural key, format PRO-nnnnnn. Correlates 1:1 by row index with SOURCE_ERP.orders.erp_order_number for the same physical shipment.',
    carrier_name VARCHAR(100) COMMENT 'Freight carrier (FedEx Freight / UPS Freight / DHL Global).',
    origin_supplier_name VARCHAR(200) COMMENT 'KNOWN DATA QUALITY ISSUE: free-text supplier name entered by carrier ops — spelling variants (case, "Inc"/"Corp." suffixes) for the same supplier. Requires fuzzy EDITDISTANCE matching in the Phase 2 Silver crosswalk to resolve to a canonical supplier_id.',
    promised_delivery_date DATE COMMENT 'KNOWN DATA QUALITY ISSUE: computed as true requested-ship-date + a 2-day carrier buffer baked in by TMS, making TMS-reported OTD% more lenient than the true rate.',
    first_delivery_attempt_date DATE COMMENT 'Date of first delivery attempt — used (against the buffered promised_delivery_date) for TMS''s OTD calculation.',
    final_delivery_date DATE COMMENT 'Date of final successful delivery.',
    is_partial_shipment BOOLEAN COMMENT 'True if the shipment was split into a partial delivery.',
    load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() COMMENT 'Row load time.'
)
COMMENT = 'KNOWN DATA QUALITY ISSUE: OTD measured against promised_delivery_date, which already includes a 2-day carrier buffer — more lenient than the canonical plant-dock-receipt definition resolved in Phase 4.';

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.pick_operations (
    pick_id VARCHAR(50) COMMENT 'Warehouse pick operation natural key.',
    customer_order_ref VARCHAR(50) COMMENT 'Reference to the outbound customer order being picked.',
    units_ordered NUMBER COMMENT 'Units ordered for this pick.',
    units_picked NUMBER COMMENT 'Units actually picked — basis for Warehouse''s unit-level (continuous) fill rate, distinct from order-binary customer/supplier fill rate.'
)
COMMENT = 'Warehouse unit-level fill rate source. One of three genuinely different Fill Rate concepts (Customer-facing / Supplier-facing PO / Warehouse unit-level) resolved as distinct canonical metrics in Phase 4.';

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.freight_invoices (
    invoice_number VARCHAR(50) COMMENT 'Freight invoice natural key.',
    pro_number VARCHAR(50) COMMENT 'Joins to deliveries.pro_number. KNOWN DATA QUALITY ISSUE: only ~87.5% of pro_numbers have a matching invoice — a genuine 0-or-1 Shipment→Invoice relationship gap that fragments Landed Cost.',
    freight_cost NUMBER COMMENT 'Actual freight cost charged.',
    customs_duty NUMBER COMMENT 'Actual customs duty charged.',
    invoice_date DATE COMMENT 'Invoice date.'
)
COMMENT = 'Logistics-team Landed Cost input (actual freight+customs, no purchase price — per-shipment not per-unit). Feeds the incomplete-cost-assembly divergence vs. Procurement/Finance views.';

-- ── Synthetic data: ~800 deliveries correlated (by row index) with SOURCE_ERP.orders.
-- Target: TMS OTD ~93% (promised date = true requested date + 2-day buffer).
INSERT INTO SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.deliveries (pro_number, carrier_name, origin_supplier_name, promised_delivery_date, first_delivery_attempt_date, final_delivery_date, is_partial_shipment)
WITH base AS (
  SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT=>800))
),
attrs AS (
  SELECT
    i,
    'PRO-' || LPAD(i,6,'0') AS pro_number,
    CASE MOD(i,3) WHEN 0 THEN 'FedEx Freight' WHEN 1 THEN 'UPS Freight' ELSE 'DHL Global' END AS carrier_name,
    'Supplier-' || LPAD(1+MOD(i,50),3,'0') AS base_supplier_name,
    DATEADD(day, -MOD(i,180), CURRENT_DATE()) AS true_req_date,
    UNIFORM(0::FLOAT,1::FLOAT,RANDOM()) AS name_variant_roll,
    UNIFORM(0::FLOAT,1::FLOAT,RANDOM()) AS ontime_roll,
    UNIFORM(1,5,RANDOM()) AS late_days,
    UNIFORM(0::FLOAT,1::FLOAT,RANDOM()) AS partial_roll
  FROM base
),
attrs2 AS (
  SELECT *,
    DATEADD(day, 2, true_req_date) AS promised_delivery_date,
    -- free-text supplier name variants: same supplier, different spellings (fuel Silver EDITDISTANCE crosswalk)
    CASE
      WHEN name_variant_roll < 0.25 THEN base_supplier_name
      WHEN name_variant_roll < 0.5 THEN base_supplier_name || ' Inc'
      WHEN name_variant_roll < 0.75 THEN UPPER(base_supplier_name)
      ELSE base_supplier_name || ' Corp.'
    END AS origin_supplier_name
  FROM attrs
)
SELECT
  pro_number, carrier_name, origin_supplier_name, promised_delivery_date,
  CASE WHEN ontime_roll < 0.93 THEN promised_delivery_date ELSE DATEADD(day, late_days, promised_delivery_date) END AS first_delivery_attempt_date,
  CASE WHEN ontime_roll < 0.93 THEN promised_delivery_date ELSE DATEADD(day, late_days, promised_delivery_date) END AS final_delivery_date,
  partial_roll < 0.1 AS is_partial_shipment
FROM attrs2;

-- Warehouse pick operations — unit-level fill rate (continuous, not order-binary). Target ~88%.
INSERT INTO SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.pick_operations (pick_id, customer_order_ref, units_ordered, units_picked)
WITH base AS (
  SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT=>300))
),
attrs AS (
  SELECT
    i,
    'PICK-' || LPAD(i,6,'0') AS pick_id,
    'CO-' || LPAD(i,6,'0') AS customer_order_ref,
    UNIFORM(20,300,RANDOM()) AS units_ordered,
    UNIFORM(0::FLOAT,1::FLOAT,RANDOM()) AS fill_roll
  FROM base
)
SELECT
  pick_id, customer_order_ref, units_ordered,
  ROUND(units_ordered * (0.76 + fill_roll * 0.24)) AS units_picked
FROM attrs;

-- Freight invoices for 700/800 pro_numbers only — deliberate 0-or-1 Shipment→Invoice gap
-- that causes the Landed Cost fragmentation (some shipments have no invoice yet).
INSERT INTO SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.freight_invoices (invoice_number, pro_number, freight_cost, customs_duty, invoice_date)
WITH base AS (
  SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT=>800))
),
attrs AS (
  SELECT
    i,
    'PRO-' || LPAD(i,6,'0') AS pro_number,
    UNIFORM(50,800,RANDOM()) AS freight_cost,
    UNIFORM(0,150,RANDOM()) AS customs_duty,
    DATEADD(day, -MOD(i,180), CURRENT_DATE()) AS invoice_date
  FROM base
  WHERE MOD(i,8) != 0
)
SELECT 'INV-' || LPAD(i,6,'0'), pro_number, freight_cost, customs_duty, invoice_date
FROM attrs;

-- Legacy query — OTD as Logistics/TMS sees it (2-day buffer baked in → more lenient)
-- SELECT ROUND(SUM(CASE WHEN first_delivery_attempt_date <= promised_delivery_date THEN 1 ELSE 0 END)
--        / NULLIF(COUNT(*),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.deliveries;

-- Legacy query — Fill Rate as Warehouse sees it (unit-level, continuous, not order-binary)
-- SELECT ROUND(SUM(units_picked) / NULLIF(SUM(units_ordered),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.pick_operations;
