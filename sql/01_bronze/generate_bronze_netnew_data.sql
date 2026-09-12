-- =============================================================================
-- Phase 1: Bronze Layer — generate net-new entities (no Phase 0 source exists)
-- =============================================================================
-- parts, plants, customers are master data with no upstream system fragmentation
-- to demonstrate, so they're generated directly with a consistent schema.
-- customer_orders, inventory_snapshots, quality_events are transactional/event
-- entities that complete the ontology chain (CustomerOrder->Part->Supplier,
-- Inventory->DOI, QualityEvent->Supplier) but were out of scope for Phase 0's
-- deliberate fragmentation story.
--
-- customer_orders is calibrated to reproduce the target customer-facing fill
-- rate (~91%) and a plausible on-time-delivery distribution, consistent with
-- the divergent-metrics story carried through from Phase 0.
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;
USE SCHEMA SUPPLY_CHAIN.BRONZE;

-- -----------------------------------------------------------------------------
-- parts (100 SKUs)
-- -----------------------------------------------------------------------------
INSERT INTO PARTS (RAW_PAYLOAD, _METADATA)
WITH p AS (SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT => 100)))
SELECT
    OBJECT_CONSTRUCT(
        'part_id', 'PART-' || LPAD(i, 5, '0'),
        'part_name', 'Part ' || i,
        'category', 'CAT-' || LPAD(1 + MOD(i, 10), 2, '0'),
        'unit_cost', ROUND(UNIFORM(5, 500, RANDOM())::FLOAT + UNIFORM(0, 99, RANDOM()) / 100, 2),
        'uom', CASE MOD(i, 3) WHEN 0 THEN 'EACH' WHEN 1 THEN 'CASE' ELSE 'PALLET' END
    ),
    OBJECT_CONSTRUCT('source_system', 'SYNTHETIC_GENERATED', 'source_table', 'N/A', 'ingested_at', CURRENT_TIMESTAMP())
FROM p;

-- -----------------------------------------------------------------------------
-- plants (20 distribution centers, PLANT-001..020 — matches the 3-digit plant
-- code range already referenced by SOURCE_SUPPLIER_PORTAL.shipments.plant_code)
-- -----------------------------------------------------------------------------
INSERT INTO PLANTS (RAW_PAYLOAD, _METADATA)
WITH p AS (SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT => 20)))
SELECT
    OBJECT_CONSTRUCT(
        'plant_id', 'PLANT-' || LPAD(i, 3, '0'),
        'plant_name', CASE MOD(i, 10)
            WHEN 1 THEN 'Dallas DC' WHEN 2 THEN 'Columbus DC' WHEN 3 THEN 'Reno DC' WHEN 4 THEN 'Atlanta DC'
            WHEN 5 THEN 'Newark DC' WHEN 6 THEN 'Chicago DC' WHEN 7 THEN 'Phoenix DC' WHEN 8 THEN 'Memphis DC'
            WHEN 9 THEN 'Seattle DC' ELSE 'Denver DC' END || ' ' || CEIL(i / 10),
        'region', CASE MOD(i, 5) WHEN 1 THEN 'SOUTH' WHEN 2 THEN 'MIDWEST' WHEN 3 THEN 'WEST' WHEN 4 THEN 'SOUTHEAST' ELSE 'NORTHEAST' END,
        'plant_type', 'DISTRIBUTION_CENTER'
    ),
    OBJECT_CONSTRUCT('source_system', 'SYNTHETIC_GENERATED', 'source_table', 'N/A', 'ingested_at', CURRENT_TIMESTAMP())
FROM p;

-- -----------------------------------------------------------------------------
-- customers (50 accounts)
-- -----------------------------------------------------------------------------
INSERT INTO CUSTOMERS (RAW_PAYLOAD, _METADATA)
WITH c AS (SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT => 50)))
SELECT
    OBJECT_CONSTRUCT(
        'customer_id', 'CUST-' || LPAD(i, 4, '0'),
        'customer_name', 'Customer ' || i,
        'segment', CASE WHEN MOD(i, 10) = 0 THEN 'ENTERPRISE' WHEN MOD(i, 3) = 0 THEN 'MID_MARKET' ELSE 'SMB' END,
        'region', CASE MOD(i, 4) WHEN 0 THEN 'NORTH_AMERICA' WHEN 1 THEN 'EMEA' WHEN 2 THEN 'APAC' ELSE 'LATAM' END
    ),
    OBJECT_CONSTRUCT('source_system', 'SYNTHETIC_GENERATED', 'source_table', 'N/A', 'ingested_at', CURRENT_TIMESTAMP())
FROM c;

