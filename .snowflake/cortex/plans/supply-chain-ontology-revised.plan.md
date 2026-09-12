# Supply Chain Ontology & Governed Conversational Analytics — Master Plan

## Naming Convention

All fragmented source-system schemas use a `SOURCE_` prefix for consistency and easy identification: `SOURCE_ERP`, `SOURCE_LOGISTICS_TMS`, `SOURCE_SUPPLIER_PORTAL`, `SOURCE_IOT_SENSOR`, `SOURCE_FINANCE`.

**Why `SEMANTIC_MODELS` and `AUTOMATION` stay as separate schemas (not folded into GOLD):**
- `SEMANTIC_MODELS` is the governed business/consumption layer (semantic view, Cortex Search, Cortex Analyst) — separating it means agents/BI tools can be granted access to *this* schema only, without exposure to raw dimensional tables in GOLD. It also keeps the medallion story visually clean: `SHOW SCHEMAS` reads as BRONZE→SILVER→GOLD→SEMANTIC_MODELS, one schema per architectural layer.
- `AUTOMATION` holds operational state (Task-populated snapshots, alert history) — different in kind from canonical facts/dims, different grants (task-execution roles vs. read-only analytics roles), different lifecycle (logs, not a dimensional model). Keeping it separate avoids muddying GOLD's purpose.

## Headline Story (opens and closes the demo)

```
Supplier ──ships──▶ Part ──delivered to──▶ Plant ──fulfills──▶ CustomerOrder ──placed by──▶ Customer
```
Today, three teams ask "What's our on-time delivery rate?" against three real, disconnected systems and get three genuinely different, defensible-looking answers. We fix this by resolving the ontology once (Bronze→Silver→Gold→Semantic View) and proving — live, with generated SQL on screen — that every persona, phrased any way, now gets the identical answer.

**Judging-criteria mapping (closing slide):**
- **Real World Relevance** — fragmentation is modeled on genuine root causes (carrier buffers, dropped denominators, forecast-vs-actual, incomplete cost assembly), not arbitrary numbers.
- **Technical Execution** — Dynamic Tables medallion architecture, native `SEMANTIC VIEW` with synonyms, entity-resolution crosswalk, hybrid multi-agent router with hooks, Tasks/automation.
- **Solution Completeness** — fragmented sources → governed answer → conversational agent → real-time demo → automation/alerts → reusable skill → multi-surface deployment.

---

## Database Structure

```
SUPPLY_CHAIN (Database)
├── SOURCE_ERP, SOURCE_LOGISTICS_TMS, SOURCE_SUPPLIER_PORTAL, SOURCE_IOT_SENSOR, SOURCE_FINANCE   (Phase 0: fragmented raw systems)
├── BRONZE          (Phase 1: unified raw landing, source-shaped, VARIANT)
├── SILVER          (Phase 2: canonical/conformed, Dynamic Tables, entity resolution)
├── GOLD            (Phase 3: dimensional model — fact/dim/bridge/agg, Dynamic Tables)
├── SEMANTIC_MODELS (Phase 4: native SEMANTIC VIEW + Cortex Search + Cortex Analyst — separate for grant isolation)
└── AUTOMATION      (Phase 8: Tasks, alert snapshots, daily health metrics — separate: operational state, not dimensional model)
```

---

## Phase 0: Genuine Fragmentation (2h)

Four teams' real systems, each with a genuine definitional or data-quality flaw — not staged numbers.

