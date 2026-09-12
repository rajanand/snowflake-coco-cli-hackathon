# Phase: RBAC least-privilege role split

Closes Task 18 of the master plan ("Add least-privilege RBAC role split — Streamlit/agent
connects as read-only, not admin"). Until this script ran, `SUPPLY_CHAIN_ADMIN` was the
only role in the account and everything (build work, the Streamlit app, the agent router,
ops scripts) ran under it.

## Roles created

### `SUPPLY_CHAIN_ANALYST_RO` — read-only consumption

Grants match what `streamlit_app.py` and `agents/agent_router.py` **actually query today**:

| Object | Privilege | Why |
|---|---|---|
| `SUPPLY_CHAIN` database, `COMPUTE_WH` warehouse | `USAGE` | baseline |
| `SOURCE_ERP`, `SOURCE_LOGISTICS_TMS`, `SOURCE_SUPPLIER_PORTAL`, `SOURCE_IOT_SENSOR`, `SOURCE_FINANCE` schemas + all/future tables | `USAGE` / `SELECT` | Act 1 "Before/Chaos" legacy divergence demo queries these directly |
| `SILVER` schema + all/future tables **and dynamic tables** | `USAGE` / `SELECT` | entity-resolution proof (`shipment_crosswalk`) |
| `GOLD` schema + all/future tables **and dynamic tables** | `USAGE` / `SELECT` | Acts 2–5 query fact/dim tables directly, not just through the semantic view |
| `SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY` | `SELECT ON SEMANTIC VIEW` | the governed consumption surface (Cortex Analyst) |
| `SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS` | `USAGE ON CORTEX SEARCH SERVICE` | document-intelligence sub-agent |

**Known gap / caveat:** the Streamlit sidebar badge text says "🔒 Connected as
`SUPPLY_CHAIN_ANALYST_RO` — read-only, semantic layer only." That framing is aspirational —
the actual grants (and the app's actual queries) are broader than semantic-layer-only,
because Acts 1–4 bypass the semantic view and hit `GOLD`/`SILVER`/`SOURCE_*` tables
directly. This role is scoped to match reality (least privilege = what's actually used),
not the badge copy. If the app is later refactored to route everything through the
semantic view, this role's `SOURCE_*`/`SILVER`/`GOLD` table grants can be dropped in favor
of `SELECT` on the semantic view alone.

**Important implementation detail:** in this Snowflake version, `GRANT SELECT ON ALL
TABLES IN SCHEMA ...` does **not** cover Dynamic Tables — they're a distinct grantable
object type. Since every object in `SILVER` and all but one object in `GOLD`
(`dim_date` is the one plain, static table) are Dynamic Tables, the script grants
`SELECT ON ALL DYNAMIC TABLES` / `FUTURE DYNAMIC TABLES` explicitly in both schemas.
Confirmed via `SHOW GRANTS TO ROLE` before and after the fix.

### `SUPPLY_CHAIN_TASK_EXECUTOR` — operational

Sized for exactly what `sql/09_ops/pause_resume_compute.sql` already does, plus
near-term Task automation:

| Object | Privilege | Why |
|---|---|---|
| `COMPUTE_WH` | `USAGE`, `OPERATE` | suspend/resume the warehouse |
| All 15 `SILVER` Dynamic Tables + future | `OPERATE` | suspend/resume for cost control |
| All 13 `GOLD` Dynamic Tables + future | `OPERATE` | suspend/resume for cost control |
| `SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS` | `OPERATE ON CORTEX SEARCH SERVICE` | suspend/resume indexing+serving |
| Account | `EXECUTE TASK ON ACCOUNT` | run Snowflake Tasks (granted by `ACCOUNTADMIN`) |

**Deliberately not granted:** `CREATE TASK` / `USAGE` on an `AUTOMATION` schema — that
schema doesn't exist yet. Building the `AUTOMATION` schema, Tasks, and alerting is a
separate, currently-deferred piece of work (tracked separately — see the "still pending"
note below). Add the grant when that work starts:

```sql
GRANT USAGE, CREATE TASK ON SCHEMA SUPPLY_CHAIN.AUTOMATION TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
```

## Verification performed

1. `SHOW GRANTS TO ROLE SUPPLY_CHAIN_ANALYST_RO` / `..._TASK_EXECUTOR` — confirmed the
   full grant list (52 rows for `ANALYST_RO`, 36 for `TASK_EXECUTOR`).
2. **Negative test** (proves the role is genuinely read-only, not silently admin):
   - `USE ROLE SUPPLY_CHAIN_ANALYST_RO; CREATE TABLE SUPPLY_CHAIN.GOLD.SHOULD_FAIL_TEST (x INT);`
     → failed with `Insufficient privileges to operate on schema 'GOLD'`. ✅
   - `SELECT CURRENT_ROLE(), COUNT(*) FROM SUPPLY_CHAIN.GOLD.fact_shipment;` while active
     role was `SUPPLY_CHAIN_ANALYST_RO` → returned 800 rows. ✅
   - `SELECT * FROM SEMANTIC_VIEW(SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY
     METRICS shipment.on_time_delivery_rate);` → returned 64.875%. ✅
3. **OPERATE test** (`TASK_EXECUTOR`): resumed then re-suspended
   `SUPPLY_CHAIN.GOLD.dim_customer` — both `ALTER DYNAMIC TABLE` statements succeeded,
   object restored to its original `SUSPENDED` state afterward. ✅

## What this does NOT do

- Does **not** rewire `streamlit_app.py` or `agents/agent_router.py` to actually run as
  `SUPPLY_CHAIN_ANALYST_RO` — both still run under the connection's default role
  (`SUPPLY_CHAIN_ADMIN` for the local agent, the Streamlit app's owner role in Snowsight).
  The roles are created and grant-complete, ready to be wired in as a follow-up.
- Does **not** grant anything related to the `AUTOMATION` schema, Tasks, or Slack/email
  alerting — that whole area is still pending (deferred by explicit decision).
