---
name: "supply-chain-ontology-revised"
created: "2026-09-12T07:53:45.147Z"
status: pending
---

# Supply Chain Ontology & Governed Conversational Analytics — Master Plan

## ⚠️ Official Rules Compliance (read first — gates judging, must not miss)

Source: Snowflake CoCo CLI Hackathon for GCCs — Official Rules. Submission deadline **Sept 21, 2026** (Judging Period). Solo entry (Team Lead = only participant) — Section 4.1 profile (name, corporate email, phone, location) still required at submission, just for one person.

**Technical compliance gate (Section 9) — fails these = automatic disqualification before judging even starts:**
- [ ] Solution is built **natively on Snowflake's AI Data Cloud** (medallion + Cortex + Semantic View — already the plan's core; keep everything inside `SUPPLY_CHAIN` DB, no external DBs).
- [ ] Source code is written in **Python, Java, and/or Scala** — `agents/`, `data_generation/`, `streamlit_app.py`, `demo/` are Python ✅. SQL alone does not count as the required language; keep the Python surfaces in scope, do not cut them as stretch-only.
- [ ] All Section 4.1 + 4.5 deliverables submitted before the deadline (see checklist below) — a complete Prototype with a missing deck or missing repo link is still an incomplete Entry.

**Entry deliverables (Section 4.1, 4.5) — new Phase 12 below tracks these explicitly:**
1. Profile info (name, corporate email, phone, location) — submission-portal form, not a repo artifact.
2. The explicit **Idea** — a short written concept doc (`docs/idea-one-pager.md`), separate from the code.
3. Functional **Prototype** (this repo).
4. **Architectural presentation deck** (PPT/slides) covering idea, technical approach, system design topology, thought process.
5. Link to full source code via a functional GitHub repo (this repo, made public or judge-accessible before deadline).

**Judging Criteria — the ACTUAL 4 dimensions (Section 9), replacing any prior informal mapping:**
1. **Platform Execution & Rigor** — depth of Snowpark, Streamlit, Snowflake Intelligence, Worksheets, Marketplace usage in the *operational pipeline* (not just name-dropped). Current plan is strong on Dynamic Tables/Semantic View/Cortex but is missing an explicit **Marketplace** touchpoint and a visible **Worksheets** artifact — both added below.
2. **System Design & Engineering** — structural partitioning (medallion layering ✅), API interactions (agent router ✅), **token management**, and warehouse/compute performance optimization — token/cost tracking added below (was not explicit before).
3. **Enterprise Viability & Value** — real-world friction points, time-to-insight, multi-step workflow automation — already the headline story's strength (ontology fragmentation → governed answer).
4. **Governance & Security Guardrails** — RBAC, data privacy, **LLM hallucination mitigation** — Phase 0 governance tags/classification/DMFs are a good start, but RBAC is currently a single admin role; least-privilege role separation is added below, plus explicit hallucination-mitigation framing.

**Dataset & IP compliance (Section 4.3–4.4, 4.4e):**
- All data is 100% synthetic, generated via CoCo — **no real or proprietary GCC corporate data is used anywhere** in this project. State this explicitly in the final `README.md` and the Idea one-pager (Section 4.4(e) explicitly bars unauthorized use of employer production data — this must be an affirmative, visible statement, not an assumption).
- No external/third-party datasets or APIs are currently used. If Phase 4.5 (Marketplace enrichment, added below) pulls a public Marketplace/API dataset, list it explicitly with its license in the README per Section 4.3(b)/4.4.

**Live demo (Section 4.5(c)):** must be a **live** demonstration during the Grand Finale window (Oct 1–4, 2026) if shortlisted — pre-recorded not accepted without explicit approval. Rehearse the Streamlit demo end-to-end against a live Snowflake connection, not screenshots/video. Have a fallback (e.g. local warehouse pre-warmed, backup network) since Sponsor is not responsible for the presenter's connectivity issues.

---

## Naming Convention

All fragmented source-system schemas use a `SOURCE_` prefix for consistency and easy identification: `SOURCE_ERP`, `SOURCE_LOGISTICS_TMS`, `SOURCE_SUPPLIER_PORTAL`, `SOURCE_IOT_SENSOR`, `SOURCE_FINANCE`.

**Why `SEMANTIC_MODELS` and `AUTOMATION` stay as separate schemas (not folded into GOLD):**

