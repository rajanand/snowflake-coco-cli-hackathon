"""Cortex Analyst client with a transport chain and a guaranteed fallback.

Transport
---------
There is no single way to reach the Analyst Message API from Streamlit in
Snowflake, because it depends on the runtime:

* Warehouse runtimes inherit ``_snowflake`` from the stored-procedure sandbox,
  so ``send_snow_api_request`` works.
* Container runtimes do **not** provide ``_snowflake`` at all. They do run as
  Snowpark Container Services workloads, which are issued an OAuth token on
  disk plus an internal API host in the environment - so a plain HTTPS call
  reaches the same endpoint with no External Access Integration required.

Both are attempted, in that order, and the winning transport is reported in the
UI rather than hidden.

Neither is the ``requests``-with-session-token approach in
``agents/agent_router.py``, which returns 401 from a local
OAUTH_AUTHORIZATION_CODE session because a Snowflake session token is not an
OAuth access token.

Why there is always a fallback
------------------------------
The demo is live. If every transport fails, or Analyst returns prose without
SQL, the governed number must still appear - so every ask() resolves to a value
either from Analyst's own SQL or from a direct ``SEMANTIC_VIEW`` query. The UI
labels which path produced the number instead of hiding the difference; a
governed answer whose provenance is unclear would defeat the entire point.
"""

from __future__ import annotations

import json
import time

import streamlit as st

from lib import data as D

ANALYST_PATH = "/api/v2/cortex/analyst/message"
SPCS_TOKEN_PATH = "/snowflake/session/token"


class Result:
    """Outcome of one question."""

    def __init__(self, question: str):
        self.question = question
        self.text: str = ""
        self.sql: str | None = None
        self.value: float | None = None
        self.source: str = "pending"   # analyst | analyst_sql | fallback | error
        self.transport: str | None = None
        self.error: str | None = None
        self.latency_ms: int = 0
        self.raw_head: str = ""

    @property
    def ok(self) -> bool:
        return self.value is not None

    @property
    def used_analyst(self) -> bool:
        return self.source in ("analyst", "analyst_sql")


def _decode(raw) -> dict:
    """Normalise the SiS transport's return value.

    Depending on runtime version this is a JSON string, a dict with the body
    under 'content'/'body', or bytes.
    """
    if raw is None:
        return {}
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"_unparsed": raw}
    if isinstance(raw, dict):
        for key in ("content", "body"):
            if key in raw:
                body = raw[key]
                if isinstance(body, str):
                    try:
                        return json.loads(body)
                    except json.JSONDecodeError:
                        return {"_unparsed": body}
                if isinstance(body, dict):
                    return body
        return raw
    return {"_unparsed": str(raw)}


def _extract(payload: dict) -> tuple[str, str | None]:
    """Pull prose and SQL out of an Analyst message payload."""
    texts, sql = [], None
    message = payload.get("message") or {}
    content = message.get("content") or payload.get("content") or []
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            kind = item.get("type")
            if kind == "text" and item.get("text"):
                texts.append(item["text"].strip())
            elif kind == "sql" and item.get("statement"):
                sql = item["statement"]
    return " ".join(texts).strip(), sql


def _transport_snowflake_module(body: dict, timeout_ms: int):
    """Transport A: in-sandbox request helper.

    Available on warehouse runtimes, which inherit ``_snowflake`` from the
    stored-procedure sandbox. NOT available on container runtimes - Snowflake's
    migration guide is explicit that container runtimes don't get this module -
    so this transport is attempted and allowed to fail.
    """
    import _snowflake

    return _snowflake.send_snow_api_request(
        "POST", ANALYST_PATH, {}, {}, body, {}, timeout_ms
    )


def _transport_spcs_oauth(body: dict, timeout_ms: int):
    """Transport B: SPCS-issued OAuth token against the internal API host.

    Container-runtime apps run as Snowpark Container Services workloads, which
    are given a short-lived OAuth token on disk and the API host in the
    environment. This reaches the same REST endpoint without any External
    Access Integration, because the host is internal to Snowflake.

    This is also why the local ``requests`` path in agents/agent_router.py
    fails while this one works: there the bearer token is a session token being
    presented as if it were OAuth.
    """
    import os

    import requests

    with open(SPCS_TOKEN_PATH, encoding="utf-8") as fh:
        token = fh.read().strip()

    host = os.getenv("SNOWFLAKE_HOST")
    if not host:
        raise RuntimeError("SNOWFLAKE_HOST not set")

    resp = requests.post(
        f"https://{host}{ANALYST_PATH}",
        json=body,
        headers={
            "Authorization": f'Bearer "{token}"',
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Snowflake-Authorization-Token-Type": "OAUTH",
        },
        timeout=timeout_ms / 1000,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:240]}")
    return resp.text


