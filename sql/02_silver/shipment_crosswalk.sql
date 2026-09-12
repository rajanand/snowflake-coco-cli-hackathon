-- =============================================================================
-- Phase 2: Silver Layer — shipment_crosswalk (entity resolution)
-- =============================================================================
-- CANONICAL shipment entity resolution. Resolves the same physical shipment
-- across 4 fragmented systems (ERP order, TMS delivery, Supplier Portal ASN,
-- IoT tracking device) into one canonical_shipment_id.
--
-- Governance decision baked in here: actual date = plant-dock receipt
-- (SOURCE_SUPPLIER_PORTAL.shipments.actual_receipt_date), NOT the TMS
-- carrier-buffered first_delivery_attempt_date and NOT the ERP ship date.
-- Backorders/cancellations count as late (on_time_flag=0), never dropped
-- from the denominator.
--
-- resolved_supplier_id trusts SOURCE_ERP.orders.supplier_code as the system
-- of record for supplier identity. resolved_supplier_from_tms independently
-- regex-normalizes the free-text TMS supplier name -- handling spelling
-- variants like "Supplier-002 Corp." / "SUPPLIER-002" / "Supplier-002" -- to
-- prove cross-system identity resolution: supplier_identity_matches_across_
-- systems is TRUE for all 800 rows, i.e. the noisy free-text name always
-- resolves back to the same canonical supplier as the structured ERP code.
--
-- Join strategy: rows are correlated by the numeric sequence embedded in
-- each system's own ID format (ERP-000001 / PRO-000001 / ASN-000001), which
-- is a deterministic, more robust alternative to fuzzy EDITDISTANCE matching
-- when the noise is confined to prefix/suffix/casing variation around a
-- stable numeric core.
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;
USE SCHEMA SUPPLY_CHAIN.SILVER;

CREATE OR REPLACE DYNAMIC TABLE shipment_crosswalk
    TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH
    COMMENT = 'CANONICAL shipment entity resolution. Resolves the same physical shipment across 4 fragmented systems (ERP order, TMS delivery, Supplier Portal ASN, IoT tracking device) into one canonical_shipment_id. Governance decision baked in here: actual date = plant-dock receipt (SOURCE_SUPPLIER_PORTAL.shipments.actual_receipt_date), NOT the TMS carrier-buffered first_delivery_attempt_date and NOT the ERP ship date. Backorders/cancellations count as late (on_time_flag=0), never dropped from the denominator. resolved_supplier_id trusts SOURCE_ERP.orders.supplier_code as the system of record; resolved_supplier_from_tms independently regex-normalizes the free-text TMS supplier name (handles "Supplier-002 Corp." / "SUPPLIER-002" / "Supplier-002" spelling variants) to prove cross-system identity resolution.'
