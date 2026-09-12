# Live Account Snapshot (Supplementary Evidence)

**Purpose:** this file is a point-in-time capture of `SHOW`/`DESCRIBE`/`SELECT` commands run directly against the live Snowflake account (`sc23256.ap-northeast-1.aws`, database `SUPPLY_CHAIN`) during two review/build sessions on **2026-09-12** (an initial gap-analysis pass, followed by a gap-closing implementation pass the same day — the numbers below are from *after* the gap-closing pass, i.e. current). It exists so that a reviewer **without their own Snowflake account access** still has an auditable record of what was actually running in the account — not just what the SQL scripts in this repo *say* they create.

**How to use this file:** treat it as a dated log, the same way you'd treat a committed CI run log or test report — it is evidence that the scripts in `sql/` were executed, not just written. It is supplementary to, not a replacement for, the two primary verification paths, which require no account access at all:
1. Read the SQL/Python source file that defines the object (proves the design is correct and complete).
2. Read the phase `README.md` in the same folder, which records actual row counts / validated metric values captured at build time (proves it was run, independent of this snapshot).

Every command below is reproducible by anyone with access to this account — the SQL text is the exact command run, not paraphrased.

---

## 1. Schemas present in `SUPPLY_CHAIN`

```sql
SHOW SCHEMAS IN DATABASE SUPPLY_CHAIN;
```

12 schemas: `BRONZE`, `GOLD`, `GOVERNANCE`, `INFORMATION_SCHEMA`, `PUBLIC`, `SEMANTIC_MODELS`, `SILVER`, `SOURCE_ERP`, `SOURCE_FINANCE`, `SOURCE_IOT_SENSOR`, `SOURCE_LOGISTICS_TMS`, `SOURCE_SUPPLIER_PORTAL`.

Notably **still absent**: `AUTOMATION`. Confirms the Tasks/scheduled-automation phase described in the master plan remains not built — consistent with there being no `CREATE TASK`/`AUTOMATION`-schema SQL file anywhere under `sql/` in this repo. This is the one gap-closing task (Gap 2 in the plan) that was explicitly deferred, not attempted.

## 2. Dynamic Tables

```sql
SHOW DYNAMIC TABLES IN DATABASE SUPPLY_CHAIN;
```

28 rows — 15 in `SILVER`, 13 in `GOLD` — matching the counts recorded in `sql/02_silver/README.md` and `sql/03_gold/README.md`. Suspend/resume between working sessions is now handled by two scripts, `sql/09_ops/pause_compute.sql` and `sql/09_ops/resume_compute.sql` (split from the original single `pause_resume_compute.sql` for clarity).

## 3. Semantic View

```sql
DESCRIBE SEMANTIC VIEW SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY;
SHOW SEMANTIC VIEWS IN DATABASE SUPPLY_CHAIN;
```

1 semantic view, `SUPPLY_CHAIN_ONTOLOGY`, with 9 tables / 10 relationships / 5 metrics / 5 dimensions / 4 facts — matching `sql/04_semantic_view/README.md` § "Structural validation".

## 4. Cortex Search Service

```sql
SHOW CORTEX SEARCH SERVICES IN SCHEMA SUPPLY_CHAIN.SEMANTIC_MODELS;
```

1 row: `SUPPLY_CHAIN_DOCUMENTS`, `embedding_model = snowflake-arctic-embed-m-v1.5`, `source_data_num_rows = 11`, `target_lag = 1 hour`. Matches `sql/04_semantic_view/README.md`.

## 5. Governance tags

```sql
SHOW TAGS IN SCHEMA SUPPLY_CHAIN.GOVERNANCE;
```

3 rows: `SOURCE_SYSTEM`, `DATA_QUALITY_ISSUE`, `LIFECYCLE` — matching `sql/00_source_schemas/README.md` and `01_governance_tags.sql`.

## 6. Roles — updated, was a gap, now closed

```sql
SHOW ROLES LIKE 'SUPPLY_CHAIN%';
```