- `SEMANTIC_MODELS` is the governed business/consumption layer (semantic view, Cortex Search, Cortex Analyst) — separating it means agents/BI tools can be granted access to *this* schema only, without exposure to raw dimensional tables in GOLD. It also keeps the medallion story visually clean: `SHOW SCHEMAS` reads as BRONZE→SILVER→GOLD→SEMANTIC\_MODELS, one schema per architectural layer.
- `AUTOMATION` holds operational state (Task-populated snapshots, alert history) — different in kind from canonical facts/dims, different grants (task-execution roles vs. read-only analytics roles), different lifecycle (logs, not a dimensional model). Keeping it separate avoids muddying GOLD's purpose.

## Repo Structure (target state at submission)

```
snowflake-coco-cli-hackathon/
├── .gitignore
├── README.md                                 # setup, architecture diagram, demo instructions, dataset/license + synthetic-data disclosure — write last
│
├── .snowflake/cortex/plans/
│   └── supply-chain-ontology-revised.plan.md # planning-phase artifact (CoCo evidence)
│
├── docs/
│   ├── idea-one-pager.md                     # Entry Section 4.1(b) — the explicit Idea (Phase 12)
│   └── architecture-deck.pptx                # Entry Section 4.5(a) — architectural presentation deck (Phase 12)
│
├── sql/
│   ├── 00_source_schemas/                    # Phase 0 — fragmentation
│   │   ├── 00_setup_role.sql                 # SUPPLY_CHAIN_ADMIN + least-privilege role split (Phase 0 RBAC)
│   │   ├── source_erp.sql
│   │   ├── source_logistics_tms.sql
│   │   ├── source_supplier_portal.sql
│   │   ├── source_iot_sensor.sql
│   │   └── source_finance.sql
│   ├── 01_bronze/create_bronze_tables.sql            # Phase 1
│   ├── 02_silver/                                    # Phase 2
│   │   ├── create_silver_dynamic_tables.sql
│   │   └── shipment_crosswalk.sql
│   ├── 03_gold/create_gold_dynamic_tables.sql        # Phase 3
│   ├── 04_semantic_view/supply_chain_ontology_semantic_view.sql  # Phase 4 (source of truth; drop semantic_models/*.yaml if redundant)
│   ├── 04_semantic_view/worksheet_legacy_queries.sql # Phase 4.5 — saved Worksheet artifact for judges
│   └── 08_automation/tasks_and_alerts.sql            # Phase 8
│
├── data_generation/generate_synthetic_data.py        # CoCo-driven synthetic dataset generator
├── semantic_models/supply_chain_ontology.yaml        # Cortex-Analyst-facing model (decide vs. native SEMANTIC VIEW during Phase 4)
├── agents/agent_router.py                            # hybrid router, hooks, sub-agents (Phase 5)
├── demo/inject_new_shipments.py                      # real-time injection demo (Phase 6)
├── streamlit_app.py                                  # Before/After/Cross-persona/Ontology explorer (Phase 7)
│
├── skills/supply-chain-analyst-skill/                # reusable CoCo skill (Phase 10)
│   ├── .cortex-plugin/plugin.json
│   ├── skills/
│   │   ├── analyze-supplier-performance.md
│   │   ├── identify-at-risk-orders.md
│   │   ├── run-what-if-scenario.md
│   │   └── trace-root-cause.md
│   └── README.md
│
└── tests/test_golden_questions.py                    # golden test suite (Phase 9); also token/cost usage check
```

Notes:

- `sql/` is numbered by medallion phase so the architecture reads top-to-bottom by folder name alone.
- `.snowflake/cortex/plans/` stays in the repo deliberately as literal CoCo-planning-phase evidence for judging.
- Decide during Phase 4 whether `semantic_models/*.yaml` is kept alongside the native `SEMANTIC VIEW` SQL or dropped as redundant once the SQL object is the source of truth.
- `skills/supply-chain-analyst-skill/` is a standalone installable unit (`cortex skill install ./skills/supply-chain-analyst-skill`).
- `README.md` should be written/updated last, once the build stabilizes.

---

## Headline Story (opens and closes the demo)

```
Supplier ──ships──▶ Part ──delivered to──▶ Plant ──fulfills──▶ CustomerOrder ──placed by──▶ Customer
```

Today, three teams ask "What's our on-time delivery rate?" against three real, disconnected systems and get three genuinely different, defensible-looking answers. We fix this by resolving the ontology once (Bronze→Silver→Gold→Semantic View) and proving — live, with generated SQL on screen — that every persona, phrased any way, now gets the identical answer.