def call_analyst(question: str, timeout_ms: int = 55000) -> tuple[dict, str, str]:
    """Try each transport in turn. Returns (payload, raw_head, transport_name).

    Raises only if every transport fails, in which case ask() falls back to the
    semantic view so a governed number is still produced.
    """
    body = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": question}]}
        ],
        "semantic_view": D.SEMANTIC_VIEW,
    }

    errors = []
    for name, fn in (
        ("_snowflake", _transport_snowflake_module),
        ("spcs_oauth", _transport_spcs_oauth),
    ):
        try:
            raw = fn(body, timeout_ms)
            payload = _decode(raw)
            if payload and not payload.get("_unparsed"):
                return payload, str(raw)[:600], name
            errors.append(f"{name}: unparsable response")
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    raise RuntimeError(" | ".join(errors))


def ask(question: str, metric_key: str) -> Result:
    """Answer ``question`` for ``metric_key``, guaranteeing a governed value.

    Order of preference:
      1. Analyst returns SQL -> run it, use its scalar result.
      2. Analyst returns prose only -> keep the prose, take the value from the
         semantic view.
      3. No transport works -> semantic view only, clearly labelled.
    """
    spec = D.METRICS[metric_key]
    r = Result(question)
    started = time.time()

    try:
        payload, head, transport = call_analyst(question)
        r.raw_head = head
        r.transport = transport
        r.text, r.sql = _extract(payload)

        if not r.text and not r.sql:
            msg = payload.get("message") or payload.get("error") or payload
            raise RuntimeError(f"no usable content: {str(msg)[:220]}")

        if r.sql:
            try:
                val = D.scalar(r.sql)
                if val is not None:
                    r.value = float(val)
                    r.source = "analyst_sql"
            except Exception:
                pass  # fall through to the semantic-view value

        if r.value is None:
            r.value = D.governed_value(spec["result_col"])
            r.source = "analyst" if r.text else "fallback"

    except Exception as exc:
        r.error = str(exc)
        r.value = D.governed_value(spec["result_col"])
        r.source = "fallback" if r.value is not None else "error"
        if not r.sql:
            r.sql = D.governed_sql(spec["metric"])

    r.latency_ms = int((time.time() - started) * 1000)
    return r


# ---------------------------------------------------------------------------
# Question routing
# ---------------------------------------------------------------------------
# Routing uses the *live* synonym lists from DESCRIBE SEMANTIC VIEW, so the
# phrasings the app understands are exactly those the semantic view declares -
# there is no second, drifting copy of the vocabulary in the UI.

_STOP = {"what", "whats", "what's", "is", "our", "the", "a", "an", "of", "we",
         "are", "how", "much", "many", "do", "does", "per", "in", "on", "at",
         "for", "to", "and", "by", "rate", "this", "that", "it", "s"}


def _tokens(text: str) -> set[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {t for t in cleaned.split() if t and t not in _STOP}


@st.cache_data(ttl=D.TTL, show_spinner=False)
def _vocab() -> dict[str, set[str]]:
    """Build {metric_key: vocabulary} from live synonyms plus the label."""
    vocab: dict[str, set[str]] = {}
    for key, spec in D.METRICS.items():
        terms = set(_tokens(spec["label"]))
        meta = D.metric_meta(spec["metric_name"])
        syns = meta.get("synonyms")
        if isinstance(syns, str):
            try:
                syns = json.loads(syns)
            except json.JSONDecodeError:
                syns = []
        for s in syns or []:
            terms |= _tokens(str(s))
        terms |= _tokens(spec["metric_name"].replace("_", " "))
        vocab[key] = terms
    return vocab


def route(question: str, default: str = "otd") -> tuple[str, int]:
    """Map a free-text question to a metric. Returns (metric_key, score)."""
    q = _tokens(question)
    if not q:
        return default, 0
    best, best_score = default, 0
    for key, terms in _vocab().items():
        score = len(q & terms)
        if score > best_score:
            best, best_score = key, score
    return best, best_score