**Schemas & tables:**
- `SOURCE_ERP.orders` (key: `erp_order_number`) — excludes cancelled/backorder rows from OTD denominator (inflates)
- `SOURCE_LOGISTICS_TMS.deliveries` (key: `pro_number`) — 2-day carrier buffer baked into "promised date"; free-text supplier names (spelling variants) create a real entity-resolution problem
- `SOURCE_SUPPLIER_PORTAL.shipments` (key: `asn_number`) — drops in-transit/currently-late shipments from denominator entirely
- `SOURCE_IOT_SENSOR.tracking_events` (key: `device_tag`) — only 70% sensor coverage, epoch-millis VARIANT payload with noise
- `SOURCE_SUPPLIER_PORTAL.purchase_orders` + `SOURCE_LOGISTICS_TMS.pick_operations` — for Fill Rate divergence (supplier-fulfilling-us vs. unit-level vs. customer-facing)
- `SOURCE_ERP.demand_forecast` + `SOURCE_FINANCE.daily_cogs` — for DOI divergence (forecast vs. financial vs. trailing-actuals methodology)
- `SOURCE_LOGISTICS_TMS.freight_invoices` + `SOURCE_FINANCE.overhead_allocation` — for Landed Cost divergence (incomplete cost assembly per team)

```sql
CREATE DATABASE IF NOT EXISTS SUPPLY_CHAIN;
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SOURCE_ERP;
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS;
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL;
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SOURCE_IOT_SENSOR;
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.SOURCE_FINANCE;

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_ERP.orders (
    erp_order_number VARCHAR(50), supplier_code VARCHAR(50), part_sku VARCHAR(50),
    requested_ship_date DATE, actual_ship_date DATE, order_status VARCHAR(30),
    quantity NUMBER, load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.deliveries (
    pro_number VARCHAR(50), carrier_name VARCHAR(100), origin_supplier_name VARCHAR(200),
    promised_delivery_date DATE, first_delivery_attempt_date DATE, final_delivery_date DATE,
    is_partial_shipment BOOLEAN, load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.shipments (
    asn_number VARCHAR(50), supplier_id_portal VARCHAR(50), part_number_portal VARCHAR(50),
    plant_code VARCHAR(20), planned_receipt_date DATE, actual_receipt_date DATE,
    shipment_status VARCHAR(30), quantity NUMBER, load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_IOT_SENSOR.tracking_events (
    device_tag VARCHAR(50), event_payload VARIANT, load_timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.purchase_orders (
    po_number VARCHAR(50), supplier_id_portal VARCHAR(50), part_number_portal VARCHAR(50),
    qty_ordered NUMBER, qty_received NUMBER, po_status VARCHAR(30)
);

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.pick_operations (
    pick_id VARCHAR(50), customer_order_ref VARCHAR(50), units_ordered NUMBER, units_picked NUMBER
);

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_ERP.demand_forecast (
    part_sku VARCHAR(50), forecast_month DATE, forecasted_daily_demand NUMBER
);

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_FINANCE.daily_cogs (
    part_id VARCHAR(50), cogs_date DATE, daily_cogs NUMBER
);

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.freight_invoices (
    invoice_number VARCHAR(50), pro_number VARCHAR(50), freight_cost NUMBER,
    customs_duty NUMBER, invoice_date DATE
);

CREATE OR REPLACE TABLE SUPPLY_CHAIN.SOURCE_FINANCE.overhead_allocation (
    part_category VARCHAR(50), month DATE, allocated_overhead_per_unit NUMBER
);
```

**Synthetic data (generate via CoCo):** ~800 ground-truth physical shipments projected into 2-4 source tables each with deliberate ID divergence and completeness gaps, tuned so live legacy queries produce a believable spread per metric:
- OTD: ERP ~90%, TMS ~93%, Supplier Portal ~78%, IoT ~84%
- Fill Rate: Customer-facing ~91%, Supplier-facing PO fill ~85%, Unit-level ~88% (three different concepts, not just different numbers)
- DOI: Planning (forecast) vs. Finance (COGS-based) vs. Warehouse (7-day trailing) — deliberately different methodologies
- Landed Cost: Procurement (PO+quoted freight only) vs. Logistics (actual freight+customs, no purchase price) vs. Finance (full stack, ~1 month stale)