**Judging-criteria mapping (closing slide — use the official 4 dimensions, Section 9):**

- **Platform Execution & Rigor** — Dynamic Tables medallion pipeline (Snowpark-adjacent SQL engineering), Streamlit demo app, Cortex Analyst/Search as the Snowflake Intelligence surface, a saved **Worksheet** with the four legacy "Before" queries for judges to open directly in Snowsight, and a **Marketplace**-sourced dataset enriching the what-if simulation (Phase 4.5).
- **System Design & Engineering** — medallion layering, entity-resolution crosswalk, hybrid multi-agent router with hooks, explicit **token/cost tracking** and right-sized warehouses (Phase 9).
- **Enterprise Viability & Value** — fragmentation modeled on genuine root causes (carrier buffers, dropped denominators, forecast-vs-actual, incomplete cost assembly) resolved into one governed answer, automating a real multi-step workflow (at-risk-order detection → alerting).
- **Governance & Security Guardrails** — governance tags/classification/DMFs (Phase 0), least-privilege RBAC role separation (added below), confidence-threshold fallback + verified queries as hallucination mitigation (Phase 5).

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

**Synthetic data (generate via CoCo):** \~800 ground-truth physical shipments projected into 2-4 source tables each with deliberate ID divergence and completeness gaps, tuned so live legacy queries produce a believable spread per metric:

- OTD: ERP \~90%, TMS \~93%, Supplier Portal \~78%, IoT \~84%
- Fill Rate: Customer-facing \~91%, Supplier-facing PO fill \~85%, Unit-level \~88% (three different concepts, not just different numbers)
- DOI: Planning (forecast) vs. Finance (COGS-based) vs. Warehouse (7-day trailing) — deliberately different methodologies
- Landed Cost: Procurement (PO+quoted freight only) vs. Logistics (actual freight+customs, no purchase price) vs. Finance (full stack, \~1 month stale)

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

**RBAC & least-privilege roles (Governance & Security Guardrails criterion — do not ship with a single admin role):**

The existing `sql/00_source_schemas/00_setup_role.sql` only creates `SUPPLY_CHAIN_ADMIN`. Add a small role hierarchy so grants map to actual access patterns, and so the RBAC story is demonstrable, not just "everything is ACCOUNTADMIN":

```sql
-- Owns all objects, runs DDL/build scripts (human/build-time role)
CREATE ROLE IF NOT EXISTS SUPPLY_CHAIN_ADMIN;

-- Read-only, scoped to SEMANTIC_MODELS + GOLD only — the role Cortex Analyst/Agent/Streamlit
-- app connects as. Cannot see SOURCE_*/BRONZE fragmented raw data or run DDL.
CREATE ROLE IF NOT EXISTS SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON DATABASE SUPPLY_CHAIN TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.SEMANTIC_MODELS TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.GOLD TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON ALL TABLES IN SCHEMA SUPPLY_CHAIN.GOLD TO ROLE SUPPLY_CHAIN_ANALYST_RO;
GRANT SELECT ON SEMANTIC VIEW SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY TO ROLE SUPPLY_CHAIN_ANALYST_RO;

-- Executes scheduled Tasks only — separate from the human admin role
CREATE ROLE IF NOT EXISTS SUPPLY_CHAIN_TASK_EXECUTOR;
GRANT USAGE ON DATABASE SUPPLY_CHAIN TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
GRANT USAGE ON SCHEMA SUPPLY_CHAIN.AUTOMATION TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA SUPPLY_CHAIN.AUTOMATION TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
GRANT SELECT ON SEMANTIC VIEW SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
```

- Streamlit app and the agent router connect using `SUPPLY_CHAIN_ANALYST_RO` — proves the app can never see raw fragmented/PII-adjacent source data, only the governed layer.
- Document this role split in the README's "Governance" section with a one-paragraph rationale — this is the single most visible, cheapest-to-build proof point for the Governance & Security Guardrails judging dimension.
- Optional stretch (only if time remains): a `DYNAMIC DATA MASKING POLICY` on `GOLD.fact_shipment.shipment_value`/cost columns, unmasked only for `SUPPLY_CHAIN_ADMIN` — a concrete masking demo beyond just role grants, cheap to add and highly visible to judges scanning for "governance."

---

## Phase 1-3: Medallion Layers for Remaining Entities (7h)

