-- =============================================================================
-- Phase 1: Bronze Layer — raw landing zone (structured + semi-structured)
-- =============================================================================
-- Bronze tables use TWO landing patterns:
--
-- 1. STRUCTURED (16 tables): typed columns mapped 1:1 from source, plus
--    _METADATA (OBJECT: source_system, source_table, ingested_at) for lineage,
--    plus LOAD_TIMESTAMP. No VARIANT wrapper — the source data is clean,
--    relational data and wrapping it in VARIANT loses type safety for no gain.
--
-- 2. SEMI-STRUCTURED (1 table: tracking_events): DEVICE_TAG as a typed column
--    (stable identifier) + EVENT_PAYLOAD as VARIANT (genuinely nested/variable
--    sensor JSON with noise fields). This is what VARIANT is designed for.
--
-- _METADATA is retained on every table regardless of pattern — it tracks
-- lineage (which source system/table/timestamp each row came from) and is
-- genuinely useful metadata independent of payload shape.
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;

CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.BRONZE
    COMMENT = 'Phase 1: raw landing zone. Structured typed-column landing for relational sources (16 tables) + semi-structured VARIANT landing for IoT sensor events (1 table). Ingests Phase 0 SOURCE_* systems plus directly-generated synthetic data for entities with no fragmented source-system equivalent (parts, plants, customers, customer_orders, inventory_snapshots, quality_events).';

USE SCHEMA SUPPLY_CHAIN.BRONZE;

-- -----------------------------------------------------------------------------
-- Ingested from Phase 0 SOURCE_* schemas (11 tables) — typed columns, 1:1 match
-- -----------------------------------------------------------------------------

