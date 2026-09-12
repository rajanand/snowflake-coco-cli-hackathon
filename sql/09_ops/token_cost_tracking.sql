-- =============================================================================
-- Phase 9: Token/cost tracking + warehouse sizing (System Design & Engineering)
-- =============================================================================
-- "Evidenced with a real number, not asserted" -- every query below was run
-- live; results are recorded in docs/token-and-cost-tracking.md.
--
-- Uses the correct ACCOUNT_USAGE views per the cost-intelligence skill's
-- reference queries (NOT CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY, which doesn't
-- exist -- CORTEX_ANALYST_USAGE_HISTORY and CORTEX_SEARCH_DAILY_USAGE_HISTORY
-- are the real views).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Cortex Analyst credit + request usage (last 30 days)
-- -----------------------------------------------------------------------------
SELECT
    ROUND(SUM(CREDITS), 4) AS total_credits,
    SUM(REQUEST_COUNT) AS total_requests,
    COUNT(DISTINCT USERNAME) AS active_users
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_ANALYST_USAGE_HISTORY
WHERE START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP());
-- Result when run live: 1.1390 credits, 17 requests, 1 active user

-- -----------------------------------------------------------------------------
-- Cortex Search credit + token usage (last 30 days)
-- -----------------------------------------------------------------------------
SELECT
    ROUND(SUM(CREDITS), 4) AS total_credits,
    SUM(TOKENS) AS total_tokens,
    COUNT(DISTINCT SERVICE_NAME) AS active_services
FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_SEARCH_DAILY_USAGE_HISTORY
WHERE USAGE_DATE >= DATEADD('day', -30, CURRENT_DATE());
-- Result when run live: 0.0001 credits, 4132 tokens, 1 active service
-- (SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS -- mostly EMBED_TEXT_TOKENS
-- from initial indexing; the service is currently SUSPENDED for cost control,
-- see sql/09_ops/pause_resume_compute.sql)

-- -----------------------------------------------------------------------------
-- COMPUTE_WH warehouse credit usage (last 30 days)
-- -----------------------------------------------------------------------------
SELECT
    ROUND(SUM(CREDITS_USED), 4)                AS total_credits,
    ROUND(SUM(CREDITS_USED_COMPUTE), 4)         AS compute_credits,
    ROUND(SUM(CREDITS_USED_CLOUD_SERVICES), 4)  AS cloud_services_credits,
    COUNT(*)                                    AS metering_hours
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE WAREHOUSE_NAME = 'COMPUTE_WH'
  AND START_TIME >= DATEADD('day', -30, CURRENT_TIMESTAMP());
-- Result when run live: 8.7947 total credits (8.6269 compute + 0.1679 cloud
-- services) across 14 metering hours over the last 30 days -- almost all of
-- it is medallion Dynamic Table refreshes (28 tables at TARGET_LAG=10-15
-- minutes) plus build-time DDL, not Cortex AI calls (Analyst+Search combined
-- are ~1.14 credits, <13% of the warehouse total).

-- -----------------------------------------------------------------------------
-- Warehouse right-sizing: tighten AUTO_SUSPEND to match the plan's explicit
-- "X-SMALL, AUTO_SUSPEND=60" cost decision (was 300s)
-- -----------------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;
ALTER WAREHOUSE COMPUTE_WH SET AUTO_SUSPEND = 60;
-- Verified live: SHOW WAREHOUSES LIKE 'COMPUTE_WH' -> size=X-Small, auto_suspend=60