- **Bronze**: unified raw landing for parts, plants, customer\_orders, inventory, quality\_events, invoices — source-shaped, VARIANT columns for semi-structured payloads (tracking\_events, specifications, contact\_info), `_metadata` OBJECT column, tagged by `source_system`.
- **Silver**: Dynamic Tables (`TARGET_LAG = '5 MINUTES'`), type-cast, deduplicated (`QUALIFY ROW_NUMBER()...=1`), VARIANT flattened, canonical `on_time_flag` applied via the ONE governance decision (plant-dock receipt as source of truth; backorders count as late, not dropped; no artificial buffers).
- **Gold**: Dynamic Tables (`TARGET_LAG = '10 MINUTES'`) — `dim_supplier` (SCD2), `dim_part`, `dim_plant`, `dim_customer`, `dim_date`; `fact_shipment`, `fact_order_fulfillment`, `fact_inventory_snapshot`, `fact_quality_event`; `bridge_supplier_part`; `agg_supplier_performance` (pre-aggregated, `TARGET_LAG='15 MINUTES'`).
- Synthetic data generated via CoCo prompts for referential integrity (500 suppliers, 2000 parts, 50 plants, 10,000 shipments, 20,000 orders, 5,000 quality events).

---

## Phase 4: The Ontology, Encoded as a Governed Semantic View (4h)

### Entities (9), Relationships, Hierarchies

| Entity                                                                                     | Grain                                                                                                         |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
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

### Phase 4.5: Marketplace + Worksheets touchpoints (Platform Execution & Rigor criterion — currently missing, cheap to add)

- **Snowflake Marketplace**: pull one small, free public dataset (e.g. a weather/climate or public holiday-calendar listing) and join it into the what-if `SimulationAgent` — e.g. "suppliers in regions with active weather disruptions are higher at-risk" — a light but genuine Marketplace-sourced enrichment, not just a namecheck. List the listing name + license in the README per Section 4.3(b)/4.4.
- **Worksheets**: save the four Phase 0 legacy "Before" queries plus the semantic-view validation query (`SELECT * FROM SEMANTIC_VIEW(...)`) as a named Snowsight Worksheet (or `.sql` script importable as one) — gives judges a concrete, screenshot-able Worksheets artifact rather than relying only on the Streamlit app.

---

## Phase 5: Hybrid Multi-Agent Router (5h)

`agents/agent_router.py`:

- `PreQueryValidator` — entity/forbidden-term/length/language checks before any query runs

- `PostQueryEnricher` — extracts supplier names from answers, pulls matching Cortex Search document snippets, appends as "Supporting Evidence"

- `SupplyChainAgentRouter` — classifies intent (standard / document\_qa / what\_if / root\_cause / at\_risk) and routes to:

  - Main Cortex Analyst (standard) — returns structured `{text, sql, confidence}`, not just narrative text, so we can display generated SQL and extract `base_table`/`measure_name` via `sqlglot` for the consistency-proof UI
  - `DocumentQAAgent`, `SimulationAgent` (what-if delay impact), `EvidenceTraceAgent` (root-cause evidence trail)

- **Confidence-threshold fallback**: if Cortex Analyst confidence is low, respond "I'm not confident in this answer — here's what I found and why" instead of guessing

- Sub-agents registered as callable tools/functions on the main agent, not just internal Python classes invoked by the router