**Entity resolution crosswalk (Silver):**
```sql
CREATE OR REPLACE DYNAMIC TABLE SUPPLY_CHAIN.SILVER.shipment_crosswalk
TARGET_LAG = '5 MINUTES' WAREHOUSE = COMPUTE_WH AS
SELECT
    HASH(e.erp_order_number, t.pro_number, s.asn_number) AS canonical_shipment_id,
    e.erp_order_number, t.pro_number, s.asn_number, i.device_tag,
    sup.supplier_id AS resolved_supplier_id,
    COALESCE(s.part_number_portal, e.part_sku) AS resolved_part_id
FROM SUPPLY_CHAIN.SOURCE_ERP.orders e
LEFT JOIN SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.shipments s
    ON e.part_sku = s.part_number_portal AND ABS(DATEDIFF(day, e.requested_ship_date, s.planned_receipt_date)) <= 1
LEFT JOIN SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.deliveries t
    ON ABS(DATEDIFF(day, e.requested_ship_date, t.promised_delivery_date)) <= 3
LEFT JOIN SUPPLY_CHAIN.SILVER.suppliers sup
    ON EDITDISTANCE(UPPER(TRIM(t.origin_supplier_name)), UPPER(sup.supplier_name)) <= 3
LEFT JOIN SUPPLY_CHAIN.SOURCE_IOT_SENSOR.tracking_events i ON i.device_tag = e.erp_order_number;
```