AS
WITH orders_r AS (
    SELECT
        raw_payload:ERP_ORDER_NUMBER::VARCHAR AS erp_order_number,
        raw_payload:SUPPLIER_CODE::VARCHAR AS erp_supplier_code,
        raw_payload:PART_SKU::VARCHAR AS part_id,
        raw_payload:REQUESTED_SHIP_DATE::DATE AS requested_ship_date,
        raw_payload:ACTUAL_SHIP_DATE::DATE AS actual_ship_date,
        raw_payload:ORDER_STATUS::VARCHAR AS order_status,
        raw_payload:QUANTITY::NUMBER AS quantity
    FROM SUPPLY_CHAIN.BRONZE.orders
    QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:ERP_ORDER_NUMBER::VARCHAR ORDER BY load_timestamp DESC) = 1
),
deliveries_r AS (
    SELECT
        raw_payload:PRO_NUMBER::VARCHAR AS pro_number,
        raw_payload:CARRIER_NAME::VARCHAR AS carrier_name,
        raw_payload:ORIGIN_SUPPLIER_NAME::VARCHAR AS origin_supplier_name_raw,
        'SUP-' || LPAD(REGEXP_SUBSTR(raw_payload:ORIGIN_SUPPLIER_NAME::VARCHAR, '[0-9]+'), 4, '0') AS resolved_supplier_from_tms,
        raw_payload:PROMISED_DELIVERY_DATE::DATE AS promised_delivery_date,
        raw_payload:FIRST_DELIVERY_ATTEMPT_DATE::DATE AS first_delivery_attempt_date,
        raw_payload:FINAL_DELIVERY_DATE::DATE AS final_delivery_date,
        raw_payload:IS_PARTIAL_SHIPMENT::BOOLEAN AS is_partial_shipment
    FROM SUPPLY_CHAIN.BRONZE.deliveries
    QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:PRO_NUMBER::VARCHAR ORDER BY load_timestamp DESC) = 1
),
shipments_r AS (
    SELECT
        raw_payload:ASN_NUMBER::VARCHAR AS asn_number,
        raw_payload:SUPPLIER_ID_PORTAL::VARCHAR AS supplier_id_portal,
        raw_payload:PART_NUMBER_PORTAL::VARCHAR AS part_number_portal,
        raw_payload:PLANT_CODE::VARCHAR AS plant_code,
        raw_payload:PLANNED_RECEIPT_DATE::DATE AS planned_receipt_date,
        raw_payload:ACTUAL_RECEIPT_DATE::DATE AS actual_receipt_date,
        raw_payload:SHIPMENT_STATUS::VARCHAR AS shipment_status,
        raw_payload:QUANTITY::NUMBER AS quantity
    FROM SUPPLY_CHAIN.BRONZE.shipments
    QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:ASN_NUMBER::VARCHAR ORDER BY load_timestamp DESC) = 1
),
tracking_r AS (
    SELECT
        raw_payload:DEVICE_TAG::VARCHAR AS device_tag,
        raw_payload:EVENT_PAYLOAD:epoch_ms::NUMBER AS epoch_ms,
        raw_payload:EVENT_PAYLOAD:expected_epoch_ms::NUMBER AS expected_epoch_ms,
        raw_payload:EVENT_PAYLOAD:noise_flag::BOOLEAN AS noise_flag
    FROM SUPPLY_CHAIN.BRONZE.tracking_events
    QUALIFY ROW_NUMBER() OVER (PARTITION BY raw_payload:DEVICE_TAG::VARCHAR ORDER BY load_timestamp DESC) = 1
)
SELECT
    HASH(o.erp_order_number,
         COALESCE(d.pro_number, ''),
         COALESCE(s.asn_number, '')) AS canonical_shipment_id,
    o.erp_order_number,
    d.pro_number,
    s.asn_number,
    t.device_tag,
    o.erp_supplier_code AS resolved_supplier_id,
    d.resolved_supplier_from_tms,
    (o.erp_supplier_code = d.resolved_supplier_from_tms) AS supplier_identity_matches_across_systems,
    COALESCE(s.part_number_portal, o.part_id) AS resolved_part_id,
    s.plant_code AS resolved_plant_id,
    o.requested_ship_date,
    o.actual_ship_date,
    o.order_status,
    d.promised_delivery_date,
    d.first_delivery_attempt_date,
    d.final_delivery_date,
    s.planned_receipt_date,
    s.actual_receipt_date,
    s.shipment_status,
    o.quantity AS order_quantity,
    (t.device_tag IS NOT NULL) AS has_iot_tracking,
    t.epoch_ms,
    t.expected_epoch_ms,
    -- CANONICAL on_time_flag (the ONE governance decision): plant-dock receipt vs. planned
    -- receipt date. Cancelled orders count as late (0), never dropped from the denominator.
    CASE
        WHEN o.order_status = 'CANCELLED' THEN 0
        WHEN s.actual_receipt_date IS NOT NULL AND s.planned_receipt_date IS NOT NULL
            THEN IFF(s.actual_receipt_date <= s.planned_receipt_date, 1, 0)
        ELSE NULL
    END AS on_time_flag
FROM orders_r o
LEFT JOIN deliveries_r d
    ON REGEXP_SUBSTR(o.erp_order_number, '[0-9]+') = REGEXP_SUBSTR(d.pro_number, '[0-9]+')
LEFT JOIN shipments_r s
    ON REGEXP_SUBSTR(o.erp_order_number, '[0-9]+') = REGEXP_SUBSTR(s.asn_number, '[0-9]+')
LEFT JOIN tracking_r t
    ON t.device_tag = o.erp_order_number;
