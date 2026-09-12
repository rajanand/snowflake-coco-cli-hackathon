-- SOURCE_FINANCE — genuine flaws:
--   1) daily_cogs — DOI methodology differs from Planning's forecast-based view ($-based, not unit-based)
--   2) overhead_allocation — feeds the incomplete Landed Cost cost-assembly divergence (Finance: full stack, ~1 month stale)
USE ROLE SUPPLY_CHAIN_ADMIN;
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SOURCE_FINANCE
    COMMENT = 'Fragmented raw Finance system (daily COGS, overhead allocation). Phase 0 (pre-governance).';

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_FINANCE.daily_cogs (
    part_id VARCHAR(50) COMMENT 'Part identifier, joins to SOURCE_ERP.demand_forecast.part_sku.',
    cogs_date DATE COMMENT 'Cost-of-goods-sold date.',
    daily_cogs NUMBER COMMENT 'Daily cost of goods sold ($) for this part.'
)
COMMENT = 'KNOWN DATA QUALITY ISSUE: Finance''s Days-of-Inventory methodology is dollar-based ($-value / daily COGS), not unit-based like Planning''s forecast — a genuine methodology mismatch, not a data error, resolved as distinct canonical metrics in Phase 4.';

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_FINANCE.overhead_allocation (
    part_category VARCHAR(50) COMMENT 'Part category identifier, format CAT-nn.',
    month DATE COMMENT 'First day of the allocation month.',
    allocated_overhead_per_unit NUMBER COMMENT 'Finance-allocated overhead cost per unit ($) — the piece Procurement/Logistics views of Landed Cost omit.'
)
COMMENT = 'KNOWN DATA QUALITY ISSUE: Finance''s Landed Cost view is the only one with full cost-stack assembly (purchase + freight + customs + overhead) but runs on a ~1-month-stale allocation cycle vs. Procurement/Logistics real-time views.';

-- Daily COGS: 100 parts x 90 days — feeds DOI (Finance methodology) divergence in Phase 3-4.
INSERT INTO SUPPLY_CHAIN.SOURCE_FINANCE.daily_cogs (part_id, cogs_date, daily_cogs)
WITH parts AS (
  SELECT 'PART-' || LPAD(SEQ4()+1,5,'0') AS part_id FROM TABLE(GENERATOR(ROWCOUNT=>100))
),
days AS (
  SELECT DATEADD(day, -SEQ4(), CURRENT_DATE()) AS cogs_date FROM TABLE(GENERATOR(ROWCOUNT=>90))
)
SELECT part_id, cogs_date, UNIFORM(100,5000,RANDOM()) AS daily_cogs
FROM parts CROSS JOIN days;

-- Overhead allocation: 10 part categories x 6 months — feeds Landed Cost (Finance: full stack).
INSERT INTO SUPPLY_CHAIN.SOURCE_FINANCE.overhead_allocation (part_category, month, allocated_overhead_per_unit)
WITH cats AS (
  SELECT 'CAT-' || LPAD(SEQ4()+1,2,'0') AS part_category FROM TABLE(GENERATOR(ROWCOUNT=>10))
),
months AS (
  SELECT DATE_TRUNC(month, DATEADD(month, -SEQ4(), CURRENT_DATE())) AS month FROM TABLE(GENERATOR(ROWCOUNT=>6))
)
SELECT part_category, month, UNIFORM(1,20,RANDOM())
FROM cats CROSS JOIN months;

-- Legacy query — DOI as Finance sees it ($-based, not unit-based) — requires GOLD.fact_inventory_snapshot (Phase 3)
-- SELECT inv.part_id, inv.inventory_value / NULLIF(cogs.daily_cogs, 0) AS doi_finance
-- FROM SUPPLY_CHAIN.GOLD.fact_inventory_snapshot inv JOIN SUPPLY_CHAIN.SOURCE_FINANCE.daily_cogs cogs ON inv.part_id = cogs.part_id;
