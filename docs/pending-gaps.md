# Pending gaps (explicitly deferred)

Tracking note for the two items intentionally left out of the RBAC/Marketplace/cost/testing
pass, per explicit decision rather than oversight.

## Gap 2 — `AUTOMATION` schema, Snowflake Tasks, Slack/email alerting

**Status: deferred, not started.**

Scope (from the master plan, Phase 8 / Task 14): `SUPPLY_CHAIN.AUTOMATION` schema,
`at_risk_orders_snapshot` + `daily_health_metrics` tables, `refresh_at_risk_orders` +
`daily_health_snapshot` Tasks, and a Slack (or email, given this trial account has no
External Access Integration) alert on new high-risk rows.

`SUPPLY_CHAIN_TASK_EXECUTOR` (created in `sql/07_rbac/`) is already sized for this —
it has `EXECUTE TASK ON ACCOUNT` and `OPERATE` on every existing Dynamic Table/Cortex
Search service. When this work starts, add:

```sql
GRANT USAGE, CREATE TASK ON SCHEMA SUPPLY_CHAIN.AUTOMATION TO ROLE SUPPLY_CHAIN_TASK_EXECUTOR;
```

No account-level notification integration, secret, or external access integration exists
yet (confirmed via `SHOW NOTIFICATION INTEGRATIONS`, `SHOW SECRETS IN ACCOUNT`,
`SHOW EXTERNAL ACCESS INTEGRATIONS` — all empty).

## Gap 6 — custom CoCo skill (Task 15, stretch)

**Status: deferred, not started.**

Scope (from the master plan, Phase 10): package a `skills/supply-chain-analyst-skill/`
installable plugin wrapping `agents/agent_router.py`'s callable tools
(`ask_supply_chain_analyst`, `ask_supplier_contracts`, `run_what_if_supplier_delay`,
`trace_root_cause`) as CoCo skill actions. This is explicitly a P3/"nice-to-have"
ingenuity-bonus item per the plan's priority tiers, not compliance-gating.

Not started in this pass. If picked up later, use the `skill-development` skill's
`create-from-scratch` workflow rather than authoring the skill manifest by hand.
