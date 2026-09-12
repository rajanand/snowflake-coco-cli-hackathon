-- =============================================================================
-- Phase 4: The Ontology, Encoded as a Governed Semantic View
-- =============================================================================
-- Native CREATE SEMANTIC VIEW object (not YAML-only) over the GOLD dimensional
-- model. Every metric COMMENT documents the governance decision that resolved
-- the cross-team disagreement demonstrated in Phase 0.
--
-- IMPORTANT alias direction: in FACTS/DIMENSIONS clauses, the syntax is
-- `<table>.<new_semantic_name> AS <physical_column>` -- i.e. the NEW name
-- comes first, the underlying column comes after AS. This is the opposite
-- direction from a normal SQL SELECT alias and easy to get backwards.
-- =============================================================================

USE ROLE SUPPLY_CHAIN_ADMIN;

CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SEMANTIC_MODELS
    COMMENT = 'Phase 4: governed business/consumption layer. Native SEMANTIC VIEW + Cortex Search + Cortex Analyst. Kept separate from GOLD for grant isolation -- agents/BI tools can be granted access to this schema only, without exposure to raw dimensional tables.';

ALTER SCHEMA SUPPLY_CHAIN.SEMANTIC_MODELS SET TAG SUPPLY_CHAIN.GOVERNANCE.LIFECYCLE = 'GOVERNED_SEMANTIC';

