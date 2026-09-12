# Supply Chain Ontology & Governed Conversational Analytics

**Snowflake CoCo CLI Hackathon 2026 for GCCs**

A governed, native-Snowflake semantic layer that resolves a real problem in large
organizations: five different systems (ERP, TMS, Supplier Portal, IoT, Finance) each
compute "On-Time Delivery," "Fill Rate," "Days of Inventory," and "Landed Cost"
differently, and every team believes their number is correct. This project builds the
fragmentation deliberately, resolves it with one governed Snowflake **Semantic View**,
and layers a multi-agent conversational analytics router and a Streamlit narrative app
on top — so any persona (Planning, Procurement, Logistics) asks a differently-worded
question and gets the same, governed answer.

> **100% synthetic data.** Every row in this repository is generated (`data_generation/`,
> `sql/01_bronze/generate_bronze_netnew_data.sql`, and seeded `RANDOM()` logic in
> `sql/00_source_schemas/*.sql`). No proprietary or real customer/GCC data is used
> anywhere in this project.

## The problem, in one table

Before governance, four teams query four systems and get four different answers to
"What's our On-Time Delivery rate?" — each answer is *correct by that team's definition*,
which is exactly the problem:

| Team | System | Definition | Legacy answer |
|---|---|---|---|
| Operations | ERP | Ship-confirm before requested date; excludes cancelled/backorder rows | 89.4% |
| Logistics | TMS | Delivery before promised date (2-day carrier buffer baked in) | 91.3% |
| Procurement | Supplier Portal | ASN receipt before planned date; drops in-transit shipments | 78.6% |
| Warehouse | IoT sensors | Sensor-detected dock receipt; only ~70% sensor coverage | biased sample |
| **Governed truth** | **Semantic View** | Plant-dock receipt vs. planned; cancelled/overdue-in-transit always count as late | **64.875%** |

The governed number is *stricter* than every legacy answer, not just "different" — the
governance decision closes loopholes each source system used to look better than reality.
See [`sql/10_workspace_artifact/legacy_before_queries.sql`](sql/10_workspace_artifact/legacy_before_queries.sql)
for the equivalent divergence on Fill Rate, Days of Inventory, and Landed Cost, each with
its actually-observed result recorded inline.

## Architecture

```
SOURCE_ERP, SOURCE_LOGISTICS_TMS, SOURCE_SUPPLIER_PORTAL,      Phase 0 — genuine
SOURCE_IOT_SENSOR, SOURCE_FINANCE  (fragmented, source-shaped)  fragmentation
        │
        ▼
BRONZE            unified raw landing zone                      Phase 1
        │
        ▼
SILVER            canonical layer + shipment_crosswalk          Phase 2
                  (cross-system entity resolution: ERP order ↔
                   TMS delivery ↔ Supplier Portal shipment ↔
                   IoT sensor tag, resolved into ONE shipment)
        │
        ▼
GOLD              dimensional model: 9 entities, 28 Dynamic      Phase 3
                  Tables (facts/dims/bridge/agg)
        │
        ▼
SEMANTIC_MODELS   native SEMANTIC VIEW (9 tables, 10             Phase 4
                  relationships, 5 metrics, 5 dimensions) +
                  Cortex Search over supplier contract PDFs
        │
        ├──► agents/agent_router.py     multi-agent router:      Phase 5
        │    intent classification → CortexAnalystClient /
        │    SimulationAgent / EvidenceTraceAgent / DocumentQAAgent,
        │    with PreQueryValidator + PostQueryEnricher guardrails
        │
        └──► streamlit_app.py           deployed Streamlit-in-   Phase 7
             Snowflake narrative app (6 "Acts": chaos → governed
             truth → cross-persona proof → zero-identifiers →
             ontology explorer → live ops)

SUPPLY_CHAIN.GOVERNANCE   tags, classification, RBAC roles,
                          Marketplace enrichment, Workspace artifact
```

Every canonical metric's governance decision is documented as a `COMMENT` directly on
the metric in [`sql/04_semantic_view/supply_chain_ontology_semantic_view.sql`](sql/04_semantic_view/supply_chain_ontology_semantic_view.sql)
— open that file to see exactly which cross-team disagreement each metric resolves and how.

## Repository structure

```
sql/
├── 00_source_schemas/     Phase 0 — fragmented SOURCE_* systems + governance tags/classification
├── 01_bronze/             Phase 1 — unified raw landing zone
├── 02_silver/             Phase 2 — canonical layer + shipment_crosswalk entity resolution
├── 03_gold/               Phase 3 — dimensional model (28 Dynamic Tables)
├── 04_semantic_view/      Phase 4 — native SEMANTIC VIEW + Cortex Search over supplier PDFs
├── 07_rbac/               Least-privilege roles: SUPPLY_CHAIN_ANALYST_RO, SUPPLY_CHAIN_TASK_EXECUTOR
├── 08_marketplace_enrichment/  Free Marketplace weather dataset joined to shipment risk
├── 09_ops/                Pause/resume compute scripts + token/cost tracking queries
└── 10_workspace_artifact/ Legacy divergence queries published as a Snowsight Workspace

agents/agent_router.py     Phase 5 — hybrid multi-agent router with guardrails
streamlit_app.py           Phase 7 — deployed Streamlit-in-Snowflake narrative app
snowflake.yml              Streamlit deployment manifest
data_generation/           Synthetic data + supplier contract PDF generators
tests/test_golden_questions.py   Phase 9 — golden-question validation suite

docs/
├── hackathon-review-human.md    Full requirement-by-requirement review (start here for detail)
├── hackathon-review-agent.md    Machine-readable companion checklist
├── evidence/live-account-snapshot.md   Point-in-time live-account SHOW/DESCRIBE snapshot
├── token-and-cost-tracking.md   Real 30-day Cortex/warehouse credit usage
└── pending-gaps.md              Explicitly deferred work (not oversights)

.cortex/plans/, .snowflake/cortex/plans/   Dated CoCo planning-session artifacts
```