**The "legacy queries"** (run live in Streamlit's Before tab, per metric, with an expander showing SQL + plain-English "why it diverges"):
```sql
-- OTD — Planning/ERP (excludes cancelled/backorder rows → inflated)
SELECT ROUND(SUM(CASE WHEN actual_ship_date <= requested_ship_date THEN 1 ELSE 0 END)
       / NULLIF(COUNT(*),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_ERP.orders WHERE order_status = 'COMPLETE';

-- OTD — Logistics/TMS (2-day carrier buffer baked in → more lenient)
SELECT ROUND(SUM(CASE WHEN first_delivery_attempt_date <= promised_delivery_date THEN 1 ELSE 0 END)
       / NULLIF(COUNT(*),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.deliveries;

-- OTD — Procurement/Supplier Portal (drops in-transit → hides the worst cases)
SELECT ROUND(SUM(CASE WHEN actual_receipt_date <= planned_receipt_date THEN 1 ELSE 0 END)
       / NULLIF(COUNT(*),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.shipments WHERE shipment_status = 'RECEIVED';

-- OTD — IoT Dashboard (only 70% sensor coverage → biased sample)
SELECT ROUND(SUM(CASE WHEN event_payload:epoch_ms::NUMBER <= event_payload:expected_epoch_ms::NUMBER THEN 1 ELSE 0 END)
       / NULLIF(COUNT(*),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_IOT_SENSOR.tracking_events;

-- Fill Rate — Procurement (supplier-facing PO fill, opposite direction from customer fill rate)
SELECT ROUND(SUM(qty_received) / NULLIF(SUM(qty_ordered),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.purchase_orders;

-- Fill Rate — Warehouse (unit-level, continuous, not order-binary)
SELECT ROUND(SUM(units_picked) / NULLIF(SUM(units_ordered),0) * 100, 1) FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.pick_operations;

-- DOI — Planning (forecast-based, optimism-bias risk)
SELECT inv.part_id, inv.current_stock / NULLIF(f.forecasted_daily_demand, 0) AS doi_planning
FROM SUPPLY_CHAIN.GOLD.fact_inventory_snapshot inv JOIN SUPPLY_CHAIN.SOURCE_ERP.demand_forecast f ON inv.part_id = f.part_sku;

-- DOI — Finance ($-based, not unit-based)
SELECT inv.part_id, inv.inventory_value / NULLIF(cogs.daily_cogs, 0) AS doi_finance
FROM SUPPLY_CHAIN.GOLD.fact_inventory_snapshot inv JOIN SUPPLY_CHAIN.SOURCE_FINANCE.daily_cogs cogs ON inv.part_id = cogs.part_id;

-- Landed Cost — Procurement (PO price + quoted freight only, understates true cost)
SELECT p.part_id, p.unit_cost + COALESCE(quote.freight_estimate, 0) AS landed_cost_procurement
FROM SUPPLY_CHAIN.SILVER.parts p LEFT JOIN SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.freight_quotes quote ON p.part_id = quote.part_id;

-- Landed Cost — Logistics (actual freight+customs, no purchase price — per-shipment not per-unit)
SELECT t.pro_number, fi.freight_cost + fi.customs_duty AS shipment_cost_logistics
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.deliveries t JOIN SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.freight_invoices fi ON t.pro_number = fi.pro_number;
```

---

## Phase 1-3: Medallion Layers for Remaining Entities (7h)

- **Bronze**: unified raw landing for parts, plants, customer_orders, inventory, quality_events, invoices — source-shaped, VARIANT columns for semi-structured payloads (tracking_events, specifications, contact_info), `_metadata` OBJECT column, tagged by `source_system`.
- **Silver**: Dynamic Tables (`TARGET_LAG = '5 MINUTES'`), type-cast, deduplicated (`QUALIFY ROW_NUMBER()...=1`), VARIANT flattened, canonical `on_time_flag` applied via the ONE governance decision (plant-dock receipt as source of truth; backorders count as late, not dropped; no artificial buffers).
- **Gold**: Dynamic Tables (`TARGET_LAG = '10 MINUTES'`) — `dim_supplier` (SCD2), `dim_part`, `dim_plant`, `dim_customer`, `dim_date`; `fact_shipment`, `fact_order_fulfillment`, `fact_inventory_snapshot`, `fact_quality_event`; `bridge_supplier_part`; `agg_supplier_performance` (pre-aggregated, `TARGET_LAG='15 MINUTES'`).
- Synthetic data generated via CoCo prompts for referential integrity (500 suppliers, 2000 parts, 50 plants, 10,000 shipments, 20,000 orders, 5,000 quality events).

---

## Phase 4: The Ontology, Encoded as a Governed Semantic View (4h)

### Entities (9), Relationships, Hierarchies

| Entity | Grain |
|---|---|
| Supplier, Part, Plant, Shipment, CustomerOrder, Customer, Inventory, QualityEvent, Invoice | one row per supplier / SKU / facility / delivery / order-line / customer / part-plant-day / defect / cost-doc |

Key relationships: Supplier↔Part (many-to-many via bridge), Shipment→Invoice (0-or-1 — the gap causing Landed Cost fragmentation), CustomerOrder→Part (the join path enabling at-risk-order queries).

Hierarchies: Supplier (→Tier→Region), Part (→Category), Geography (Plant/Supplier→Country→Region), Customer (→Segment), Time (Date→Week→Month→Quarter→Year).

### Native Semantic View (not YAML-only — a real, queryable Snowflake object)

```sql
CREATE OR REPLACE SEMANTIC VIEW SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY
  TABLES (
    supplier AS SUPPLY_CHAIN.GOLD.dim_supplier PRIMARY KEY (supplier_id) WITH SYNONYMS ('vendor','seller'),
    part AS SUPPLY_CHAIN.GOLD.dim_part PRIMARY KEY (part_id) WITH SYNONYMS ('sku','material','component'),
    shipment AS SUPPLY_CHAIN.GOLD.fact_shipment PRIMARY KEY (shipment_id) WITH SYNONYMS ('delivery','inbound shipment'),
    customer_order AS SUPPLY_CHAIN.GOLD.fact_order_fulfillment PRIMARY KEY (customer_order_id) WITH SYNONYMS ('order','sales order')
  )
  RELATIONSHIPS (
    shipment_to_supplier AS shipment (supplier_id) REFERENCES supplier (supplier_id),
    shipment_to_part AS shipment (part_id) REFERENCES part (part_id),
    order_to_part AS customer_order (part_id) REFERENCES part (part_id)
  )
  FACTS ( shipment.is_on_time AS on_time_flag, shipment.value_usd AS shipment_value )
  DIMENSIONS (
    supplier.tier_name WITH SYNONYMS ('supplier category','vendor tier'),
    supplier.region WITH SYNONYMS ('vendor location','geography'),
    part.category WITH SYNONYMS ('part type','commodity group'),
    customer_order.customer_segment WITH SYNONYMS ('account tier','customer type')
  )
  METRICS (
    shipment.on_time_delivery_rate AS
      (SUM(CASE WHEN is_on_time = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(shipment_id), 0)) * 100
      WITH SYNONYMS ('OTD','OTD%','on-time %','delivery performance','are we hitting delivery dates','schedule adherence')
      COMMENT = 'CANONICAL. Actual date = plant-dock receipt. Excludes true cancellations only.',
    customer_order.customer_fill_rate AS
      (SUM(CASE WHEN on_time_flag = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(customer_order_id), 0)) * 100
      WITH SYNONYMS ('fill rate','order fill rate','perfect order rate','orders shipped complete')
      COMMENT = 'CANONICAL customer-facing fill rate. Distinct from SupplierFillRate.',
    customer_order.supplier_fill_rate AS (SUM(qty_received) / NULLIF(SUM(qty_ordered), 0)) * 100
      WITH SYNONYMS ('PO fill','supplier fulfillment rate')
      COMMENT = 'CANONICAL supplier-facing. Deliberately a separate measure from customer_fill_rate.',
    shipment.days_of_inventory AS AVG(current_stock / NULLIF(trailing_30d_avg_actual_demand, 0))
      WITH SYNONYMS ('DOI','days on hand','stock coverage')
      COMMENT = 'CANONICAL. 30-day trailing ACTUAL demand — not forecast, not 7-day window.',
    shipment.landed_cost_per_unit AS AVG(unit_cost + freight_cost_per_unit + customs_duty_per_unit + handling_fee_per_unit)
      WITH SYNONYMS ('true cost','total unit cost','fully loaded cost','all-in cost')
      COMMENT = 'CANONICAL. Computed at shipment grain as data arrives, not monthly batch.'
  )
  COMMENT = 'Governed supply chain ontology. Every measure comment documents the governance decision that resolved cross-team disagreement.';
```

Directly queryable for validation: `SELECT * FROM SEMANTIC_VIEW(SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY DIMENSIONS supplier.tier_name METRICS shipment.on_time_delivery_rate);`

**Validate with `reflect_semantic_model` before wiring to Cortex Analyst** — catches synonym collisions and dangling relationships.

**Verified queries** (golden test questions, pointed at the resolved Gold layer):
1. `at_risk_orders_due_to_supplier_delays`
2. `what_if_supplier_delay` (parameterized: supplier + delay days)
3. `root_cause_order_at_risk` (parameterized: order id) — this is the literal "walk the ontology chain" query for the headline story

**Cortex Search** (`supply_chain_documents`) over `AI_PARSE_DOCUMENT`-parsed supplier contract PDFs (payment terms, SLA penalty clauses) — feeds the post-query enrichment hook.

**Cortex Analyst** deployed on this semantic view with a system prompt enforcing canonical-definition usage and persona-aware framing without changing which measure is queried.

---

## Phase 5: Hybrid Multi-Agent Router (5h)

`agents/agent_router.py`:
- `PreQueryValidator` — entity/forbidden-term/length/language checks before any query runs
- `PostQueryEnricher` — extracts supplier names from answers, pulls matching Cortex Search document snippets, appends as "Supporting Evidence"
- `SupplyChainAgentRouter` — classifies intent (standard / document_qa / what_if / root_cause / at_risk) and routes to:
  - Main Cortex Analyst (standard) — returns structured `{text, sql, confidence}`, not just narrative text, so we can display generated SQL and extract `base_table`/`measure_name` via `sqlglot` for the consistency-proof UI
  - `DocumentQAAgent`, `SimulationAgent` (what-if delay impact), `EvidenceTraceAgent` (root-cause evidence trail)
- **Confidence-threshold fallback**: if Cortex Analyst confidence is low, respond "I'm not confident in this answer — here's what I found and why" instead of guessing
- Sub-agents registered as callable tools/functions on the main agent, not just internal Python classes invoked by the router

---

## Phase 6: Real-Time Data Injection Demo (1h)

`demo/inject_new_shipments.py` — generates 10 demo shipments (70% on-time/30% late), inserts into **both** `SOURCE_ERP.orders` and `SOURCE_SUPPLIER_PORTAL.shipments` simultaneously (so the crosswalk has to resolve them live), manually triggers Dynamic Table refresh for demo timing, then re-queries OTD% before/after to show the live change plus the crosswalk resolving the new dual-sourced records into one canonical shipment.

---

## Phase 7: Streamlit — Live Proof, Not Staged Numbers (4h)

**Tab 1 — Before (per-metric selector):** OTD / Fill Rate / DOI / Landed Cost, each running its real legacy queries live against Phase 0 source tables, each with an expander explaining *why* it diverges (data-quality bug / conceptual collision / methodology mismatch / incomplete assembly — four distinct failure modes).

**Tab 2 — After, Cross-Persona Consistency Proof:** three parallel columns, three *differently-worded* persona questions:
- Planning: "How are we tracking against planned delivery dates this quarter?"
- Procurement: "What's our suppliers' on-time delivery performance?"
- Logistics: "What percentage of shipments arrived on schedule?"

Each column shows question → **generated SQL** (from Cortex Analyst) → resulting number. "Run All Three" button fires all three and shows an automated pass/fail banner comparing values (must be <0.01% variance) AND base table/measure name (must be identical).

**Tab 3 — Zero Raw Identifiers:** dedicated input pre-filled with *"Are we hitting our delivery dates?"* — no table/column names — proving business vocabulary alone resolves correctly via semantic view synonyms.

**Tab 4 — Ontology Explorer:** the headline Supplier→Part→Plant→Order→Customer mermaid diagram, clickable to run the root-cause verified query live.

---

## Phase 8: Orchestration & Automation (2h)

```sql
CREATE SCHEMA IF NOT EXISTS SUPPLY_CHAIN.AUTOMATION;
CREATE OR REPLACE TABLE SUPPLY_CHAIN.AUTOMATION.at_risk_orders_snapshot (
    snapshot_timestamp TIMESTAMP_NTZ, customer_order_id NUMBER,
    at_risk_supplier VARCHAR(200), risk_level VARCHAR(20), order_value NUMBER);
CREATE OR REPLACE TABLE SUPPLY_CHAIN.AUTOMATION.daily_health_metrics (
    metric_date DATE, otd_percent NUMBER, customer_fill_rate NUMBER,
    avg_doi NUMBER, avg_landed_cost_per_unit NUMBER);

CREATE OR REPLACE TASK SUPPLY_CHAIN.AUTOMATION.refresh_at_risk_orders
    WAREHOUSE = COMPUTE_WH SCHEDULE = '15 MINUTE' AS
    INSERT INTO SUPPLY_CHAIN.AUTOMATION.at_risk_orders_snapshot
    SELECT CURRENT_TIMESTAMP(), customer_order_id, at_risk_supplier, risk_level, order_value
    FROM TABLE(SUPPLY_CHAIN.SEMANTIC_MODELS.at_risk_orders_query());

CREATE OR REPLACE TASK SUPPLY_CHAIN.AUTOMATION.daily_health_snapshot
    WAREHOUSE = COMPUTE_WH SCHEDULE = 'USING CRON 0 6 * * * UTC' AS
    INSERT INTO SUPPLY_CHAIN.AUTOMATION.daily_health_metrics
    SELECT CURRENT_DATE(), otd, fill_rate, doi, landed_cost
    FROM SEMANTIC_VIEW(SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY
        METRICS shipment.on_time_delivery_rate AS otd, customer_order.customer_fill_rate AS fill_rate, ...);

ALTER TASK SUPPLY_CHAIN.AUTOMATION.refresh_at_risk_orders RESUME;
ALTER TASK SUPPLY_CHAIN.AUTOMATION.daily_health_snapshot RESUME;
```

- Register an equivalent **CoCo automation** (via the `automation` skill) so scheduled/unattended execution is demonstrated inside CoCo itself, not just as Snowflake Tasks.
- **MCP Slack connector**: new HIGH-risk rows in `at_risk_orders_snapshot` push an alert — Snowflake `NOTIFICATION INTEGRATION` + webhook as fallback if MCP Slack server isn't available in this environment.
- **Document intelligence**: `AI_PARSE_DOCUMENT` over synthetic supplier contract PDFs → Cortex Search → demo moment: *"Does our contract with Acme Corp have an SLA penalty for late delivery?"* enriches a root-cause answer via the post-query hook.

---

## Phase 9: Testing & Validation (2h)

`tests/test_golden_questions.py`:
- `test_at_risk_orders_query`, `test_what_if_scenario`, `test_root_cause_trace`
- `test_cross_persona_consistency_different_phrasing` — asserts same value AND same `base_table`/`measure_name` across 3 differently-worded questions
- `test_business_language_resolves_without_raw_identifiers` — asserts "Are we hitting our delivery dates?" resolves to `on_time_delivery_rate` with no raw column names leaking into the generated SQL surfaced to the user
- Run `reflect_semantic_model` and the `sql-verify` sub-agent on all verified-query SQL before demo day

---

## Phase 10: Custom CoCo Skill (1h)

`skills/supply-chain-analyst-skill/` — installable plugin, 4 skills: `analyze-supplier-performance`, `identify-at-risk-orders`, `run-what-if-scenario`, `trace-root-cause`.

---

## Phase 11: Multi-Surface Deployment (stretch, 2h)

1. CoCo CLI/Desktop — the build/test surface throughout
2. **Snowsight Cloud Agent** — register the same Cortex Analyst + semantic view as a Snowflake Intelligence object
3. **Slackbot** (stretch) — `@mention` the bot and get the same governed answer

---

## Consolidated Task List

1. Create `SOURCE_ERP`, `SOURCE_LOGISTICS_TMS`, `SOURCE_SUPPLIER_PORTAL`, `SOURCE_IOT_SENSOR`, `SOURCE_FINANCE` schemas with genuine definitional conflicts across all 4 metrics
2. Generate correlated synthetic ground-truth data with deliberate cross-source divergence (via CoCo)
3. Build `shipment_crosswalk` entity-resolution Dynamic Table (fuzzy supplier match, date-proximity join)
4. Write & validate legacy queries per metric — confirm live divergent spread
5. Build unified Bronze landing for all sources + remaining entities (parts, plants, orders, inventory, quality, invoices)
6. Build Silver canonical layer applying one governance-approved definition per metric
7. Build Gold fact/dim/bridge/agg Dynamic Tables
8. Define ontology and encode as native `CREATE SEMANTIC VIEW` with explicit synonyms per measure/dimension (in `SEMANTIC_MODELS` schema)
9. Validate semantic view with `reflect_semantic_model`; deploy Cortex Analyst + Cortex Search
10. Build hybrid agent router with pre/post-query hooks, confidence fallback, and sub-agents registered as callable tools
11. Validate golden test questions + cross-persona consistency + zero-raw-identifier resolution
12. Build real-time injection demo (dual-source injection proving live crosswalk resolution)
13. Build Streamlit: Before (4-metric selector) / After (cross-persona proof) / Zero-identifiers / Ontology explorer
14. Build `AUTOMATION` schema + Snowflake Tasks + CoCo automation + MCP Slack alert + document intelligence demo
15. Package the custom CoCo skill
16. (Stretch) Deploy to Snowsight Cloud Agent + Slackbot
17. Delete the stale `supply-chain-ontology-hackathon.plan.md` (superseded, pre-revision draft)

## Priority Tiers (if time-constrained)
- **P1 (must-have):** Tasks 1-13 — fully answers every literal challenge requirement
- **P2 (should-have):** Task 14 — required for full CoCo-usage guideline credit
- **P3 (nice-to-have):** Tasks 15-16 — ingenuity bonus points
