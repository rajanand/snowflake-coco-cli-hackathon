-- =============================================================================
-- Phase 1: Bronze Layer — ingest Phase 0 SOURCE_* systems (11 tables)
-- =============================================================================
-- Pattern: OBJECT_CONSTRUCT(*) captures the source row as-is (column names and
-- all) into RAW_PAYLOAD, so Bronze stays source-shaped — no cleansing,
-- renaming, or type-casting happens until Silver. _METADATA records exactly
-- which source system/table/timestamp each row came from, which is what lets
-- Silver's shipment_crosswalk (entity resolution) trace a canonical shipment
-- back to its originating fragmented record.
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;
USE SCHEMA SUPPLY_CHAIN.BRONZE;

INSERT INTO ORDERS (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_ERP', 'source_table', 'ORDERS', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_ERP.orders;

INSERT INTO DELIVERIES (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_LOGISTICS_TMS', 'source_table', 'DELIVERIES', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.deliveries;

INSERT INTO SHIPMENTS (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_SUPPLIER_PORTAL', 'source_table', 'SHIPMENTS', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.shipments;

INSERT INTO TRACKING_EVENTS (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_IOT_SENSOR', 'source_table', 'TRACKING_EVENTS', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_IOT_SENSOR.tracking_events;

INSERT INTO PURCHASE_ORDERS (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_SUPPLIER_PORTAL', 'source_table', 'PURCHASE_ORDERS', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.purchase_orders;

INSERT INTO PICK_OPERATIONS (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_LOGISTICS_TMS', 'source_table', 'PICK_OPERATIONS', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.pick_operations;

INSERT INTO DEMAND_FORECAST (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_ERP', 'source_table', 'DEMAND_FORECAST', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_ERP.demand_forecast;

INSERT INTO DAILY_COGS (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_FINANCE', 'source_table', 'DAILY_COGS', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_FINANCE.daily_cogs;

INSERT INTO FREIGHT_INVOICES (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_LOGISTICS_TMS', 'source_table', 'FREIGHT_INVOICES', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.freight_invoices;

INSERT INTO OVERHEAD_ALLOCATION (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_FINANCE', 'source_table', 'OVERHEAD_ALLOCATION', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_FINANCE.overhead_allocation;

INSERT INTO FREIGHT_QUOTES (RAW_PAYLOAD, _METADATA)
SELECT OBJECT_CONSTRUCT(*),
       OBJECT_CONSTRUCT('source_system', 'SOURCE_SUPPLIER_PORTAL', 'source_table', 'FREIGHT_QUOTES', 'ingested_at', CURRENT_TIMESTAMP())
FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.freight_quotes;