**3 rows** (was 1): `SUPPLY_CHAIN_ADMIN`, `SUPPLY_CHAIN_ANALYST_RO`, `SUPPLY_CHAIN_TASK_EXECUTOR`. The least-privilege RBAC split designed in `.snowflake/cortex/plans/rbac-marketplace-cost-testing-gaps.plan.md` (Task 1) is now created by `sql/07_rbac/create_analyst_and_executor_roles.sql`, including a negative-privilege test (a `CREATE TABLE` attempt under `SUPPLY_CHAIN_ANALYST_RO` failed with "Insufficient privileges," confirming the role is genuinely read-only) — see `sql/07_rbac/README.md` § "Verification performed". **Known remaining gap:** the Streamlit app and `agents/agent_router.py` are not yet rewired to actually connect *as* `SUPPLY_CHAIN_ANALYST_RO` — the roles exist and are grant-complete, but nothing runs under them yet.

## 7. Tasks

```sql
SHOW TASKS IN DATABASE SUPPLY_CHAIN;
```

0 rows. No scheduled automation exists — consistent with §1.

## 8. Marketplace enrichment — updated, was a gap, now closed

```sql
SHOW DATABASES LIKE '%WEATHER%';
```

**1 row** (was 0): `WEATHER_MARKETPLACE`, acquired from the free "Pelmorex Weather Source: Frostbyte" listing (global name `GZSOZ1LLEL`). `sql/08_marketplace_enrichment/01_acquire_weather_listing.sql` performs the acquisition; `02_region_weather_enrichment.sql` builds `SUPPLY_CHAIN.GOLD.v_shipment_weather_risk`, joining shipments to weather observations by destination region and ship date. See `sql/08_marketplace_enrichment/README.md` for the honestly-reported coverage limitation (the free listing only covers 3 of 5 synthetic plant regions) and the correlation query's actual output (408 of 800 shipments matched; sample too small in the severe-weather bucket to claim a real signal — reported as such, not oversold).

## 9. Workspaces — updated, was a gap, now closed

```sql
SHOW WORKSPACES;
```

**2 rows** (was 1): the default personal workspace `USER$RAJANAND.PUBLIC.DEFAULT$`, plus `SUPPLY_CHAIN.GOVERNANCE.LEGACY_QUERIES_WORKSPACE` — created via `CREATE WORKSPACE` / `PUT` / `COMMIT` per `sql/10_workspace_artifact/README.md`, containing `legacy_before_queries.sql` (all 4 metrics' legacy divergence queries plus the governed semantic-view validation query, each with its actually-observed result recorded as a comment).

## 10. Streamlit app

```sql
SHOW STREAMLITS IN DATABASE SUPPLY_CHAIN;
```

1 row: `SUPPLY_CHAIN_ONTOLOGY_APP` in `SUPPLY_CHAIN.SEMANTIC_MODELS`, `query_warehouse = COMPUTE_WH`, `runtime_name = SYSTEM$ST_CONTAINER_RUNTIME_PY3_11`. Matches the deployment manifest in `snowflake.yml`. (The local `output/bundle/` build directory this command produces is a regenerable artifact and is gitignored — `snowflake.yml` + `streamlit_app.py` are the source of truth for what's deployed, not the bundle copy.)

## 11. Warehouse configuration — updated, was a discrepancy, now resolved

```sql
SHOW WAREHOUSES LIKE 'COMPUTE_WH';
```

`size = X-Small`, **`auto_suspend = 60`** (was 300). `sql/09_ops/token_cost_tracking.sql` explicitly runs `ALTER WAREHOUSE COMPUTE_WH SET AUTO_SUSPEND = 60;` to match the master plan's stated cost decision — this is now a committed, executed script, not just a plan-file claim. The same script also captures real 30-day usage numbers (recorded in `docs/token-and-cost-tracking.md`): Cortex Analyst + Cortex Search combined ≈1.14 credits, vs. ≈8.79 credits for the `COMPUTE_WH` warehouse over the same window — most spend is Dynamic Table refresh, not the AI layer.

---

*This snapshot reflects account state as of the gap-closing pass on 2026-09-12 and will drift as the project continues. If you have your own Snowflake trial account and want to reproduce the "DONE" claims independently, every script referenced above is the actual, unmodified script committed to this repo under `sql/`.*
