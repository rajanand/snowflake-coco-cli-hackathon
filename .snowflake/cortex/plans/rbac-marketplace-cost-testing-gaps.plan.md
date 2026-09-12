
# Plan: RBAC, Marketplace enrichment, cost tracking, and golden-test validation

Scope: gaps 1, 3, 4, 5 get implemented. Gaps 2 and 6 are explicitly deferred per your answers ("keep as pending for now") — they'll just be marked as still-open in status tracking, no code.

## Context gathered

- Live Snowflake account `sc23256` (`SUPPLY_CHAIN` DB, `AWS_AP_NORTHEAST_1`). Only role that exists today: `SUPPLY_CHAIN_ADMIN`. No `AUTOMATION` schema, no Tasks, no notification integrations, no secrets, no EAI (confirmed via `SHOW` commands).
- `streamlit_app.py` and `agents/agent_router.py` query `SOURCE_*` (Act 1 divergence demo), `SILVER.shipment_crosswalk`, all `GOLD.*` fact/dim tables directly, plus the `SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY` semantic view (via Cortex Analyst) and `SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS` Cortex Search service. Read-only role grants must cover all of these for the app to keep working if it's ever pointed at the new role (not doing that wiring now, per your answer).
- `sql/09_ops/pause_resume_compute.sql` lists the exact 15 Silver + 13 Gold Dynamic Tables and the Cortex Search service that operational suspend/resume touches — this defines the `TASK_EXECUTOR` OPERATE grant list.
- `dim_plant.region` values: WEST/SOUTHEAST/MIDWEST/SOUTH/NORTHEAST. `dim_supplier.region` values: APAC/EMEA/LATAM/NORTH_AMERICA. No lat/long or postal code anywhere — a Marketplace weather join needs a representative-city mapping table since there's no real geocoordinate to join on.
- `agent_router.py` already has everything the golden-test script needs: `SupplyChainAgentRouter`, `CortexAnalystClient._extract_sql_targets` (base_table/measure_name parsing), `SimulationAgent`, `EvidenceTraceAgent`. Connects via local `connections.toml` profile `GC94671`.
- `COMPUTE_WH` is already `X-SMALL`, but `AUTO_SUSPEND=300`, not the `60` the master plan explicitly claims as "a deliberate cost decision" — will fix to match.
- Marketplace search (via `cortex search marketplace`) confirmed multiple weather listings available publicly, including Pelmorex Weather Source and AccuWeather historical products. Will use `SHOW AVAILABLE LISTINGS` + `SYSTEM$REQUEST_LISTING_AND_WAIT` + `SYSTEM$ACCEPT_LEGAL_TERMS` + `CREATE DATABASE ... FROM LISTING` (fully SQL-scriptable per Snowflake docs) to pick whichever is free/instantly available in-region.
- Workspaces (not legacy Worksheets, which are deprecated June 2026) are the current SQL-scriptable way to produce a saved, shareable "Worksheet"-equivalent artifact: `CREATE WORKSPACE`, `ALTER WORKSPACE ... ADD LIVE VERSION FROM LAST`, `PUT`, `ALTER WORKSPACE ... COMMIT`.

## Task 1 — RBAC: `SUPPLY_CHAIN_ANALYST_RO` + `SUPPLY_CHAIN_TASK_EXECUTOR`

New file `sql/07_rbac/create_analyst_and_executor_roles.sql`:

- `USE ROLE ACCOUNTADMIN;` for account-level grants (`CREATE ROLE`, `EXECUTE TASK ON ACCOUNT`), then `USE ROLE SUPPLY_CHAIN_ADMIN;` for object-level grants inside `SUPPLY_CHAIN` (since that role owns the DB objects).
- **`SUPPLY_CHAIN_ANALYST_RO`** (read-only consumption role — matches actual app/agent query surface):
  - `USAGE` on `DATABASE SUPPLY_CHAIN`, `WAREHOUSE COMPUTE_WH`.
  - `USAGE` on schemas `SOURCE_ERP`, `SOURCE_LOGISTICS_TMS`, `SOURCE_SUPPLIER_PORTAL`, `SOURCE_IOT_SENSOR`, `SOURCE_FINANCE`, `SILVER`, `GOLD`, `SEMANTIC_MODELS`.
  - `SELECT` on all tables (+ `SELECT ON FUTURE TABLES`) in each `SOURCE_*` schema, `SILVER`, `GOLD`.
  - `SELECT` on `SEMANTIC VIEW SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY`.
  - `USAGE` on `CORTEX SEARCH SERVICE SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS`.
  - Grant role to `USER RAJANAND` for testing.
