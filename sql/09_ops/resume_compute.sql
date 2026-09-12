
-- -----------------------------------------------------------------------------
-- RESUME (run this before your next working session / demo)
-- -----------------------------------------------------------------------------
-- Uncomment and run the block below when ready to continue.
-- Dynamic Tables will catch up to the latest Bronze data on their next
-- scheduled refresh after RESUME (no manual REFRESH needed).


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


-- -----------------------------------------------------------------------------
-- Verification queries
-- -----------------------------------------------------------------------------
-- SHOW DYNAMIC TABLES IN DATABASE SUPPLY_CHAIN;                 -- check scheduling_state
-- SHOW CORTEX SEARCH SERVICES IN DATABASE SUPPLY_CHAIN;         -- check indexing_state / serving_state
-- SHOW WAREHOUSES LIKE 'COMPUTE_WH';                            -- check state (STARTED / SUSPENDED)
