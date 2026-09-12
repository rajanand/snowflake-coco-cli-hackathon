-- SOURCE_IOT_SENSOR — genuine flaw: only 70% sensor coverage, epoch-millis VARIANT payload with noise
USE ROLE SUPPLY_CHAIN_ADMIN;
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SOURCE_IOT_SENSOR
    COMMENT = 'Fragmented raw IoT sensor telemetry for in-transit shipment tracking. Phase 0 (pre-governance).';

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_IOT_SENSOR.tracking_events (
    device_tag VARCHAR(50) COMMENT 'Sensor device tag, format ERP-nnnnnn — matches SOURCE_ERP.orders.erp_order_number 1:1 where sensor coverage exists.',
    event_payload VARIANT COMMENT 'KNOWN DATA QUALITY ISSUE: semi-structured epoch-millis payload (epoch_ms, expected_epoch_ms, sensor_battery_pct, noise_flag) with device-level timing noise. Only 70% of shipments have any row here — a biased, incomplete sample.',
    load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() COMMENT 'Row load time.'
)
COMMENT = 'KNOWN DATA QUALITY ISSUE: only 70% sensor coverage — the IoT dashboard''s OTD% is computed over a biased subset of shipments, not the full population.';

-- ── Synthetic data: only 70% of the 800 correlated shipments have sensor coverage (biased sample).
-- Target: IoT OTD ~84% among covered rows.
INSERT INTO SUPPLY_CHAIN.SOURCE_IOT_SENSOR.tracking_events (device_tag, event_payload)
WITH base AS (
  SELECT SEQ4() + 1 AS i FROM TABLE(GENERATOR(ROWCOUNT=>800))
),
covered AS (
  SELECT i FROM base WHERE MOD(i,10) < 7  -- 70% coverage
),
attrs AS (
  SELECT
    i,
    'ERP-' || LPAD(i,6,'0') AS device_tag,
    DATE_PART(epoch_second, DATEADD(day, -MOD(i,180), CURRENT_TIMESTAMP())) * 1000 AS expected_epoch_ms,
    UNIFORM(0::FLOAT,1::FLOAT,RANDOM()) AS ontime_roll,
    UNIFORM(3600000,432000000,RANDOM()) AS late_ms,
    UNIFORM(0,500,RANDOM()) AS early_ms
  FROM covered
)
SELECT
  device_tag,
  OBJECT_CONSTRUCT(
    'epoch_ms', CASE WHEN ontime_roll < 0.84 THEN (expected_epoch_ms - early_ms) ELSE (expected_epoch_ms + late_ms) END,
    'expected_epoch_ms', expected_epoch_ms,
    'sensor_battery_pct', UNIFORM(20,100,RANDOM()),
    'noise_flag', TRUE
  ) AS event_payload
FROM attrs;

-- Legacy query — OTD as the IoT dashboard sees it (only 70% sensor coverage → biased sample)
-- SELECT ROUND(SUM(CASE WHEN event_payload:epoch_ms::NUMBER <= event_payload:expected_epoch_ms::NUMBER THEN 1 ELSE 0 END)
--        / NULLIF(COUNT(*),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_IOT_SENSOR.tracking_events;