- **`SUPPLY_CHAIN_TASK_EXECUTOR`** (operational role, sized for what `pause_resume_compute.sql` already does plus near-term Task automation):
  - `USAGE` + `OPERATE` on `WAREHOUSE COMPUTE_WH`.
  - `USAGE` on `SILVER`, `GOLD`, `SEMANTIC_MODELS`.
  - `OPERATE` on all 15 Silver + 13 Gold Dynamic Tables (explicit list from `pause_resume_compute.sql`) + `OPERATE ON FUTURE DYNAMIC TABLES` in both schemas.
  - `OPERATE` on `CORTEX SEARCH SERVICE SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS`.
  - `EXECUTE TASK ON ACCOUNT` (account-level, needs ACCOUNTADMIN to grant).
  - Comment block noting `CREATE TASK` on an `AUTOMATION` schema grant is intentionally **not** included yet — that schema doesn't exist (Gap 2, deferred); add it when that work starts.
  - Grant role to `USER RAJANAND` for testing.
- Add `sql/07_rbac/README.md` documenting the role split, the explicit grant rationale, and the known gap: the badge text in `streamlit_app.py` currently says "read-only, semantic layer only" but the actual grants (and the app's real queries) are broader than semantic-layer-only, because the app bypasses the semantic view for Acts 1–4. Flag this as a follow-up if/when the app is wired to run as this role.
- Execute the script, then run verification queries: confirm `SHOW GRANTS TO ROLE SUPPLY_CHAIN_ANALYST_RO` / `..._TASK_EXECUTOR` look right, and spot-check one `SELECT` under each role.

## Task 2 — Gap 2 stays pending (no code)

Just a one-line status note (in the RBAC README or a short addition to the plan file) recording that `AUTOMATION` schema / Tasks / Slack alerting remain deferred, so it doesn't silently disappear from tracking.

## Task 3 — Marketplace weather enrichment

New folder `sql/08_marketplace_enrichment/`:

1. `01_acquire_weather_listing.sql`:
   - `SHOW AVAILABLE LISTINGS LIKE '%Weather%';` to get live global names/pricing/region-readiness (values shift, so the script queries live rather than hardcoding a stale global name).
   - `CALL SYSTEM$REQUEST_LISTING_AND_WAIT('<global_name>');` if not immediately ready.
   - `CALL SYSTEM$ACCEPT_LEGAL_TERMS('DATA_EXCHANGE_LISTING', '<global_name>');`
   - `CREATE DATABASE WEATHER_MARKETPLACE FROM LISTING '<global_name>';`
   - Comment documenting the chosen listing's title, provider, and license terms (for the README dataset/license list task later — out of scope here, just leaving the breadcrumb).
2. `02_region_weather_enrichment.sql`:
   - `SUPPLY_CHAIN.GOVERNANCE.region_weather_city_map` — small static table mapping our synthetic `dim_plant.region` values (WEST/SOUTHEAST/MIDWEST/SOUTH/NORTHEAST) to representative real cities available in the weather dataset, since there's no geocoordinate in the synthetic data to join on directly.
   - `SUPPLY_CHAIN.GOLD.v_shipment_weather_risk` view: joins `fact_shipment` → `dim_plant` (for region) → `region_weather_city_map` → the weather dataset on ship date, surfacing a `severe_weather_flag` and correlating it with `is_on_time`, to genuinely answer "are late shipments correlated with severe weather at the destination region on the ship date?" — a real analytical use of the enrichment, not just a namecheck join.
3. `sql/08_marketplace_enrichment/README.md`: what the listing is, why it was picked (free/global coverage, license), and the enrichment query.
4. Run it live, sanity-check row counts and the correlation query.

## Task 4 — Snowsight Workspace with the legacy "Before" queries

- New `sql/10_workspace_artifact/legacy_before_queries.sql`: the 4 legacy divergent OTD/fill-rate/DOI/landed-cost queries (pulled from the existing Phase 0 SQL / `streamlit_app.py` Act 1 queries) plus the semantic-view validation query `SELECT * FROM SEMANTIC_VIEW(SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY ...)`, each with a comment header explaining what it shows.
- Execute via SQL: `CREATE WORKSPACE SUPPLY_CHAIN.GOVERNANCE.LEGACY_QUERIES_WORKSPACE;` → `ALTER WORKSPACE ... ADD LIVE VERSION FROM LAST;` → `PUT file://.../legacy_before_queries.sql snow://workspace/.../versions/live/ AUTO_COMPRESS=false OVERWRITE=true;` → `ALTER WORKSPACE ... COMMIT;`
- Verify with `LIST snow://workspace/SUPPLY_CHAIN.GOVERNANCE.LEGACY_QUERIES_WORKSPACE/versions/head/;`

## Task 5 — Token/cost tracking + warehouse sizing

- New `sql/09_ops/token_cost_tracking.sql`:
  - Query `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY` filtered to Cortex Analyst / Cortex Search function calls, grouped by day, summing tokens — the "evidenced with a real number" requirement from the plan.
  - Query `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY` for `COMPUTE_WH` credit usage.
- `ALTER WAREHOUSE COMPUTE_WH SET AUTO_SUSPEND = 60;` — tightens to match the plan's explicit "X-SMALL, AUTO_SUSPEND=60" cost-decision claim (currently 300s).
- Short `docs/token-and-cost-tracking.md` capturing one real sample run's numbers (tokens used, credits burned) so this is evidenced, not asserted.

## Task 6 — Golden test question validation

New `tests/test_golden_questions.py` (plain script with assert-based checks + a PASS/FAIL summary printed at the end, exits non-zero on failure — no new pytest dependency since none is currently vendored):

- Imports `agents/agent_router.py` (adds repo root to `sys.path`).
- `test_cross_persona_consistency()` — sends 3 differently-worded OTD questions (Planning/Procurement/Logistics phrasing from the plan) through `CortexAnalystClient`, asserts numeric values match within 0.01% and `base_table`/`measure_name` are identical (using the existing `_extract_sql_targets`).
- `test_zero_raw_identifiers()` — asks "Are we hitting our delivery dates?", asserts the generated SQL resolves via the semantic view and contains no raw `SOURCE_*`/`SILVER.*` table names.
- `test_at_risk_orders()` — runs the at-risk verified query path (`intent="at_risk"`), asserts it returns rows with expected shape.
- `test_what_if_scenario()` — `SimulationAgent.simulate()` with a sample supplier + delay days, asserts response structure and `newly_at_risk` semantics.
- `test_root_cause_trace()` — `EvidenceTraceAgent.trace()` for a sample at-risk order, asserts a supplier root cause is identified when one exists.
- Run it live against the current connection; also re-run `reflect_semantic_model` on the semantic view file as a companion validation step.
- Record pass/fail results back to the user (and fix anything that fails — this is a validation pass, not just writing the test).

## Task 7 — Gap 6 stays pending (no code)

One-line status note only, same treatment as Task 2.

## Out of scope for this pass (explicitly deferred, no action)

- Gap 2: `AUTOMATION` schema, Snowflake Tasks, MCP/Slack/email alerting.
- Gap 6: custom CoCo skill packaging.
- Rewiring `streamlit_app.py` to actually run as `SUPPLY_CHAIN_ANALYST_RO` (roles are created and ready, but not wired in, per your answer).
- README rewrite, idea one-pager, architecture deck, portal submission (separate gaps from the earlier list, not part of 1–6).
