# Phase 4.5 — Legacy "Before" queries as a Snowsight Workspace

Closes the second half of Task 19 ("save the four Phase 0 legacy 'Before' queries plus the
semantic-view validation query as a named Snowsight Worksheet — gives judges a concrete,
screenshot-able Worksheets artifact").

**Uses Workspaces, not legacy Worksheets** — legacy Worksheets are being removed from
Snowsight on 2026-06-22 and Workspaces is the current SQL-scriptable replacement
(`CREATE WORKSPACE`, `PUT`, `COMMIT` — no equivalent DDL exists for legacy Worksheets).

## What's in it

`legacy_before_queries.sql` — every legacy divergence query for all 4 canonical metrics
(not just OTD), each one **actually run live** against `SUPPLY_CHAIN.SOURCE_*`/`GOLD`
before being written down, with the real result recorded as a comment:

| Metric | Legacy answers (as run live) | Governed answer |
|---|---|---|
| On-Time Delivery | ERP 89.4% / TMS 91.3% / Supplier Portal 78.6% / IoT (biased sample) | 64.875% |
| Fill Rate | Supplier PO fill 86.3% / Warehouse pick fulfillment 87.7% | Customer 90.8% / Supplier 86.294% (two distinct canonical measures) |
| Days of Inventory | Planning (forecast) 40.1 days / Finance ($-based) 506.6 days | 48.6 days |
| Landed Cost/Unit | Procurement $276.40 / Logistics $488.29 | $251.68 |

Finishes with the governed semantic-view validation query — one `SELECT * FROM
SEMANTIC_VIEW(...)` call returning all 5 governed metrics in a single row, to put next to
every divergent legacy answer above it.

Note the governed OTD (64.875%) is *lower* than any individual legacy answer — the
governance decision (plant-dock receipt as "actual", cancelled orders count as late, never
dropped) is stricter than any of the source systems' more forgiving definitions, not just a
different number in the same range. That's a genuinely useful thing for a judge to see next
to the legacy queries, not a discrepancy to explain away.

## How it was published (SQL, no UI)

```sql
CREATE WORKSPACE SUPPLY_CHAIN.GOVERNANCE.LEGACY_QUERIES_WORKSPACE;
ALTER WORKSPACE SUPPLY_CHAIN.GOVERNANCE.LEGACY_QUERIES_WORKSPACE ADD LIVE VERSION FROM LAST;
PUT file://.../legacy_before_queries.sql
    snow://workspace/SUPPLY_CHAIN.GOVERNANCE.LEGACY_QUERIES_WORKSPACE/versions/live/
    AUTO_COMPRESS=false OVERWRITE=true;
ALTER WORKSPACE SUPPLY_CHAIN.GOVERNANCE.LEGACY_QUERIES_WORKSPACE COMMIT;
```

Verified with `LIST 'snow://workspace/SUPPLY_CHAIN.GOVERNANCE.LEGACY_QUERIES_WORKSPACE/versions/head/';`
— file present, 7344 bytes, committed.

To open it in Snowsight: **Projects » Workspaces » Shared with me** (or search
`LEGACY_QUERIES_WORKSPACE`) — any role with `READ`/`WRITE` on the workspace can open it.
Currently owned by `SUPPLY_CHAIN_ADMIN`; grant `READ` to another role if a judge needs
access under a different role:

```sql
GRANT READ ON WORKSPACE SUPPLY_CHAIN.GOVERNANCE.LEGACY_QUERIES_WORKSPACE TO ROLE <role>;
```
