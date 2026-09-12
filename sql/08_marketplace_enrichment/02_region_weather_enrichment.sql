-- =============================================================================
-- Phase 4.5 (Marketplace touchpoint): region-to-weather enrichment
-- =============================================================================
-- The synthetic dim_plant.region values (WEST/SOUTHEAST/MIDWEST/SOUTH/
-- NORTHEAST) have no geocoordinate to join against WEATHER_MARKETPLACE
-- directly. This maps each region to a representative city available in the
-- free Frostbyte listing's coverage, then joins fact_shipment -> dim_plant ->
-- this map -> HISTORY_DAY on ship date, to genuinely test whether late
-- shipments correlate with severe weather at the destination plant's region
-- on the day the shipment moved.
--
-- Coverage limitation (see sql/08_marketplace_enrichment/README.md): the free
-- listing only covers NY/NJ/MA, Denver, and Seattle/Bay Area cities. SOUTH and
-- SOUTHEAST have no representative city in this dataset and are intentionally
-- left unmapped (excluded from the correlation, not force-mapped to a
-- wrong-climate city).
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;

CREATE OR REPLACE TABLE SUPPLY_CHAIN.GOVERNANCE.region_weather_city_map (
    region              VARCHAR(20)   NOT NULL,
    representative_city VARCHAR(65)  NOT NULL,
    postal_code         VARCHAR(20)   NOT NULL,
    country             VARCHAR(2)    NOT NULL,
    mapping_note        VARCHAR(200)
)
COMMENT = 'Maps synthetic dim_plant.region values to a representative US city available in the free WEATHER_MARKETPLACE (Pelmorex Frostbyte) listing, since the synthetic data has no geocoordinate. SOUTH/SOUTHEAST are intentionally absent -- no representative city exists in this free listing''s coverage.';

INSERT INTO SUPPLY_CHAIN.GOVERNANCE.region_weather_city_map VALUES
    ('NORTHEAST', 'New York', '10001', 'US', 'Direct fit -- NYC metro is the best-covered region in the free listing.'),
    ('WEST',      'Seattle',  '98101', 'US', 'Direct fit -- Pacific Northwest / West Coast.'),
    ('MIDWEST',   'Denver',   '80202', 'US', 'Approximate proxy -- Denver is Mountain West, not true Midwest, but is the nearest continental-interior city the free listing covers.');
-- SOUTH and SOUTHEAST deliberately have no row: no Dallas/Houston/Atlanta/
-- Miami/Charlotte-equivalent city exists in this free listing's ~447 US
-- cities. Adding a wrong-climate proxy (e.g. mapping SOUTH to Denver too)
-- would produce a misleading correlation, so those regions are excluded from
-- v_shipment_weather_risk below instead.

CREATE OR REPLACE VIEW SUPPLY_CHAIN.GOLD.v_shipment_weather_risk
COMMENT = 'Marketplace enrichment (Phase 4.5): joins fact_shipment -> dim_plant -> region_weather_city_map -> WEATHER_MARKETPLACE.ONPOINT_ID.HISTORY_DAY on ship date, to test whether late shipments correlate with severe weather at the destination region on the day the shipment moved. Only covers plants in NORTHEAST/WEST/MIDWEST -- see region_weather_city_map comment for why SOUTH/SOUTHEAST are excluded.'
AS
SELECT
    fs.shipment_id,
    fs.supplier_id,
    fs.plant_id,
    dp.region                          AS plant_region,
    fs.actual_ship_date,
    fs.is_on_time,
    hw.avg_temperature_air_2m_f,
    hw.tot_precipitation_in,
    hw.tot_snowfall_in,
    hw.max_wind_speed_10m_mph,
    -- "Severe weather" heuristic: heavy precipitation, meaningful snowfall, or
    -- high sustained wind on the ship date at the destination region.
    IFF(
        hw.tot_precipitation_in >= 1.0
        OR hw.tot_snowfall_in >= 1.0
        OR hw.max_wind_speed_10m_mph >= 25.0,
        TRUE, FALSE
    )                                   AS severe_weather_flag
FROM SUPPLY_CHAIN.GOLD.fact_shipment fs
JOIN SUPPLY_CHAIN.GOLD.dim_plant dp
    ON dp.plant_key = fs.plant_key
JOIN SUPPLY_CHAIN.GOVERNANCE.region_weather_city_map rwm
    ON rwm.region = dp.region
JOIN WEATHER_MARKETPLACE.ONPOINT_ID.HISTORY_DAY hw
    ON hw.postal_code = rwm.postal_code
    AND hw.country = rwm.country
    AND hw.date_valid_std = fs.actual_ship_date;

-- -----------------------------------------------------------------------------
-- Correlation summary: is on-time rate lower on severe-weather ship days?
-- -----------------------------------------------------------------------------
-- SELECT
--     plant_region,
--     severe_weather_flag,
--     COUNT(*)                                   AS shipments,
--     ROUND(AVG(is_on_time) * 100, 1)            AS on_time_pct
-- FROM SUPPLY_CHAIN.GOLD.v_shipment_weather_risk
-- GROUP BY plant_region, severe_weather_flag
-- ORDER BY plant_region, severe_weather_flag;
