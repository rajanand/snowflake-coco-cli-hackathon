# Token & cost tracking (Phase 9 — System Design & Engineering)

Closes Task 20 of the master plan: right-sized warehouse called out as a deliberate
decision, plus token/cost spend evidenced with a real number rather than asserted.
Queries live in `sql/09_ops/token_cost_tracking.sql`.

## Warehouse sizing — deliberate, not default

`COMPUTE_WH` is `X-SMALL` with `AUTO_SUSPEND = 60` (tightened from `300` during this
pass — the plan explicitly calls out `X-SMALL, AUTO_SUSPEND=60` as the intended cost
decision for this workload's volume: 28 Dynamic Tables at 10–15 minute `TARGET_LAG`,
one Cortex Search service, occasional Cortex Analyst calls). Verified live via
`SHOW WAREHOUSES LIKE 'COMPUTE_WH'` after the change.

## Real numbers, last 30 days (run 2026-09-12)

| Source | Metric | Value |
|---|---|---|
| `CORTEX_ANALYST_USAGE_HISTORY` | Credits | 1.1390 |
| `CORTEX_ANALYST_USAGE_HISTORY` | Requests | 17 |
| `CORTEX_ANALYST_USAGE_HISTORY` | Active users | 1 |
| `CORTEX_SEARCH_DAILY_USAGE_HISTORY` | Credits | 0.0001 |
| `CORTEX_SEARCH_DAILY_USAGE_HISTORY` | Tokens | 4,132 |
| `CORTEX_SEARCH_DAILY_USAGE_HISTORY` | Active services | 1 |
| `WAREHOUSE_METERING_HISTORY` (`COMPUTE_WH`) | Total credits | 8.7947 |
| `WAREHOUSE_METERING_HISTORY` (`COMPUTE_WH`) | Compute credits | 8.6269 |
| `WAREHOUSE_METERING_HISTORY` (`COMPUTE_WH`) | Cloud services credits | 0.1679 |
| `WAREHOUSE_METERING_HISTORY` (`COMPUTE_WH`) | Metering hours | 14 |

**Reading these together:** Cortex Analyst + Cortex Search combined (~1.14 credits) is
under 13% of the 30-day warehouse total (8.79 credits). Almost all of the compute spend
is Dynamic Table refresh (Bronze→Silver→Gold, 28 tables) and build-time DDL, not the AI
layer — the governed semantic view and agent router are cheap to run relative to the
pipeline that feeds them. This is the real distribution, not an assumption.

## Trial credit budget

Trial accounts on this Contest track a $400 credit budget (per the master plan). At
8.79 credits/30 days for the current (mostly idle-paused) usage pattern, and with
`sql/09_ops/pause_resume_compute.sql` used to suspend all Dynamic Tables + the Cortex
Search service + the warehouse between working sessions, the pipeline is far from
exhausting that budget before the Grand Finale demo. Re-run the queries in
`token_cost_tracking.sql` periodically (they're read-only and cheap) to keep this
number current rather than trusting a stale snapshot as the demo date approaches.

## Correct views (a correction worth documenting)

The master plan's Phase 9 section names `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY`
as the source for Cortex token tracking — that view does not exist. The
Cortex AI cost skill's routing table gives the real views used here:
`CORTEX_ANALYST_USAGE_HISTORY` (credits + `REQUEST_COUNT`, aggregated per user per
hour — no token-level breakdown for Analyst) and `CORTEX_SEARCH_DAILY_USAGE_HISTORY`
(credits + `TOKENS` by `CONSUMPTION_TYPE`, daily grain, service-level only — no
user attribution).