-- SOURCE_ERP.orders (structured)
CREATE OR REPLACE TABLE ORDERS (
    ERP_ORDER_NUMBER     VARCHAR(50)   COMMENT 'ERP natural key.',
    SUPPLIER_CODE        VARCHAR(50)   COMMENT 'ERP-internal supplier identifier, format SUPnnnn.',
    PART_SKU             VARCHAR(50)   COMMENT 'ERP-internal part identifier, format PARTnnnnn.',
    REQUESTED_SHIP_DATE  DATE          COMMENT 'Date the order was requested to ship.',
    ACTUAL_SHIP_DATE     DATE          COMMENT 'Date the order actually shipped. NULL for CANCELLED/BACKORDER.',
    ORDER_STATUS         VARCHAR(30)   COMMENT 'COMPLETE / CANCELLED / BACKORDER.',
    QUANTITY             NUMBER(38,0)  COMMENT 'Units ordered.',
    _METADATA            OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP       TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_ERP.orders — typed columns, source-shaped.';

-- SOURCE_LOGISTICS_TMS.deliveries (structured)
CREATE OR REPLACE TABLE DELIVERIES (
    PRO_NUMBER                   VARCHAR(50)   COMMENT 'TMS natural key.',
    CARRIER_NAME                 VARCHAR(100)  COMMENT 'Freight carrier.',
    ORIGIN_SUPPLIER_NAME         VARCHAR(200)  COMMENT 'Free-text supplier name entered by carrier ops — spelling variants.',
    PROMISED_DELIVERY_DATE       DATE          COMMENT 'TMS promised delivery date (includes 2-day carrier buffer).',
    FIRST_DELIVERY_ATTEMPT_DATE  DATE          COMMENT 'Date of first delivery attempt.',
    FINAL_DELIVERY_DATE          DATE          COMMENT 'Date of final successful delivery.',
    IS_PARTIAL_SHIPMENT          BOOLEAN       COMMENT 'True if split into a partial delivery.',
    _METADATA                    OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP               TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_LOGISTICS_TMS.deliveries — typed columns.';

-- SOURCE_SUPPLIER_PORTAL.shipments (structured)
CREATE OR REPLACE TABLE SHIPMENTS (
    ASN_NUMBER           VARCHAR(50)   COMMENT 'Advance Ship Notice natural key.',
    SUPPLIER_ID_PORTAL   VARCHAR(50)   COMMENT 'Portal-internal supplier identifier.',
    PART_NUMBER_PORTAL   VARCHAR(50)   COMMENT 'Portal-internal part identifier.',
    PLANT_CODE           VARCHAR(20)   COMMENT 'Receiving plant identifier, format PLANTnnn.',
    PLANNED_RECEIPT_DATE DATE          COMMENT 'Planned receipt date at the plant.',
    ACTUAL_RECEIPT_DATE  DATE          COMMENT 'Actual receipt date. NULL while IN_TRANSIT.',
    SHIPMENT_STATUS      VARCHAR(30)   COMMENT 'RECEIVED / IN_TRANSIT.',
    QUANTITY             NUMBER(38,0)  COMMENT 'Units shipped.',
    _METADATA            OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP       TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_SUPPLIER_PORTAL.shipments — typed columns.';

-- SOURCE_IOT_SENSOR.tracking_events (SEMI-STRUCTURED — genuinely nested sensor JSON)
CREATE OR REPLACE TABLE TRACKING_EVENTS (
    DEVICE_TAG       VARCHAR(50) COMMENT 'Sensor device tag — typed, stable identifier.',
    EVENT_PAYLOAD    VARIANT     COMMENT 'Semi-structured sensor event JSON (epoch_ms, expected_epoch_ms, sensor_battery_pct, noise_flag). Genuinely variable/nested — stays VARIANT.',
    _METADATA        OBJECT      COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP   TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_IOT_SENSOR.tracking_events — semi-structured (VARIANT payload for genuinely nested sensor JSON).';

-- SOURCE_SUPPLIER_PORTAL.purchase_orders (structured)
CREATE OR REPLACE TABLE PURCHASE_ORDERS (
    PO_NUMBER            VARCHAR(50)   COMMENT 'Purchase order natural key.',
    SUPPLIER_ID_PORTAL   VARCHAR(50)   COMMENT 'Portal-internal supplier identifier.',
    PART_NUMBER_PORTAL   VARCHAR(50)   COMMENT 'Portal-internal part identifier.',
    QTY_ORDERED          NUMBER(38,0)  COMMENT 'Quantity ordered on the PO.',
    QTY_RECEIVED         NUMBER(38,0)  COMMENT 'Quantity received against the PO.',
    PO_STATUS            VARCHAR(30)   COMMENT 'OPEN / CLOSED.',
    _METADATA            OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP       TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_SUPPLIER_PORTAL.purchase_orders — typed columns.';

-- SOURCE_LOGISTICS_TMS.pick_operations (structured)
CREATE OR REPLACE TABLE PICK_OPERATIONS (
    PICK_ID              VARCHAR(50)   COMMENT 'Warehouse pick operation natural key.',
    CUSTOMER_ORDER_REF   VARCHAR(50)   COMMENT 'Reference to the outbound customer order.',
    UNITS_ORDERED        NUMBER(38,0)  COMMENT 'Units ordered for this pick.',
    UNITS_PICKED         NUMBER(38,0)  COMMENT 'Units actually picked.',
    _METADATA            OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP       TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_LOGISTICS_TMS.pick_operations — typed columns.';

-- SOURCE_ERP.demand_forecast (structured)
CREATE OR REPLACE TABLE DEMAND_FORECAST (
    PART_SKU                 VARCHAR(50)   COMMENT 'ERP-internal part identifier.',
    FORECAST_MONTH           DATE          COMMENT 'First day of the forecasted month.',
    FORECASTED_DAILY_DEMAND  NUMBER(38,0)  COMMENT 'Planning-team forecasted average daily demand (units).',
    _METADATA                OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP           TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_ERP.demand_forecast — typed columns.';

-- SOURCE_FINANCE.daily_cogs (structured)
CREATE OR REPLACE TABLE DAILY_COGS (
    PART_ID      VARCHAR(50)   COMMENT 'Part identifier.',
    COGS_DATE    DATE          COMMENT 'Cost-of-goods-sold date.',
    DAILY_COGS   NUMBER(38,0)  COMMENT 'Daily cost of goods sold ($) for this part.',
    _METADATA    OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_FINANCE.daily_cogs — typed columns.';

-- SOURCE_LOGISTICS_TMS.freight_invoices (structured)
CREATE OR REPLACE TABLE FREIGHT_INVOICES (
    INVOICE_NUMBER VARCHAR(50) COMMENT 'Freight invoice natural key.',
    PRO_NUMBER     VARCHAR(50) COMMENT 'Joins to deliveries.pro_number.',
    FREIGHT_COST   NUMBER(38,0) COMMENT 'Actual freight cost charged.',
    CUSTOMS_DUTY   NUMBER(38,0) COMMENT 'Actual customs duty charged.',
    INVOICE_DATE   DATE         COMMENT 'Invoice date.',
    _METADATA      OBJECT       COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_LOGISTICS_TMS.freight_invoices — typed columns.';

-- SOURCE_FINANCE.overhead_allocation (structured)
CREATE OR REPLACE TABLE OVERHEAD_ALLOCATION (
    PART_CATEGORY               VARCHAR(50)   COMMENT 'Part category identifier, format CATnn.',
    MONTH                       DATE          COMMENT 'First day of the allocation month.',
    ALLOCATED_OVERHEAD_PER_UNIT NUMBER(38,0)  COMMENT 'Finance-allocated overhead cost per unit ($).',
    _METADATA                   OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP              TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_FINANCE.overhead_allocation — typed columns.';

-- SOURCE_SUPPLIER_PORTAL.freight_quotes (structured)
CREATE OR REPLACE TABLE FREIGHT_QUOTES (
    PART_ID          VARCHAR(50)   COMMENT 'Part identifier.',
    FREIGHT_ESTIMATE NUMBER(38,0)  COMMENT 'Supplier-quoted freight estimate.',
    _METADATA        OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP   TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_SUPPLIER_PORTAL.freight_quotes — typed columns.';

-- -----------------------------------------------------------------------------
-- Net-new entities (6 tables) — no Phase 0 fragmented source exists;
-- generated directly into Bronze (_metadata.source_system = SYNTHETIC_GENERATED)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE TABLE PARTS (
    PART_ID    VARCHAR(50)    COMMENT 'Part identifier, format PART-nnnnn.',
    PART_NAME  VARCHAR(100)   COMMENT 'Part display name.',
    CATEGORY   VARCHAR(50)    COMMENT 'Part category, format CAT-nn.',
    UNIT_COST  NUMBER(10,2)   COMMENT 'Unit cost ($).',
    UOM        VARCHAR(20)    COMMENT 'Unit of measure (EACH/CASE/PALLET).',
    _METADATA  OBJECT         COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for parts master data. Net-new entity — no Phase 0 fragmented source exists; generated directly (_metadata.source_system = SYNTHETIC_GENERATED).';

CREATE OR REPLACE TABLE PLANTS (
    PLANT_ID   VARCHAR(50)    COMMENT 'Plant identifier, format PLANT-nnn.',
    PLANT_NAME VARCHAR(100)   COMMENT 'Plant/facility display name.',
    REGION     VARCHAR(50)    COMMENT 'Geographic region.',
    PLANT_TYPE VARCHAR(50)    COMMENT 'Facility type (DISTRIBUTION_CENTER).',
    _METADATA  OBJECT         COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for plant/facility master data. Net-new entity — generated directly.';

CREATE OR REPLACE TABLE CUSTOMERS (
    CUSTOMER_ID   VARCHAR(50)    COMMENT 'Customer identifier, format CUST-nnnn.',
    CUSTOMER_NAME VARCHAR(100)   COMMENT 'Customer display name.',
    SEGMENT       VARCHAR(50)    COMMENT 'Customer segment (ENTERPRISE/MID_MARKET/SMB).',
    REGION        VARCHAR(50)    COMMENT 'Geographic region.',
    _METADATA     OBJECT         COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for customer master data. Net-new entity — generated directly.';

CREATE OR REPLACE TABLE CUSTOMER_ORDERS (
    CUSTOMER_ORDER_ID      VARCHAR(50)   COMMENT 'Customer order identifier, format ORD-nnnnnn.',
    CUSTOMER_ID            VARCHAR(50)   COMMENT 'Customer FK.',
    PART_ID                VARCHAR(50)   COMMENT 'Part FK.',
    ORDER_DATE             DATE          COMMENT 'Order placement date.',
    REQUESTED_DELIVERY_DATE DATE         COMMENT 'Customer-requested delivery date.',
    ACTUAL_DELIVERY_DATE   DATE          COMMENT 'Actual delivery date.',
    QTY_ORDERED            NUMBER(38,0)  COMMENT 'Quantity ordered.',
    QTY_SHIPPED            NUMBER(38,0)  COMMENT 'Quantity shipped.',
    ORDER_STATUS           VARCHAR(30)   COMMENT 'COMPLETE / PARTIAL.',
    _METADATA              OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP         TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for outbound customer orders. Net-new entity — generated directly; enables the CustomerOrder->Part->Supplier ontology chain.';

CREATE OR REPLACE TABLE INVENTORY_SNAPSHOTS (
    SNAPSHOT_ID        VARCHAR(50)   COMMENT 'Snapshot identifier, format INVSNAP-nnnnnn.',
    PLANT_ID           VARCHAR(50)   COMMENT 'Plant FK.',
    PART_ID            VARCHAR(50)   COMMENT 'Part FK.',
    SNAPSHOT_DATE      DATE          COMMENT 'Snapshot date.',
    ON_HAND_QTY        NUMBER(38,0)  COMMENT 'On-hand inventory quantity.',
    SAFETY_STOCK_QTY   NUMBER(38,0)  COMMENT 'Safety stock quantity.',
    AVG_DAILY_USAGE_QTY NUMBER(38,0) COMMENT 'Trailing average daily usage (units).',
    _METADATA          OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP     TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for daily part-plant inventory snapshots. Net-new entity — generated directly; feeds Days-of-Inventory (DOI) in Gold.';

CREATE OR REPLACE TABLE QUALITY_EVENTS (
    QUALITY_EVENT_ID VARCHAR(50)   COMMENT 'Quality event identifier, format QE-nnnnn.',
    PART_ID          VARCHAR(50)   COMMENT 'Part FK.',
    SUPPLIER_ID      VARCHAR(50)   COMMENT 'Supplier FK.',
    PLANT_ID         VARCHAR(50)   COMMENT 'Plant FK.',
    EVENT_DATE       DATE          COMMENT 'Event date.',
    DEFECT_TYPE      VARCHAR(50)   COMMENT 'Defect category.',
    SEVERITY         VARCHAR(20)   COMMENT 'CRITICAL / MAJOR / MINOR.',
    QTY_AFFECTED     NUMBER(38,0)  COMMENT 'Units affected.',
    DISPOSITION      VARCHAR(50)   COMMENT 'Disposition action taken.',
    _METADATA        OBJECT        COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP   TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for supplier quality defect events. Net-new entity — generated directly.';

-- -----------------------------------------------------------------------------
-- Governance tags — lifecycle stage at the schema level.
-- -----------------------------------------------------------------------------

ALTER SCHEMA SUPPLY_CHAIN.BRONZE SET TAG SUPPLY_CHAIN.GOVERNANCE.LIFECYCLE = 'BRONZE';
