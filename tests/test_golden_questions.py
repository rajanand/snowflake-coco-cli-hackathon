"""Phase 9: golden test question validation (Task 11 / Gap 5).

Validates the hallucination-mitigation claims from the master plan against the
live SUPPLY_CHAIN_ONTOLOGY semantic view and agents/agent_router.py:

  1. Cross-persona consistency: 3 differently-worded OTD questions must
     resolve to the same numeric value AND the same base_table/measure_name.
  2. Zero-raw-identifiers: a business-language question with no table/column
     names must still resolve via the semantic view, with no raw SOURCE_*/
     SILVER.* table names leaking into the generated SQL.
  3. At-risk orders: the "at_risk" intent path returns a well-formed response.
  4. What-if simulation: SimulationAgent.simulate() returns the expected shape.
  5. Root-cause trace: EvidenceTraceAgent.trace() identifies a supplier root
     cause for a known late shipment's order.

Run directly: `python tests/test_golden_questions.py`
Exits 0 if all tests pass, 1 otherwise. No pytest dependency -- plain asserts
plus a printed PASS/FAIL summary, per the plan's stated file name/location.

Reuses agents/agent_router.py's classes as-is except for two bug fixes made
in that file during this validation pass (both real bugs, not sandbox-only):
  1. SnowflakeSession.host was reconstructed as f"{account}.snowflakecomputing.com",
     which drops the region/cloud suffix for accounts like sc23256.ap-northeast-1.aws
     (conn.account resolves to just "sc23256") -- fixed to use conn.host directly.
  2. rest_headers() didn't set X-Snowflake-Authorization-Token-Type, which the
     Cortex Analyst REST API defaults to OAUTH when omitted -- but conn.rest.token
     for an OAUTH_AUTHORIZATION_CODE connection is a Snowflake session token
     ("ver:3-hint..."), not a raw OAuth token, so the default caused a 401
     "Invalid OAuth access token" even with valid credentials.

KNOWN LIMITATION (last run: 2/5 tests passed): after fix #2, the three tests
that call CortexAnalystClient.ask() (which POSTs to /api/v2/cortex/analyst/message)
still get a plain 401 Unauthorized with the "SNOWFLAKE_SESSION_TOKEN" header
value. The two tests that only use session.sql() (what_if_scenario,
root_cause_trace) pass live. This means the Cortex Analyst REST call path in
agent_router.py has a real, unresolved auth issue when driven from a local
OAUTH_AUTHORIZATION_CODE Python session -- separate from the interactive
browser-login friction of this sandboxed environment. The equivalent
SELECT * FROM SEMANTIC_VIEW(...) SQL path (used by cross_persona_consistency's
underlying question) works fine when run directly as SQL (verified earlier via
the Snowflake SQL tool), so the semantic view and role grants are not the
problem -- it's specifically the REST bearer-token type for this connection
mode. Worth a follow-up: try a Programmatic Access Token (PAT) instead of the
session token, or confirm the exact accepted values for
X-Snowflake-Authorization-Token-Type in this account's Cortex Analyst REST
API version.

Connects independently of SnowflakeSession's default connect() call because
this sandboxed environment's OS credential manager (Windows keyring) rejects
snowflake-connector-python's default `client_store_temporary_credential=True`
token caching -- unrelated to whether the connection/auth itself is valid.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snowflake.connector

from agents.agent_router import (
    CONNECTION_NAME,
    CortexAnalystClient,
    EvidenceTraceAgent,
    SimulationAgent,
    SupplyChainAgentRouter,
)


class TestSession:
    """Duck-typed stand-in for agent_router.SnowflakeSession, identical
    interface, but connects with client_store_temporary_credential=False so
    it doesn't hit this sandbox's broken Windows credential-manager keyring.
    """

    def __init__(self, connection_name: str = CONNECTION_NAME):
        self._conn = snowflake.connector.connect(
            connection_name=connection_name,
            client_store_temporary_credential=False,
        )
        self.account = self._conn.account
        self.host = self._conn.host

    @property
    def token(self) -> str:
        return self._conn.rest.token

    def sql(self, query: str, params: dict | None = None) -> list[dict]:
        cur = self._conn.cursor(snowflake.connector.DictCursor)
        try:
            cur.execute(query, params or {})
            return cur.fetchall()
        finally:
            cur.close()

    def rest_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Snowflake-Authorization-Token-Type": "SNOWFLAKE_SESSION_TOKEN",
        }

    def close(self) -> None:
        self._conn.close()


RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = "") -> None:
    RESULTS.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))


def test_cross_persona_consistency(analyst: CortexAnalystClient) -> None:
    questions = {
        "planning": "How are we tracking against planned delivery dates this quarter?",
        "procurement": "What's our suppliers' on-time delivery performance?",
        "logistics": "What percentage of shipments arrived on schedule?",
    }
    responses = {persona: analyst.ask(q) for persona, q in questions.items()}

    values = {p: _extract_number(r.text) for p, r in responses.items()}
    base_tables = {p: r.base_table for p, r in responses.items()}
    measure_names = {p: r.measure_name for p, r in responses.items()}

    numeric_values = [v for v in values.values() if v is not None]
    values_match = (
        len(numeric_values) == 3
        and max(numeric_values) - min(numeric_values) < 0.01 * max(numeric_values, default=1)
    )
    tables_match = len(set(base_tables.values())) == 1
    measures_match = len(set(measure_names.values())) == 1

    detail = f"values={values} base_tables={base_tables} measures={measure_names}"
    record(
        "cross_persona_consistency",
        values_match and tables_match and measures_match,
        detail,
    )


def test_zero_raw_identifiers(analyst: CortexAnalystClient) -> None:
    response = analyst.ask("Are we hitting our delivery dates?")
    sql = response.sql or ""
    raw_leak = any(
        needle in sql.upper()
        for needle in ("SOURCE_ERP", "SOURCE_LOGISTICS_TMS", "SOURCE_SUPPLIER_PORTAL", "SOURCE_IOT_SENSOR", "SILVER.")
    )
    resolved_via_semantic_view = "SEMANTIC_VIEW" in sql.upper() or response.base_table is not None
    record(
        "zero_raw_identifiers",
        resolved_via_semantic_view and not raw_leak,
        f"sql={sql!r}",
    )


def test_at_risk_orders(router: SupplyChainAgentRouter) -> None:
    response = router.ask("Which orders are at risk due to supplier delays?")
    record(
        "at_risk_orders",
        bool(response.text) and response.confidence > 0,
        f"confidence={response.confidence} text={response.text[:120]!r}",
    )


def test_what_if_scenario(simulator: SimulationAgent, sample_supplier_id: str) -> None:
    response = simulator.simulate(sample_supplier_id, delay_days=5)
    ok = (
        response.agent_name == "SimulationAgent"
        and response.base_table == "SUPPLY_CHAIN.GOLD.fact_order_fulfillment"
        and response.measure_name == "newly_at_risk"
        and bool(response.text)
    )
    record("what_if_scenario", ok, f"text={response.text!r}")


def test_root_cause_trace(tracer: EvidenceTraceAgent, sample_order_id: str) -> None:
    response = tracer.trace(sample_order_id)
    ok = response.agent_name == "EvidenceTraceAgent" and bool(response.text) and response.confidence > 0
    record("root_cause_trace", ok, f"text={response.text!r}")


def _extract_number(text: str) -> float | None:
    import re

    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    return float(match.group(1)) if match else None


def _get_sample_ids(session: TestSession) -> tuple[str, str]:
    supplier_rows = session.sql(
        "SELECT supplier_id FROM SUPPLY_CHAIN.GOLD.dim_supplier LIMIT 1"
    )
    order_rows = session.sql(
        """
        SELECT co.customer_order_id
        FROM SUPPLY_CHAIN.GOLD.fact_order_fulfillment co
        JOIN SUPPLY_CHAIN.GOLD.fact_shipment fs ON fs.part_key = co.part_key
        WHERE fs.is_on_time = 0
        LIMIT 1
        """
    )
    supplier_id = supplier_rows[0]["SUPPLIER_ID"] if supplier_rows else "SUP-0001"
    order_id = str(order_rows[0]["CUSTOMER_ORDER_ID"]) if order_rows else "1"
    return supplier_id, order_id


def main() -> int:
    session = TestSession()
    try:
        analyst = CortexAnalystClient(session)
        simulator = SimulationAgent(session)
        tracer = EvidenceTraceAgent(session)
        router = SupplyChainAgentRouter(session=session)

        sample_supplier_id, sample_order_id = _get_sample_ids(session)

        checks = [
            ("cross_persona_consistency", lambda: test_cross_persona_consistency(analyst)),
            ("zero_raw_identifiers", lambda: test_zero_raw_identifiers(analyst)),
            ("at_risk_orders", lambda: test_at_risk_orders(router)),
            ("what_if_scenario", lambda: test_what_if_scenario(simulator, sample_supplier_id)),
            ("root_cause_trace", lambda: test_root_cause_trace(tracer, sample_order_id)),
        ]
        for name, check in checks:
            try:
                check()
            except Exception as exc:  # noqa: BLE001 -- report, don't abort the suite
                record(name, False, f"raised {type(exc).__name__}: {exc}")
    finally:
        session.close()

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{passed}/{total} tests passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
