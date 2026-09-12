-- =============================================================================
-- Phase 4.5 (Marketplace touchpoint): acquire a free weather dataset
-- =============================================================================
-- Purpose: genuine Marketplace-sourced enrichment (not just a namecheck) for
-- the "are late shipments correlated with severe weather at the destination
-- on the ship date?" analysis in 02_region_weather_enrichment.sql.
--
-- Listing chosen: "Pelmorex Weather Source: Frostbyte" (global_name GZSOZ1LLEL)
--   - Free (is_monetized = false), instantly available (is_ready_for_import =
--     true), all regions -- picked live via `SHOW AVAILABLE LISTINGS` rather
--     than hardcoding a search result, since availability/global names can
--     change.
--   - This is Pelmorex Weather Source's standard free hands-on-lab sample
--     dataset (used across multiple official Snowflake quickstarts), not a
--     synthetic/toy dataset -- it's real historical daily weather observations.
--   - License: Snowflake Marketplace standard consumer terms, accepted via
--     SYSTEM$ACCEPT_LEGAL_TERMS below. No cost, no usage restrictions beyond
--     the standard Marketplace listing terms.
-- =============================================================================

-- 1. Find the listing live (global names/availability can change over time --
--    don't trust a hardcoded value from an old search result).
SHOW AVAILABLE LISTINGS;
SELECT "global_name", "title", "is_monetized", "is_by_request", "is_ready_for_import", "regions"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
WHERE "title" ILIKE '%weather%'
ORDER BY "is_monetized", "title";
-- -> confirmed GZSOZ1LLEL ("Pelmorex Weather Source: Frostbyte"): free,
--    is_ready_for_import = true, regions = ALL.

-- 2. Request it (no-op / instant if already ready-for-import in this region).
USE ROLE ACCOUNTADMIN;
CALL SYSTEM$REQUEST_LISTING_AND_WAIT('GZSOZ1LLEL');

-- 3. Accept the listing's legal terms (one-time per account).
CALL SYSTEM$ACCEPT_LEGAL_TERMS('DATA_EXCHANGE_LISTING', 'GZSOZ1LLEL');

-- 4. Create the database from the listing.
CREATE DATABASE IF NOT EXISTS WEATHER_MARKETPLACE FROM LISTING 'GZSOZ1LLEL';

-- -----------------------------------------------------------------------------
-- What's inside: WEATHER_MARKETPLACE.ONPOINT_ID
-- -----------------------------------------------------------------------------
-- POSTAL_CODES(postal_code, city_name, country)                -- ~447 US cities
-- HISTORY_DAY(postal_code, country, date_valid_std, ... 50+ daily weather
--             metrics incl. avg/min/max temperature, precipitation, wind,
--             cloud cover). Confirmed live: US coverage = 2019-01-01 to
--             2026-09-11, which fully overlaps SUPPLY_CHAIN.GOLD.fact_shipment's
--             ship-date range (2026-03-17 to 2026-09-12).
--
-- Known coverage limitation of this FREE listing (documented, not silently
-- worked around): the ~447 US cities are concentrated in NY/NJ/MA metro,
-- the Denver area, and the Seattle/Bay Area -- there is no South, Southeast,
-- or additional Midwest coverage (no Chicago, Dallas, Atlanta, Houston,
-- Miami, etc.). See README.md for how this shapes the region mapping in
-- 02_region_weather_enrichment.sql. Full nationwide coverage would require
-- the paid "Global Weather & Climate Data by Pelmorex Weather Source" listing.
