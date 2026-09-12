-- SOURCE_SUPPLIER_PORTAL — genuine flaws:
--   1) drops in-transit/currently-late shipments from OTD denominator entirely
--   2) purchase_orders → supplier-facing PO fill rate (opposite direction from customer fill rate)
USE ROLE SUPPLY_CHAIN_ADMIN;
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL
    COMMENT = 'Fragmented raw Supplier Portal system (inbound shipments, purchase orders, freight quotes). Phase 0 (pre-governance).';

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.shipments (
    asn_number VARCHAR(50) COMMENT 'Advance Ship Notice natural key, format ASN-nnnnnn. Correlates 1:1 by row index with SOURCE_ERP.orders.erp_order_number for the same physical shipment.',
    supplier_id_portal VARCHAR(50) COMMENT 'Portal-internal supplier identifier, format SUP-nnnn.',
    part_number_portal VARCHAR(50) COMMENT 'Portal-internal part identifier, format PART-nnnnn.',
    plant_code VARCHAR(20) COMMENT 'Receiving plant identifier, format PLANT-nnn.',
    planned_receipt_date DATE COMMENT 'Planned receipt date at the plant.',
    actual_receipt_date DATE COMMENT 'Actual receipt date. NULL while shipment_status = IN_TRANSIT.',
    shipment_status VARCHAR(30) COMMENT 'RECEIVED / IN_TRANSIT.',
    quantity NUMBER COMMENT 'Units shipped.',
    load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() COMMENT 'Row load time.'
)
COMMENT = 'KNOWN DATA QUALITY ISSUE: legacy OTD query filters WHERE shipment_status = ''RECEIVED'', dropping in-transit/currently-late shipments from the denominator entirely — hides the worst-performing (still-late) shipments and understates true lateness.';

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.purchase_orders (
    po_number VARCHAR(50) COMMENT 'Purchase order natural key.',
    supplier_id_portal VARCHAR(50) COMMENT 'Portal-internal supplier identifier.',
    part_number_portal VARCHAR(50) COMMENT 'Portal-internal part identifier.',
    qty_ordered NUMBER COMMENT 'Quantity ordered on the PO.',
    qty_received NUMBER COMMENT 'Quantity received against the PO — basis for supplier-facing PO fill rate.',
    po_status VARCHAR(30) COMMENT 'OPEN / CLOSED.'
)
COMMENT = 'Procurement supplier-facing PO fill rate source — deliberately the opposite direction/grain from the customer-facing fill rate. One of three genuinely different Fill Rate concepts resolved as distinct canonical metrics in Phase 4.';

-- Referenced by the Landed Cost (Procurement) legacy query in Phase 2+
CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.freight_quotes (
    part_id VARCHAR(50) COMMENT 'Part identifier, joins to purchase_orders.part_number_portal.',
    freight_estimate NUMBER COMMENT 'Supplier-quoted freight estimate — Procurement''s Landed Cost input, deliberately excludes customs and actuals.'
)
COMMENT = 'Procurement Landed Cost input (PO price + quoted freight only — understates true cost vs. Logistics actual freight+customs).';

-- ── Synthetic data: ~800 shipments correlated (by row index) with SOURCE_ERP.orders.
-- Target: Supplier Portal OTD ~78% among RECEIVED rows (in-transit/late-in-flight dropped entirely).
INSERT INTO SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.shipments (asn_number, supplier_id_portal, part_number_portal, plant_code, planned_receipt_date, actual_receipt_date, shipment_status, quantity)
WITH base AS (
  SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT=>800))
),
attrs AS (
  SELECT
    i,
    'ASN-' || LPAD(i,6,'0') AS asn_number,
    'SUP-' || LPAD(1+MOD(i,50),4,'0') AS supplier_id_portal,
    'PART-' || LPAD(1+MOD(i,100),5,'0') AS part_number_portal,
    'PLANT-' || LPAD(1+MOD(i,20),3,'0') AS plant_code,
    DATEADD(day, -MOD(i,180), CURRENT_DATE()) AS planned_receipt_date,
    UNIFORM(0::FLOAT,1::FLOAT,RANDOM()) AS status_roll,
    UNIFORM(0::FLOAT,1::FLOAT,RANDOM()) AS ontime_roll,
    UNIFORM(1,6,RANDOM()) AS late_days,
    UNIFORM(10,500,RANDOM()) AS quantity
  FROM base
)
SELECT
  asn_number, supplier_id_portal, part_number_portal, plant_code, planned_receipt_date,
  CASE WHEN status_roll < 0.90 AND ontime_roll < 0.78 THEN planned_receipt_date
       WHEN status_roll < 0.90 THEN DATEADD(day, late_days, planned_receipt_date)
       ELSE NULL END AS actual_receipt_date,
  CASE WHEN status_roll < 0.90 THEN 'RECEIVED' ELSE 'IN_TRANSIT' END AS shipment_status,
  quantity
FROM attrs;

-- Purchase orders — supplier-facing PO fill rate. Target ~85%.
INSERT INTO SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.purchase_orders (po_number, supplier_id_portal, part_number_portal, qty_ordered, qty_received, po_status)
WITH base AS (
  SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT=>300))
),
attrs AS (
  SELECT
    i,
    'PO-' || LPAD(i,6,'0') AS po_number,
    'SUP-' || LPAD(1+MOD(i,50),4,'0') AS supplier_id_portal,
    'PART-' || LPAD(1+MOD(i,100),5,'0') AS part_number_portal,
    UNIFORM(50,1000,RANDOM()) AS qty_ordered,
    UNIFORM(0::FLOAT,1::FLOAT,RANDOM()) AS fill_roll
  FROM base
)
SELECT
  po_number, supplier_id_portal, part_number_portal, qty_ordered,
  ROUND(qty_ordered * (0.70 + fill_roll * 0.30)) AS qty_received,
  CASE WHEN fill_roll > 0.9 THEN 'OPEN' ELSE 'CLOSED' END AS po_status
FROM attrs;

-- Freight quotes: 100 parts — feeds Landed Cost (Procurement: PO price + quoted freight only).
INSERT INTO SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.freight_quotes (part_id, freight_estimate)
SELECT 'PART-' || LPAD(SEQ4()+1,5,'0'), UNIFORM(5,80,RANDOM())
FROM TABLE(GENERATOR(ROWCOUNT=>100));

-- Legacy query — OTD as Procurement/Supplier Portal sees it (drops in-transit → hides the worst cases)
-- SELECT ROUND(SUM(CASE WHEN actual_receipt_date <= planned_receipt_date THEN 1 ELSE 0 END)
--        / NULLIF(COUNT(*),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.shipments WHERE shipment_status = 'RECEIVED';

-- Legacy query — Fill Rate as Procurement sees it (supplier-facing PO fill)
-- SELECT ROUND(SUM(qty_received) / NULLIF(SUM(qty_ordered),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.purchase_orders;
