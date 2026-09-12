"""Phase 5: Hybrid multi-agent router for the supply chain ontology.

Architecture (per the plan):
    SupplyChainAgentRouter
        -> PreQueryValidator            (entity/forbidden-term/length/language checks)
        -> intent classification
            - "standard"      -> CortexAnalystClient (main agent, backed by the native
                                  SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY view)
            - "document_qa"   -> DocumentQAAgent      (Cortex Search over supplier contracts)
            - "what_if"       -> SimulationAgent       (parameterized delay-impact what-if)
            - "root_cause"    -> EvidenceTraceAgent     (walks Supplier->Part->Plant->Order chain)
            - "at_risk"       -> CortexAnalystClient with the at_risk_orders verified query
        -> PostQueryEnricher            (extracts supplier names, attaches Cortex Search
                                          evidence snippets as "Supporting Evidence")
        -> confidence-threshold fallback ("I'm not confident in this answer -- here's what
                                          I found and why" instead of guessing)

All sub-agents are exposed as plain callables AND registered in AGENT_TOOLS so they can be
handed to any tool-calling LLM as function-call targets, not just invoked internally by the
router.

Auth: uses the local `connections.toml` connection profile (same one CoCo uses) via
snowflake-connector-python's `connection_name=` parameter, which handles the
OAUTH_AUTHORIZATION_CODE flow transparently. The resulting session token is reused as the
Bearer token for the Cortex Analyst and Cortex Search REST APIs.
"""

from __future__ import annotations

import json
import re
import dataclasses
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import requests
import snowflake.connector

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

CONNECTION_NAME = "GC94671"
DATABASE = "SUPPLY_CHAIN"
SEMANTIC_VIEW_FQN = f"{DATABASE}.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY"
CORTEX_SEARCH_SERVICE_FQN = f"{DATABASE}.SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS"

CONFIDENCE_THRESHOLD = 0.6
MAX_QUESTION_LENGTH = 500
FORBIDDEN_TERMS = ("drop table", "delete from", "truncate", "grant ", "alter role")


# -----------------------------------------------------------------------------
# Snowflake session (shared by all agents)
# -----------------------------------------------------------------------------

class SnowflakeSession:
    """Thin wrapper providing a SQL connection and a REST bearer token."""

    def __init__(self, connection_name: str = CONNECTION_NAME):
        self._conn = snowflake.connector.connect(connection_name=connection_name)
        self.account = self._conn.account
        # Use the connector's actual resolved host, not f"{account}.snowflakecomputing.com" --
        # that reconstruction drops the region/cloud suffix for accounts like
        # sc23256.ap-northeast-1.aws (conn.account is just "sc23256"), producing
        # a 404 against the Cortex Analyst REST API.
        self.host = self._conn.host

    @property
    def token(self) -> str:
        # snowflake-connector-python exposes the active session token via rest.token
        return self._conn.rest.token  # type: ignore[attr-defined]

    def sql(self, query: str, params: Optional[dict] = None) -> list[dict]:
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
            # Required: the REST API defaults to treating the bearer token as an
            # OAuth access token if this header is omitted. conn.rest.token here
            # is a Snowflake session token (starts with "ver:3-hint..."), not a
            # raw OAuth token, so omitting this header produces a 401 "Invalid
            # OAuth access token" even with valid, working credentials.
            "X-Snowflake-Authorization-Token-Type": "SNOWFLAKE_SESSION_TOKEN",
        }

    def close(self) -> None:
        self._conn.close()


# -----------------------------------------------------------------------------
# Structured response contract every agent returns
# -----------------------------------------------------------------------------

@dataclass
class AgentResponse:
    text: str
    sql: Optional[str] = None
    confidence: float = 1.0
    base_table: Optional[str] = None
    measure_name: Optional[str] = None
    supporting_evidence: list[str] = field(default_factory=list)
    agent_name: str = "unknown"

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


# -----------------------------------------------------------------------------
# PreQueryValidator
# -----------------------------------------------------------------------------