CREATE OR REPLACE SEMANTIC VIEW SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY
  TABLES (
    supplier AS SUPPLY_CHAIN.GOLD.dim_supplier PRIMARY KEY (supplier_key) WITH SYNONYMS ('vendor','seller') COMMENT = 'Supplier master data, resolved from fragmented Phase 0 systems.',
    part AS SUPPLY_CHAIN.GOLD.dim_part PRIMARY KEY (part_key) WITH SYNONYMS ('sku','material','component') COMMENT = 'Parts/materials master data.',
    plant AS SUPPLY_CHAIN.GOLD.dim_plant PRIMARY KEY (plant_key) WITH SYNONYMS ('facility','warehouse','distribution center') COMMENT = 'Plant/distribution-center master data.',
    customer AS SUPPLY_CHAIN.GOLD.dim_customer PRIMARY KEY (customer_key) WITH SYNONYMS ('account','client') COMMENT = 'Customer master data.',
    shipment AS SUPPLY_CHAIN.GOLD.fact_shipment PRIMARY KEY (shipment_id) WITH SYNONYMS ('delivery','inbound shipment') COMMENT = 'Canonical resolved shipment (entity-resolved via SILVER.shipment_crosswalk across ERP/TMS/Supplier-Portal/IoT).',
    customer_order AS SUPPLY_CHAIN.GOLD.fact_order_fulfillment PRIMARY KEY (customer_order_id) WITH SYNONYMS ('order','sales order') COMMENT = 'Canonical customer order fulfillment.',
    purchase_order AS SUPPLY_CHAIN.GOLD.fact_purchase_order PRIMARY KEY (po_number) WITH SYNONYMS ('po') COMMENT = 'Canonical supplier-facing purchase order.',
    inventory_snapshot AS SUPPLY_CHAIN.GOLD.fact_inventory_snapshot PRIMARY KEY (snapshot_id) WITH SYNONYMS ('inventory','stock') COMMENT = 'Canonical part-plant-day inventory snapshot.',
    landed_cost AS SUPPLY_CHAIN.GOLD.fact_landed_cost PRIMARY KEY (shipment_id) WITH SYNONYMS ('true cost detail') COMMENT = 'Canonical full-stack landed cost per shipment.'
  )
  RELATIONSHIPS (
    shipment_to_supplier AS shipment (supplier_key) REFERENCES supplier (supplier_key),
    shipment_to_part AS shipment (part_key) REFERENCES part (part_key),
    shipment_to_plant AS shipment (plant_key) REFERENCES plant (plant_key),
    order_to_part AS customer_order (part_key) REFERENCES part (part_key),
    order_to_customer AS customer_order (customer_key) REFERENCES customer (customer_key),
    po_to_supplier AS purchase_order (supplier_key) REFERENCES supplier (supplier_key),
    po_to_part AS purchase_order (part_key) REFERENCES part (part_key),
    inventory_to_plant AS inventory_snapshot (plant_key) REFERENCES plant (plant_key),
    inventory_to_part AS inventory_snapshot (part_key) REFERENCES part (part_key),
    landed_cost_to_shipment AS landed_cost (shipment_id) REFERENCES shipment (shipment_id)
  )
  FACTS (
    shipment.shipment_is_on_time AS is_on_time,
    shipment.shipment_value AS value_usd,
    customer_order.order_on_time_flag AS on_time_flag,
    customer_order.order_fill_flag AS fill_flag
  )
  DIMENSIONS (
    supplier.tier_name AS tier_name WITH SYNONYMS ('supplier category','vendor tier'),
    supplier.supplier_region AS region WITH SYNONYMS ('vendor location','supplier geography'),
    part.category AS category WITH SYNONYMS ('part type','commodity group'),
    plant.plant_region AS region WITH SYNONYMS ('facility location','plant geography'),
    customer.customer_segment AS customer_segment WITH SYNONYMS ('account tier','customer type')
  )
  METRICS (
    shipment.on_time_delivery_rate AS
      (SUM(CASE WHEN shipment_is_on_time = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(shipment_id), 0)) * 100
      WITH SYNONYMS ('OTD','OTD%','on-time %','delivery performance','are we hitting delivery dates','schedule adherence')
      COMMENT = 'CANONICAL. Actual date = plant-dock receipt (SILVER.shipment_crosswalk governance decision). Cancelled orders count as late, never dropped from the denominator.',
    customer_order.customer_fill_rate AS
      (SUM(CASE WHEN order_fill_flag = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(customer_order_id), 0)) * 100
      WITH SYNONYMS ('fill rate','order fill rate','perfect order rate','orders shipped complete')
      COMMENT = 'CANONICAL customer-facing fill rate: order-binary (qty_shipped >= qty_ordered). Distinct from supplier_fill_rate and warehouse_unit_fill_rate.',
    purchase_order.supplier_fill_rate AS
      (SUM(qty_received) / NULLIF(SUM(qty_ordered), 0)) * 100
      WITH SYNONYMS ('PO fill','supplier fulfillment rate','vendor fill rate')
      COMMENT = 'CANONICAL supplier-facing PO fill rate. Deliberately a separate measure from customer_fill_rate -- opposite direction of flow (supplier-to-us, not us-to-customer).',
    inventory_snapshot.days_of_inventory AS
      AVG(current_stock / NULLIF(trailing_30d_avg_actual_demand, 0))
      WITH SYNONYMS ('DOI','days on hand','stock coverage','inventory coverage')
      COMMENT = 'CANONICAL. 30-day trailing ACTUAL demand (avg_daily_usage_qty) -- not forecast, not $-based, not a 7-day window.',
    landed_cost.landed_cost_per_unit AS
      AVG(landed_cost_per_unit)
      WITH SYNONYMS ('true cost','total unit cost','fully loaded cost','all-in cost')
      COMMENT = 'CANONICAL. unit_cost + freight_cost_per_unit + customs_duty_per_unit + handling_fee_per_unit, computed at shipment grain as data arrives -- not a monthly batch, not missing any cost component.'
  )
  COMMENT = 'Governed supply chain ontology. Every measure comment documents the governance decision that resolved cross-team disagreement between ERP/Planning, TMS/Logistics, Supplier Portal/Procurement, IoT/Warehouse, and Finance.';

-- -----------------------------------------------------------------------------
-- Validation queries -- directly queryable, real Snowflake object
-- -----------------------------------------------------------------------------

-- All four headline metrics in one query (no fan-out: every metric's fact
-- table has a 1:1 or clean many-to-one path back through the relationship
-- graph, so combining them doesn't distort any individual metric)
SELECT * FROM SEMANTIC_VIEW(
  SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY
  METRICS shipment.on_time_delivery_rate, customer_order.customer_fill_rate,
          purchase_order.supplier_fill_rate, inventory_snapshot.days_of_inventory,
          landed_cost.landed_cost_per_unit
);

-- OTD broken down by supplier tier and region
SELECT * FROM SEMANTIC_VIEW(
  SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY
  DIMENSIONS supplier.tier_name, supplier.supplier_region
  METRICS shipment.on_time_delivery_rate
) ORDER BY 1, 2;