-- -----------------------------------------------------------------------------
-- customer_orders (500 orders, ~91% customer-facing fill rate, ~91% on-time)
-- -----------------------------------------------------------------------------
INSERT INTO CUSTOMER_ORDERS (RAW_PAYLOAD, _METADATA)
WITH base AS (SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT => 500))),
attrs AS (
    SELECT
        i,
        'ORD-' || LPAD(i, 6, '0') AS customer_order_id,
        'CUST-' || LPAD(1 + MOD(i, 50), 4, '0') AS customer_id,
        'PART-' || LPAD(1 + MOD(i, 100), 5, '0') AS part_id,
        DATEADD(day, -MOD(i, 120), CURRENT_DATE()) AS order_date,
        UNIFORM(10, 200, RANDOM()) AS qty_ordered,
        UNIFORM(0::FLOAT, 1::FLOAT, RANDOM()) AS fill_roll,
        UNIFORM(0::FLOAT, 1::FLOAT, RANDOM()) AS ontime_roll,
        UNIFORM(1, 5, RANDOM()) AS late_days
    FROM base
)
SELECT
    OBJECT_CONSTRUCT(
        'customer_order_id', customer_order_id,
        'customer_id', customer_id,
        'part_id', part_id,
        'order_date', order_date,
        'requested_delivery_date', DATEADD(day, 7, order_date),
        'actual_delivery_date', CASE WHEN ontime_roll < 0.91 THEN DATEADD(day, 7, order_date) ELSE DATEADD(day, 7 + late_days, order_date) END,
        'qty_ordered', qty_ordered,
        'qty_shipped', CASE WHEN fill_roll < 0.91 THEN qty_ordered ELSE ROUND(qty_ordered * UNIFORM(0.3, 0.9, RANDOM())) END,
        'order_status', CASE WHEN fill_roll < 0.91 THEN 'COMPLETE' ELSE 'PARTIAL' END
    ),
    OBJECT_CONSTRUCT('source_system', 'SYNTHETIC_GENERATED', 'source_table', 'N/A', 'ingested_at', CURRENT_TIMESTAMP())
FROM attrs;

-- -----------------------------------------------------------------------------
-- inventory_snapshots (10 days x 100 parts x 20 plants = 20,000 rows) — DOI feed
-- -----------------------------------------------------------------------------
INSERT INTO INVENTORY_SNAPSHOTS (RAW_PAYLOAD, _METADATA)
WITH days AS (SELECT SEQ4() AS d FROM TABLE(GENERATOR(ROWCOUNT => 10))),
parts AS (SELECT SEQ4() + 1 AS p FROM TABLE(GENERATOR(ROWCOUNT => 100))),
plants AS (SELECT SEQ4() + 1 AS pl FROM TABLE(GENERATOR(ROWCOUNT => 20))),
combo AS (
    SELECT d, p, pl, ROW_NUMBER() OVER (ORDER BY d, p, pl) AS rn
    FROM days CROSS JOIN parts CROSS JOIN plants
)
SELECT
    OBJECT_CONSTRUCT(
        'snapshot_id', 'INVSNAP-' || LPAD(rn, 6, '0'),
        'plant_id', 'PLANT-' || LPAD(pl, 3, '0'),
        'part_id', 'PART-' || LPAD(p, 5, '0'),
        'snapshot_date', DATEADD(day, -d, CURRENT_DATE()),
        'on_hand_qty', UNIFORM(0, 5000, RANDOM()),
        'safety_stock_qty', UNIFORM(100, 500, RANDOM()),
        'avg_daily_usage_qty', UNIFORM(10, 150, RANDOM())
    ),
    OBJECT_CONSTRUCT('source_system', 'SYNTHETIC_GENERATED', 'source_table', 'N/A', 'ingested_at', CURRENT_TIMESTAMP())
FROM combo;

-- -----------------------------------------------------------------------------
-- quality_events (150 defect events) — supplier quality feed
-- -----------------------------------------------------------------------------
INSERT INTO QUALITY_EVENTS (RAW_PAYLOAD, _METADATA)
WITH q AS (SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT => 150)))
SELECT
    OBJECT_CONSTRUCT(
        'quality_event_id', 'QE-' || LPAD(i, 5, '0'),
        'part_id', 'PART-' || LPAD(1 + MOD(i, 50), 5, '0'),
        'supplier_id', 'SUP-' || LPAD(1 + MOD(i, 25), 4, '0'),
        'plant_id', 'PLANT-' || LPAD(1 + MOD(i, 20), 3, '0'),
        'event_date', DATEADD(day, -MOD(i * 3, 180), CURRENT_DATE()),
        'defect_type', CASE MOD(i, 5) WHEN 0 THEN 'DIMENSIONAL' WHEN 1 THEN 'COSMETIC' WHEN 2 THEN 'FUNCTIONAL' WHEN 3 THEN 'PACKAGING' ELSE 'DOCUMENTATION' END,
        'severity', CASE MOD(i, 3) WHEN 0 THEN 'CRITICAL' WHEN 1 THEN 'MAJOR' ELSE 'MINOR' END,
        'qty_affected', UNIFORM(1, 200, RANDOM()),
        'disposition', CASE MOD(i, 4) WHEN 0 THEN 'RETURNED_TO_SUPPLIER' WHEN 1 THEN 'SCRAPPED' WHEN 2 THEN 'REWORKED' ELSE 'ACCEPTED_WITH_DEVIATION' END
    ),
    OBJECT_CONSTRUCT('source_system', 'SYNTHETIC_GENERATED', 'source_table', 'N/A', 'ingested_at', CURRENT_TIMESTAMP())
FROM q;
