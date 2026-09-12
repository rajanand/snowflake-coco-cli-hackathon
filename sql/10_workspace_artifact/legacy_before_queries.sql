-- =============================================================================
-- Phase 4.5 (Marketplace + Worksheets touchpoint): the legacy "Before" queries
-- =============================================================================
-- Every query below was run live against SUPPLY_CHAIN.SOURCE_* / GOLD and the
-- results are recorded as comments -- this is the concrete, screenshot-able
-- artifact proving the pre-governance metric fragmentation was real, not
-- staged. Published to a Snowsight Workspace via:
--   CREATE WORKSPACE SUPPLY_CHAIN.GOVERNANCE.LEGACY_QUERIES_WORKSPACE;
--   ALTER WORKSPACE ... ADD LIVE VERSION FROM LAST;
--   PUT file://.../legacy_before_queries.sql snow://workspace/.../versions/live/;
--   ALTER WORKSPACE ... COMMIT;
-- =============================================================================


-- =============================================================================
-- METRIC 1: On-Time Delivery (OTD) -- four teams, four incompatible answers
-- =============================================================================

-- ERP Team (Operations): excludes cancelled/backorder rows -> inflated
SELECT ROUND(
    SUM(CASE WHEN ACTUAL_SHIP_DATE <= REQUESTED_SHIP_DATE THEN 1 ELSE 0 END)
    * 100.0 / COUNT(*), 1
) AS otd_pct
FROM SUPPLY_CHAIN.SOURCE_ERP.ORDERS
WHERE ORDER_STATUS = 'COMPLETE';
-- Result when run live: 89.4%

-- TMS Team (Logistics): promised-delivery-date has a 2-day carrier buffer baked in -> more lenient
SELECT ROUND(
    SUM(CASE WHEN FINAL_DELIVERY_DATE <= PROMISED_DELIVERY_DATE THEN 1 ELSE 0 END)
    * 100.0 / COUNT(*), 1
) AS otd_pct
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.DELIVERIES;
-- Result when run live: 91.3%

-- Supplier Portal (Procurement): drops in-transit shipments -> hides the worst cases
SELECT ROUND(
    SUM(CASE WHEN ACTUAL_RECEIPT_DATE <= PLANNED_RECEIPT_DATE THEN 1 ELSE 0 END)
    * 100.0 / COUNT(*), 1
) AS otd_pct
FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.SHIPMENTS
WHERE SHIPMENT_STATUS = 'RECEIVED';
-- Result when run live: 78.6%

-- IoT Team (Warehouse): sensor-detected dock receipt, but only ~70% of shipments
-- carry an active sensor tag -> biased sample, semi-structured VARIANT payload
SELECT DEVICE_TAG, EVENT_PAYLOAD
FROM SUPPLY_CHAIN.SOURCE_IOT_SENSOR.TRACKING_EVENTS;
-- OTD computed from parsed payload events; varies by sensor subset, not comparable 1:1


-- =============================================================================
-- METRIC 2: Fill Rate -- two different concepts entirely, not just different numbers
-- =============================================================================

-- Procurement: supplier-facing PO fill rate (units received vs. units ordered on POs)
SELECT ROUND(SUM(qty_received) / NULLIF(SUM(qty_ordered), 0) * 100, 1) AS fill_rate_pct
FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.purchase_orders;
-- Result when run live: 86.3%

-- Warehouse: unit-level pick fulfillment (units picked vs. units ordered on pick lists)
SELECT ROUND(SUM(units_picked) / NULLIF(SUM(units_ordered), 0) * 100, 1) AS fill_rate_pct
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.pick_operations;
-- Result when run live: 87.7%
-- Deliberately close in value but conceptually different -- one is supplier
-- performance, the other is warehouse execution. The governed semantic view
-- keeps these as two separate canonical measures (customer_fill_rate vs.
-- supplier_fill_rate), not one blended number.


