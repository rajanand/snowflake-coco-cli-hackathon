-- =============================================================================
-- Ops: Pause / Resume all auto-refreshing compute in SUPPLY_CHAIN
-- =============================================================================
-- Purpose: All 28 Dynamic Tables (Silver + Gold) and the Cortex Search Service
-- consume warehouse credits on every scheduled refresh (TARGET_LAG), even with
-- no new data landing in Bronze. Between working sessions, suspend everything
-- below to stop incurring charges. Re-run the RESUME section when you want to
-- pick the project back up (e.g. before a demo).
--
-- Current state as of last pause: all objects SUSPENDED (see pause section run
-- on 2026-09-12). Warehouse COMPUTE_WH manually suspended too.
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;

-- -----------------------------------------------------------------------------
-- PAUSE (run this to stop incurring charges)
-- -----------------------------------------------------------------------------

-- Silver Dynamic Tables
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.suppliers SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.parts SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.plants SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.customers SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.shipment_crosswalk SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.customer_orders SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.purchase_orders SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.pick_operations SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.demand_forecast SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.daily_cogs SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.inventory_snapshots SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.freight_invoices SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.overhead_allocation SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.freight_quotes SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.quality_events SUSPEND;

-- Gold Dynamic Tables (dim_date is a static table, not a Dynamic Table -- no action needed)
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.dim_supplier SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.dim_part SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.dim_plant SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.dim_customer SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_shipment SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_order_fulfillment SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_inventory_snapshot SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_quality_event SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.bridge_supplier_part SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.agg_supplier_performance SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_purchase_order SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_pick_operation SUSPEND;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_landed_cost SUSPEND;

-- Cortex Search Service (suspends both INDEXING and SERVING)
ALTER CORTEX SEARCH SERVICE SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS SUSPEND;

-- Warehouse (auto_suspend=300s already protects against idle cost, but suspend
-- immediately rather than waiting out the 5-minute timer)
ALTER WAREHOUSE COMPUTE_WH SUSPEND;

-- -----------------------------------------------------------------------------
-- RESUME (run this before your next working session / demo)
-- -----------------------------------------------------------------------------
-- Uncomment and run the block below when ready to continue.
-- Dynamic Tables will catch up to the latest Bronze data on their next
-- scheduled refresh after RESUME (no manual REFRESH needed).

/*
USE ROLE SUPPLY_CHAIN_ADMIN;

ALTER WAREHOUSE COMPUTE_WH RESUME;

-- Silver
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.suppliers RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.parts RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.plants RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.customers RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.shipment_crosswalk RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.customer_orders RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.purchase_orders RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.pick_operations RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.demand_forecast RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.daily_cogs RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.inventory_snapshots RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.freight_invoices RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.overhead_allocation RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.freight_quotes RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.SILVER.quality_events RESUME;

-- Gold
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.dim_supplier RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.dim_part RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.dim_plant RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.dim_customer RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_shipment RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_order_fulfillment RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_inventory_snapshot RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_quality_event RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.bridge_supplier_part RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.agg_supplier_performance RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_purchase_order RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_pick_operation RESUME;
ALTER DYNAMIC TABLE SUPPLY_CHAIN.GOLD.fact_landed_cost RESUME;

-- Cortex Search Service
ALTER CORTEX SEARCH SERVICE SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS RESUME;
*/

-- -----------------------------------------------------------------------------
-- Verification queries
-- -----------------------------------------------------------------------------
-- SHOW DYNAMIC TABLES IN DATABASE SUPPLY_CHAIN;                 -- check scheduling_state
-- SHOW CORTEX SEARCH SERVICES IN DATABASE SUPPLY_CHAIN;         -- check indexing_state / serving_state
-- SHOW WAREHOUSES LIKE 'COMPUTE_WH';                            -- check state (STARTED / SUSPENDED)