class PreQueryValidator:
    """Runs before any question reaches an agent. Raises ValueError on rejection."""

    def validate(self, question: str) -> None:
        if not question or not question.strip():
            raise ValueError("Empty question.")
        if len(question) > MAX_QUESTION_LENGTH:
            raise ValueError(f"Question exceeds {MAX_QUESTION_LENGTH} characters.")
        lowered = question.lower()
        for term in FORBIDDEN_TERMS:
            if term in lowered:
                raise ValueError(f"Question contains a forbidden term: '{term.strip()}'.")
        if not re.search(r"[a-zA-Z]", question):
            raise ValueError("Question does not appear to contain natural language.")


# -----------------------------------------------------------------------------
# PostQueryEnricher
# -----------------------------------------------------------------------------

class PostQueryEnricher:
    """Runs after an agent produces an answer. Extracts supplier names and pulls
    matching Cortex Search document snippets, appended as 'Supporting Evidence'.
    """

    SUPPLIER_ID_PATTERN = re.compile(r"\bSUP-\d{4}\b")

    def __init__(self, session: SnowflakeSession):
        self.session = session

    def enrich(self, response: AgentResponse) -> AgentResponse:
        supplier_ids = set(self.SUPPLIER_ID_PATTERN.findall(response.text or ""))
        if response.sql:
            supplier_ids |= set(self.SUPPLIER_ID_PATTERN.findall(response.sql))
        if not supplier_ids:
            return response

        for supplier_id in supplier_ids:
            snippet = self._search_supplier_contract(supplier_id)
            if snippet:
                response.supporting_evidence.append(snippet)
        return response

    def _search_supplier_contract(self, supplier_id: str) -> Optional[str]:
        """Query the Cortex Search service if it exists; fail gracefully otherwise
        (the document corpus is built in Phase 8 -- this stays decoupled so the
        router works before and after that phase lands).
        """
        try:
            rows = self.session.sql(
                f"""
                SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                    '{CORTEX_SEARCH_SERVICE_FQN}',
                    '{{"query": "{supplier_id} SLA payment terms", "limit": 1}}'
                ) AS result
                """
            )
            if not rows:
                return None
            payload = json.loads(rows[0]["RESULT"])
            hits = payload.get("results", [])
            if not hits:
                return None
            return f"[{supplier_id}] {hits[0].get('chunk', '')[:300]}"
        except Exception:
            # Search service not deployed yet, or supplier has no contract on file.
            return None


# -----------------------------------------------------------------------------
# Main agent: Cortex Analyst over the semantic view
# -----------------------------------------------------------------------------