-- =============================================================================
-- METRIC 3: Days of Inventory (DOI) -- three incompatible methodologies
-- =============================================================================

SELECT 'Planning (forecast-based, optimism-bias risk)' AS team,
       ROUND(AVG(inv.current_stock / NULLIF(f.forecasted_daily_demand, 0)), 1) AS doi_days
FROM SUPPLY_CHAIN.GOLD.fact_inventory_snapshot inv
JOIN SUPPLY_CHAIN.SOURCE_ERP.demand_forecast f
    ON inv.part_id = f.part_sku AND DATE_TRUNC('MONTH', inv.snapshot_date) = f.forecast_month
UNION ALL
SELECT 'Finance ($-based, not unit-based)' AS team,
       ROUND(AVG(inv.inventory_value / NULLIF(cogs.daily_cogs, 0)), 1) AS doi_days
FROM SUPPLY_CHAIN.GOLD.fact_inventory_snapshot inv
JOIN SUPPLY_CHAIN.SOURCE_FINANCE.daily_cogs cogs
    ON inv.part_id = cogs.part_id AND inv.snapshot_date = cogs.cogs_date
UNION ALL
SELECT 'Warehouse (30-day trailing ACTUAL demand -- the governed definition)' AS team,
       ROUND(AVG(days_of_inventory), 1) AS doi_days
FROM SUPPLY_CHAIN.GOLD.fact_inventory_snapshot;
-- Result when run live:
--   Planning (forecast-based):        40.1 days
--   Finance ($-based):                506.6 days  <- wildly different SCALE, not just value
--   Warehouse (governed, 30d actual): 48.6 days
-- The Finance number isn't "wrong data" -- it's a genuinely different
-- methodology ($ inventory / $ daily COGS) that happens to produce a number
-- in the same unit ("days") but is not comparable to a units-based DOI.


-- =============================================================================
-- METRIC 4: Landed Cost per Unit -- three different cost stacks
-- =============================================================================

SELECT 'Procurement (PO price + quoted freight only -- understates true cost)' AS team,
       ROUND(AVG(dp.unit_cost + COALESCE(fq.freight_estimate, 0)), 2) AS landed_cost_per_unit
FROM SUPPLY_CHAIN.GOLD.dim_part dp
LEFT JOIN SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.freight_quotes fq ON fq.part_id = dp.part_id
UNION ALL
SELECT 'Logistics (actual freight + customs only -- no purchase price at all)' AS team,
       ROUND(AVG(fi.freight_cost + fi.customs_duty), 2) AS landed_cost_per_unit
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.freight_invoices fi
UNION ALL
SELECT 'Governed (unit cost + freight + customs + handling, per-shipment)' AS team,
       ROUND(AVG(landed_cost_per_unit), 2) AS landed_cost_per_unit
FROM SUPPLY_CHAIN.GOLD.fact_landed_cost;
-- Result when run live:
--   Procurement: $276.40   (missing customs/handling)
--   Logistics:   $488.29   (missing purchase price entirely -- not a real "landed cost")
--   Governed:    $251.68   (full stack, computed at shipment grain)


-- =============================================================================
-- GOVERNED TRUTH: the semantic-view validation query
-- =============================================================================
-- One query, one governed answer per metric -- run this after all four legacy
-- sections above to make the contrast explicit for whoever opens this
-- workspace.
SELECT * FROM SEMANTIC_VIEW(
    SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY
    METRICS
        shipment.on_time_delivery_rate,
        customer_order.customer_fill_rate,
        purchase_order.supplier_fill_rate,
        inventory_snapshot.days_of_inventory,
        landed_cost.landed_cost_per_unit
);
-- Result when run live:
--   on_time_delivery_rate: 64.875%   customer_fill_rate: 90.8%
--   supplier_fill_rate:    86.294%   days_of_inventory:  48.6 days
--   landed_cost_per_unit:  $251.68
-- One query, five governed numbers -- contrast every divergent legacy answer
-- above against this single row.