Each `sql/` phase folder has its own `README.md` recording the row counts and validated
metric values from the last actual run — not just the design, but proof it executed.

## Setup

1. **Connect to Snowflake.** This project assumes a `snow` CLI / Cortex Code connection
   profile targeting an account with `ACCOUNTADMIN` (or equivalent) access for the initial
   build. `agents/agent_router.py` reads its own connection via a local `connections.toml`
   profile (`CONNECTION_NAME` at the top of the file — update it to your profile name).
2. **Run the SQL phases in order** (each is idempotent — safe to re-run):
   ```
   sql/00_source_schemas/00_setup_role.sql          -- update <YOUR_USER> first
   sql/00_source_schemas/*.sql
   sql/01_bronze/*.sql
   sql/02_silver/*.sql
   sql/03_gold/*.sql
   sql/04_semantic_view/*.sql
   sql/07_rbac/create_analyst_and_executor_roles.sql
   sql/08_marketplace_enrichment/*.sql
   sql/10_workspace_artifact/*.sql (via the Workspace SQL commands in its README)
   ```
3. **Generate synthetic supplier contracts** (optional — sample PDFs are already
   committed under `data_generation/supplier_contracts/`):
   ```
   pip install -r data_generation/requirements.txt
   python data_generation/generate_supplier_contracts.py
   ```
4. **Deploy the Streamlit app:**
   ```
   snow streamlit deploy
   ```
   (deploys per `snowflake.yml` to `SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY_APP`)
5. **Run the golden-question test suite:**
   ```
   python tests/test_golden_questions.py
   ```
   Currently **2/5 pass live** (the 2 pure-SQL sub-agent tests). The 3 tests routed
   through the REST-based `CortexAnalystClient` fail with `401 Unauthorized` — a disclosed,
   reproducible auth-transport gap, not a semantic-view or metric-logic problem (the same
   metrics are independently proven correct via the deployed Streamlit app's SiS-native
   transport and via direct SQL). See the test file's docstring for the full diagnosis.
6. **Manage compute costs between sessions:**
   ```
   sql/09_ops/pause_compute.sql    -- suspend all 28 Dynamic Tables + Cortex Search + warehouse
   sql/09_ops/resume_compute.sql   -- resume before your next working session / demo
   ```

## Demo instructions

Open the deployed Streamlit app in Snowsight (`SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY_APP`)
and walk the 6 Acts in order: **Cover → Before (Chaos) → Cross-Persona Consistency →
Zero Raw Identifiers → Ontology Explorer → Live Ops**. Each Act runs its queries live
against the account — nothing is pre-rendered.

For a code-only walkthrough (no Snowsight needed), read
[`sql/10_workspace_artifact/legacy_before_queries.sql`](sql/10_workspace_artifact/legacy_before_queries.sql)
top to bottom: every legacy divergence query for all 4 canonical metrics, each followed
by its actually-observed result, ending with the single governed semantic-view query.

## External data used

| Dataset | Provider | License | Used for |
|---|---|---|---|
| Pelmorex Weather Source: Frostbyte (`GZSOZ1LLEL`, Snowflake Marketplace) | Pelmorex Weather Source | Free; standard Snowflake Marketplace consumer terms | `SUPPLY_CHAIN.GOLD.v_shipment_weather_risk` — tests whether late shipments correlate with severe weather at the destination on the ship date. See [`sql/08_marketplace_enrichment/README.md`](sql/08_marketplace_enrichment/README.md) for the full result, including an honestly-reported coverage limitation. |

## Current status

The core technical layers (ontology, governance tagging, semantic view, multi-agent
router, document intelligence, deployed Streamlit app, least-privilege RBAC, Marketplace
enrichment, Workspace artifact, cost tracking) are built and have recorded, verifiable
execution evidence. What's explicitly deferred (not an oversight) and what's a disclosed,
reproducible gap are both documented rather than hidden:

- **Full detail:** [`docs/hackathon-review-human.md`](docs/hackathon-review-human.md) —
  a requirement-by-requirement review with file-level evidence for every claim.
- **Deferred by explicit decision:** [`docs/pending-gaps.md`](docs/pending-gaps.md) —
  the `AUTOMATION` schema/Task automation/alerting, and a packaged custom CoCo skill.
- **Disclosed test gap:** `tests/test_golden_questions.py` reproducibly passes 2/5 (see
  Setup step 5 above).

## Contributing

This is a hackathon submission and not currently accepting external contributions.