class CortexAnalystClient:
    """Calls the Cortex Analyst Message API against SUPPLY_CHAIN_ONTOLOGY and
    returns a structured {text, sql, confidence} response -- not just narrative
    text -- so the caller can display the generated SQL and extract
    base_table/measure_name for the cross-persona consistency-proof UI.
    """

    ENDPOINT = "/api/v2/cortex/analyst/message"

    def __init__(self, session: SnowflakeSession, semantic_view: str = SEMANTIC_VIEW_FQN):
        self.session = session
        self.semantic_view = semantic_view

    def ask(self, question: str) -> AgentResponse:
        url = f"https://{self.session.host}{self.ENDPOINT}"
        body = {
            "messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
            "semantic_view": self.semantic_view,
        }
        resp = requests.post(url, headers=self.session.rest_headers(), json=body, timeout=60)
        resp.raise_for_status()
        payload = resp.json()

        text, sql, confidence = self._parse(payload)
        base_table, measure_name = self._extract_sql_targets(sql)

        return AgentResponse(
            text=text,
            sql=sql,
            confidence=confidence,
            base_table=base_table,
            measure_name=measure_name,
            agent_name="CortexAnalystClient",
        )

    @staticmethod
    def _parse(payload: dict) -> tuple[str, Optional[str], float]:
        text_parts: list[str] = []
        sql: Optional[str] = None
        confidence = 1.0

        message = payload.get("message", {})
        for item in message.get("content", []):
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif item.get("type") == "sql":
                sql = item.get("statement")
            elif item.get("type") == "confidence":
                confidence = item.get("value", confidence)

        return " ".join(text_parts).strip() or "(no narrative response)", sql, confidence

    @staticmethod
    def _extract_sql_targets(sql: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """Best-effort extraction of the primary base table and measure/metric name
        referenced by the generated SQL, used to prove cross-persona consistency
        (same phrasing-independent question must resolve to the same base_table
        and measure_name, not just the same numeric value).
        """
        if not sql:
            return None, None
        base_table_match = re.search(r"FROM\s+([A-Za-z0-9_.\"]+)", sql, re.IGNORECASE)
        base_table = base_table_match.group(1) if base_table_match else None

        # Metrics surface as aliased columns in the SEMANTIC_VIEW(...) projection,
        # e.g. "METRICS shipment.on_time_delivery_rate" or an AS alias in the SELECT.
        measure_match = re.search(
            r"METRICS\s+([A-Za-z0-9_.]+)", sql, re.IGNORECASE
        ) or re.search(r"AS\s+([A-Za-z0-9_]+)\s*$", sql.strip(), re.IGNORECASE)
        measure_name = measure_match.group(1) if measure_match else None

        return base_table, measure_name


# -----------------------------------------------------------------------------
# Sub-agents
# -----------------------------------------------------------------------------

class DocumentQAAgent:
    """Answers questions about supplier contracts via Cortex Search over
    AI_PARSE_DOCUMENT-parsed PDFs (SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_DOCUMENTS,
    built in Phase 8). Degrades gracefully with a clear message if the search
    service doesn't exist yet.
    """

    def __init__(self, session: SnowflakeSession):
        self.session = session

    def ask(self, question: str) -> AgentResponse:
        try:
            rows = self.session.sql(
                f"""
                SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                    '{CORTEX_SEARCH_SERVICE_FQN}',
                    OBJECT_CONSTRUCT('query', %(q)s, 'limit', 3)::VARCHAR
                ) AS result
                """,
                {"q": question},
            )
            payload = json.loads(rows[0]["RESULT"])
            hits = payload.get("results", [])
            if not hits:
                return AgentResponse(
                    text="No matching supplier contract clauses found.",
                    confidence=0.3,
                    agent_name="DocumentQAAgent",
                )
            snippets = [h.get("chunk", "") for h in hits]
            return AgentResponse(
                text=snippets[0],
                confidence=0.85,
                supporting_evidence=snippets[1:],
                agent_name="DocumentQAAgent",
            )
        except Exception as exc:
            return AgentResponse(
                text=(
                    "Document search isn't available yet -- the "
                    f"{CORTEX_SEARCH_SERVICE_FQN} Cortex Search service (Phase 8) "
                    f"hasn't been deployed in this environment. ({exc})"
                ),
                confidence=0.0,
                agent_name="DocumentQAAgent",
            )


class SimulationAgent:
    """Parameterized what-if: 'If supplier X is delayed by N days, how many
    downstream customer orders are put at risk?'
    """

    WHAT_IF_SQL = """
        SELECT
            co.customer_order_id,
            co.requested_delivery_date,
            DATEADD(day, %(delay_days)s, co.requested_delivery_date) AS simulated_delivery_date,
            IFF(DATEADD(day, %(delay_days)s, co.requested_delivery_date) > co.requested_delivery_date, TRUE, FALSE) AS newly_at_risk
        FROM SUPPLY_CHAIN.GOLD.fact_order_fulfillment co
        JOIN SUPPLY_CHAIN.GOLD.fact_shipment fs ON fs.part_key = co.part_key
        WHERE fs.supplier_id = %(supplier_id)s
        QUALIFY ROW_NUMBER() OVER (PARTITION BY co.customer_order_id ORDER BY co.order_date DESC) = 1
    """

    def __init__(self, session: SnowflakeSession):
        self.session = session

    def simulate(self, supplier_id: str, delay_days: int) -> AgentResponse:
        rows = self.session.sql(
            self.WHAT_IF_SQL, {"supplier_id": supplier_id, "delay_days": delay_days}
        )
        at_risk = [r for r in rows if r.get("NEWLY_AT_RISK")]
        text = (
            f"If {supplier_id} is delayed by {delay_days} day(s), "
            f"{len(at_risk)} of {len(rows)} downstream customer orders "
            f"sharing a part with that supplier would newly slip past their "
            f"requested delivery date."
        )
        return AgentResponse(
            text=text,
            sql=self.WHAT_IF_SQL,
            confidence=0.9 if rows else 0.4,
            base_table="SUPPLY_CHAIN.GOLD.fact_order_fulfillment",
            measure_name="newly_at_risk",
            agent_name="SimulationAgent",
        )


class EvidenceTraceAgent:
    """Root-cause: walks the Supplier -> Part -> Plant -> CustomerOrder chain for
    a given at-risk order, the literal 'walk the ontology chain' query.
    """

    ROOT_CAUSE_SQL = """
        SELECT
            co.customer_order_id,
            co.on_time_flag AS order_on_time,
            fs.shipment_id,
            fs.supplier_id,
            fs.is_on_time AS shipment_on_time,
            fs.actual_receipt_date,
            fs.planned_receipt_date,
            sup.supplier_name,
            sup.tier_name
        FROM SUPPLY_CHAIN.GOLD.fact_order_fulfillment co
        JOIN SUPPLY_CHAIN.GOLD.fact_shipment fs ON fs.part_key = co.part_key
        JOIN SUPPLY_CHAIN.GOLD.dim_supplier sup ON sup.supplier_key = fs.supplier_key
        WHERE co.customer_order_id = %(order_id)s
        ORDER BY fs.actual_ship_date DESC
    """

    def __init__(self, session: SnowflakeSession):
        self.session = session

    def trace(self, customer_order_id: str) -> AgentResponse:
        rows = self.session.sql(self.ROOT_CAUSE_SQL, {"order_id": customer_order_id})
        if not rows:
            return AgentResponse(
                text=f"No shipment chain found for order {customer_order_id}.",
                confidence=0.2,
                agent_name="EvidenceTraceAgent",
            )
        late_shipments = [r for r in rows if r.get("SHIPMENT_ON_TIME") == 0]
        if late_shipments:
            culprit = late_shipments[0]
            text = (
                f"Order {customer_order_id} traces to supplier "
                f"{culprit['SUPPLIER_NAME']} ({culprit['SUPPLIER_ID']}, "
                f"{culprit['TIER_NAME']}), whose shipment {culprit['SHIPMENT_ID']} "
                f"arrived {culprit['ACTUAL_RECEIPT_DATE']} against a planned "
                f"{culprit['PLANNED_RECEIPT_DATE']} -- the root cause of the delay."
            )
        else:
            text = f"Order {customer_order_id}'s upstream shipments were all on time; delay is not supplier-attributable."
        return AgentResponse(
            text=text,
            sql=self.ROOT_CAUSE_SQL,
            confidence=0.9,
            base_table="SUPPLY_CHAIN.GOLD.fact_shipment",
            measure_name="is_on_time",
            agent_name="EvidenceTraceAgent",
        )


# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------

_WHAT_IF_PATTERN = re.compile(r"what.?if|delay(?:ed)? by \d+ days?", re.IGNORECASE)
_ROOT_CAUSE_PATTERN = re.compile(r"root cause|why (is|was) order|trace order", re.IGNORECASE)
_AT_RISK_PATTERN = re.compile(r"at.?risk", re.IGNORECASE)
_DOCUMENT_PATTERN = re.compile(r"contract|SLA|payment terms|penalty clause", re.IGNORECASE)


class SupplyChainAgentRouter:
    """Classifies intent and routes to the right agent, applying pre-query
    validation, post-query enrichment, and confidence-threshold fallback.
    """

    def __init__(self, session: Optional[SnowflakeSession] = None):
        self.session = session or SnowflakeSession()
        self.validator = PreQueryValidator()
        self.enricher = PostQueryEnricher(self.session)
        self.analyst = CortexAnalystClient(self.session)
        self.document_qa = DocumentQAAgent(self.session)
        self.simulator = SimulationAgent(self.session)
        self.tracer = EvidenceTraceAgent(self.session)

    def classify_intent(self, question: str) -> str:
        if _WHAT_IF_PATTERN.search(question):
            return "what_if"
        if _ROOT_CAUSE_PATTERN.search(question):
            return "root_cause"
        if _AT_RISK_PATTERN.search(question):
            return "at_risk"
        if _DOCUMENT_PATTERN.search(question):
            return "document_qa"
        return "standard"

    def ask(self, question: str, **kwargs: Any) -> AgentResponse:
        self.validator.validate(question)
        intent = self.classify_intent(question)

        if intent == "what_if":
            supplier_id = kwargs.get("supplier_id")
            delay_days = kwargs.get("delay_days", 3)
            if not supplier_id:
                raise ValueError("what_if intent requires supplier_id kwarg.")
            response = self.simulator.simulate(supplier_id, delay_days)
        elif intent == "root_cause":
            order_id = kwargs.get("customer_order_id")
            if not order_id:
                raise ValueError("root_cause intent requires customer_order_id kwarg.")
            response = self.tracer.trace(order_id)
        elif intent == "document_qa":
            response = self.document_qa.ask(question)
        else:
            # "standard" and "at_risk" both go through Cortex Analyst; at_risk
            # questions are just phrased in natural language and rely on the
            # semantic view's synonyms/metrics to resolve correctly.
            response = self.analyst.ask(question)

        response = self.enricher.enrich(response)

        if response.confidence < CONFIDENCE_THRESHOLD:
            response.text = (
                "I'm not confident in this answer -- here's what I found and why: "
                f"{response.text}"
            )

        return response

    def close(self) -> None:
        self.session.close()


# -----------------------------------------------------------------------------
# Tool registry -- sub-agents exposed as callable tools/functions, not just
# internal classes invoked by the router
# -----------------------------------------------------------------------------

def build_agent_tools(router: SupplyChainAgentRouter) -> dict[str, Callable[..., AgentResponse]]:
    return {
        "ask_supply_chain_analyst": router.analyst.ask,
        "ask_supplier_contracts": router.document_qa.ask,
        "run_what_if_supplier_delay": router.simulator.simulate,
        "trace_root_cause": router.tracer.trace,
    }


AGENT_TOOLS_SCHEMA = [
    {
        "name": "ask_supply_chain_analyst",
        "description": "Ask a natural-language question against the governed supply chain semantic view (OTD, fill rate, DOI, landed cost, and more).",
        "parameters": {"question": "string"},
    },
    {
        "name": "ask_supplier_contracts",
        "description": "Search supplier contract documents (SLA, payment terms, penalty clauses) via Cortex Search.",
        "parameters": {"question": "string"},
    },
    {
        "name": "run_what_if_supplier_delay",
        "description": "Simulate the downstream impact if a given supplier is delayed by N days.",
        "parameters": {"supplier_id": "string", "delay_days": "integer"},
    },
    {
        "name": "trace_root_cause",
        "description": "Trace the Supplier->Part->Plant->CustomerOrder chain for a given at-risk order to find the root cause of a delay.",
        "parameters": {"customer_order_id": "string"},
    },
]


# -----------------------------------------------------------------------------
# Manual test harness
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    router = SupplyChainAgentRouter()
    try:
        for q in [
            "How are we tracking against planned delivery dates this quarter?",
            "What's our suppliers' on-time delivery performance?",
            "What percentage of shipments arrived on schedule?",
            "Are we hitting our delivery dates?",
        ]:
            r = router.ask(q)
            print(f"\nQ: {q}")
            print(f"  base_table={r.base_table} measure_name={r.measure_name} confidence={r.confidence}")
            print(f"  A: {r.text}")
    finally:
        router.close()
