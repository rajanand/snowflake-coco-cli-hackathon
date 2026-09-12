-- =============================================================================
-- Phase 1: Bronze Layer — unified raw landing zone
-- =============================================================================
-- Every source system, however it names/shapes its columns, lands in Bronze
-- through the same envelope: RAW_PAYLOAD (VARIANT, source row as-is) +
-- _METADATA (source_system, source_table, ingested_at). This is what makes
-- "unified raw landing" real rather than aspirational — Silver can pull from
-- one consistent shape no matter which of the 5 fragmented source systems
-- (or the 6 net-new entities with no fragmented source) a row came from.
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;

CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.BRONZE
    COMMENT = 'Phase 1: unified raw landing zone. Ingests Phase 0 SOURCE_* systems (still source-shaped, VARIANT payload) plus directly-generated synthetic data for entities with no fragmented source-system equivalent (parts, plants, customers, customer_orders, inventory_snapshots, quality_events).';

USE SCHEMA SUPPLY_CHAIN.BRONZE;

-- -----------------------------------------------------------------------------
-- Ingested from Phase 0 SOURCE_* schemas (11 tables) — source-shaped, unchanged
-- -----------------------------------------------------------------------------

CREATE OR REPLACE TABLE ORDERS (
    RAW_PAYLOAD VARIANT COMMENT 'Full source row as-is from SOURCE_ERP.orders.',
    _METADATA OBJECT COMMENT 'source_system, source_table, ingested_at.',
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_ERP.orders — unchanged, source-shaped.';

CREATE OR REPLACE TABLE DELIVERIES (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_LOGISTICS_TMS.deliveries.';

CREATE OR REPLACE TABLE SHIPMENTS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_SUPPLIER_PORTAL.shipments.';

CREATE OR REPLACE TABLE TRACKING_EVENTS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_IOT_SENSOR.tracking_events.';

CREATE OR REPLACE TABLE PURCHASE_ORDERS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_SUPPLIER_PORTAL.purchase_orders.';

CREATE OR REPLACE TABLE PICK_OPERATIONS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_LOGISTICS_TMS.pick_operations.';

CREATE OR REPLACE TABLE DEMAND_FORECAST (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_ERP.demand_forecast.';

CREATE OR REPLACE TABLE DAILY_COGS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_FINANCE.daily_cogs.';

CREATE OR REPLACE TABLE FREIGHT_INVOICES (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_LOGISTICS_TMS.freight_invoices.';

CREATE OR REPLACE TABLE OVERHEAD_ALLOCATION (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_FINANCE.overhead_allocation.';

CREATE OR REPLACE TABLE FREIGHT_QUOTES (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for SOURCE_SUPPLIER_PORTAL.freight_quotes.';

-- -----------------------------------------------------------------------------
-- Net-new entities (6 tables) — no Phase 0 fragmented source exists;
-- generated directly into Bronze (_metadata.source_system = SYNTHETIC_GENERATED)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE TABLE PARTS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for parts master data. Net-new entity — no Phase 0 fragmented source exists; generated directly (_metadata.source_system = SYNTHETIC_GENERATED).';

CREATE OR REPLACE TABLE PLANTS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for plant/facility master data. Net-new entity — generated directly.';

CREATE OR REPLACE TABLE CUSTOMERS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for customer master data. Net-new entity — generated directly.';

CREATE OR REPLACE TABLE CUSTOMER_ORDERS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for outbound customer orders. Net-new entity — generated directly; enables the CustomerOrder->Part->Supplier ontology chain (at-risk-order queries in Phase 4-5).';

CREATE OR REPLACE TABLE INVENTORY_SNAPSHOTS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for daily part-plant inventory snapshots. Net-new entity — generated directly; feeds Days-of-Inventory (DOI) in Gold.';

CREATE OR REPLACE TABLE QUALITY_EVENTS (
    RAW_PAYLOAD VARIANT,
    _METADATA OBJECT,
    LOAD_TIMESTAMP TIMESTAMP_NTZ(9) DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'Bronze landing for supplier quality defect events. Net-new entity — generated directly.';

-- -----------------------------------------------------------------------------
-- Governance tags — lifecycle stage at the schema level. SOURCE_SYSTEM is
-- deliberately NOT applied per-table here: its allowed_values enum is scoped
-- to a single Phase 0 system (ERP, LOGISTICS_TMS, SUPPLIER_PORTAL, IOT_SENSOR,
-- FINANCE) and doesn't fit a Bronze table that can land rows from more than
-- one upstream system over time, or a net-new entity with no source system.
-- -----------------------------------------------------------------------------

ALTER SCHEMA SUPPLY_CHAIN.BRONZE SET TAG SUPPLY_CHAIN.GOVERNANCE.LIFECYCLE = 'BRONZE';