**Hallucination-mitigation summary (Governance & Security criterion — call this out explicitly in the deck, don't leave it implicit):**
1. Verified queries (golden questions) constrain the agent to pre-validated SQL patterns for the highest-stakes questions.
2. Semantic view synonyms + metric `COMMENT`s constrain vocabulary so the LLM maps business language to one canonical measure, not an improvised aggregation.
3. `PreQueryValidator` blocks out-of-scope/forbidden-term prompts before they reach the LLM.
4. Confidence-threshold fallback refuses to answer rather than guess when uncertain.
5. `PostQueryEnricher` grounds narrative claims in retrieved Cortex Search document snippets (citations), not free generation.

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

**Token management & compute cost (System Design & Engineering criterion — add explicit tracking, not just "it works"):**
- Right-size warehouses: `COMPUTE_WH` at `X-SMALL` with `AUTO_SUSPEND = 60` for this workload's volume — call this out in the deck as a deliberate cost decision, not a default left untouched.
- Track Cortex Analyst/Search token spend via `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY` (or `CORTEX_FUNCTIONS_USAGE_HISTORY`) — add a small query/snippet in `tests/` or the README showing token usage per demo session, so "token management" is evidenced with a real number, not asserted.
- Note the $400 trial credit budget explicitly in the README and keep a rough running total (medallion Dynamic Table refreshes + Cortex Analyst calls + Cortex Search embeddings) so the account doesn't run dry before the Grand Finale live demo.
- Query result caching: keep the four legacy "Before" queries simple/cacheable so repeated demo runs don't burn unnecessary credits.

---

## Phase 10: Custom CoCo Skill (1h)

`skills/supply-chain-analyst-skill/` — installable plugin, 4 skills: `analyze-supplier-performance`, `identify-at-risk-orders`, `run-what-if-scenario`, `trace-root-cause`.

---

## Phase 11: Multi-Surface Deployment (stretch, 2h)

1. CoCo CLI/Desktop — the build/test surface throughout
2. **Snowsight Cloud Agent** — register the same Cortex Analyst + semantic view as a Snowflake Intelligence object
3. **Slackbot** (stretch) — `@mention` the bot and get the same governed answer

---

## Phase 12: Submission Package (Official Rules Section 4.1/4.5 — mandatory, not stretch)

These are Entry deliverables that gate whether the compliance review even lets this Entry reach judging (Section 9). None of this is optional, and none of it is a code task — schedule it explicitly rather than assuming it happens by osmosis at the end.

1. **Idea one-pager** (`docs/idea-one-pager.md`) — problem statement, the fragmentation story, why it matters for a GCC context, solution summary. This is Section 4.1(b)'s "explicit Idea", separate from the Prototype itself.
2. **Architectural presentation deck** (PPT/Slides, Section 4.5(a)) — idea, technical approach (medallion + semantic view + agent router), system design topology diagram (reuse the Supplier→Part→Plant→Order→Customer ontology diagram), thought process/decisions (canonical `on_time_flag` governance call-out is a good concrete example to feature). Explicitly label a slide (or section) per judging dimension (Platform Execution & Rigor / System Design & Engineering / Enterprise Viability & Value / Governance & Security Guardrails) so judges can map the deck to their scorecard without hunting.
3. **README.md rewrite** (currently a placeholder) — setup instructions, architecture diagram, demo instructions, the explicit "100% synthetic data, no proprietary GCC data" statement (Section 4.4(e)), and the dataset/license list (Section 4.3(b)/4.4) covering any Marketplace dataset added in Phase 4.5.
4. **GitHub repo readiness** (Section 4.5(b)) — confirm repo is public or judge-accessible before Sept 21, 2026; remove/redact any real credentials, account identifiers, or trial-account secrets from committed files and git history.
5. **Profile submission** (Section 4.1(a)) — name, corporate email, phone, location — submitted via the official Contest portal (solo entry, Team Lead = self), not a repo artifact.
6. **Live-demo rehearsal** (Section 4.5(c)/(d)) — full run-through of the Streamlit app against a live Snowflake connection (not a recording); confirm Dynamic Table refresh timing works live for Phase 6's before/after moment; have a backup plan for network/connectivity issues, since Sponsor is not responsible for presenter-side technical failures.

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
18. Add least-privilege RBAC role split (`SUPPLY_CHAIN_ANALYST_RO`, `SUPPLY_CHAIN_TASK_EXECUTOR`) — Streamlit/agent connects as read-only, not admin
19. Add Marketplace-sourced dataset enrichment + save a Snowsight Worksheet with the legacy "Before" queries (Phase 4.5)
20. Add token/cost tracking query + right-sized warehouse note (Phase 9)
21. Write Idea one-pager, architecture deck, and rewritten README; confirm repo is judge-accessible and free of secrets (Phase 12)
22. Submit profile + Entry via the official Contest portal before Sept 21, 2026 11:59 PM IST

## Priority Tiers (if time-constrained)

- **P1 (must-have — also compliance-gating, not just feature-complete):** Tasks 1-13, 18, 21, 22 — fully answers every literal challenge requirement AND satisfies the Section 4/9 compliance review that happens before judging even starts. Missing 21/22 risks disqualification regardless of how good the Prototype is.
- **P2 (should-have):** Tasks 14, 19, 20 — required for full CoCo-usage guideline credit and directly targets the "Platform Execution & Rigor" (Marketplace/Worksheets) and "System Design & Engineering" (token management) judging dimensions that the original plan under-served.
- **P3 (nice-to-have):** Tasks 15-16 — ingenuity bonus points
