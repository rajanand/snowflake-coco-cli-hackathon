"""Governed Answer Engine — Streamlit in Snowflake.

A live demonstration that a governed semantic layer is what makes
conversational analytics trustworthy. Ask as a department; its siloed agent
answers from its own system. Flip to Governed and the same question, from any
department, routes through Cortex Analyst against one semantic view instead -
and every ask converges on one number. Every ask, in either mode, appends a
step-by-step trace to the sidebar so the divergence and the convergence are
both visible, not just claimed.

Structure
---------
    streamlit_app.py    this file: state, the ask/trace loop, layout
    lib/tokens.py        colour, type and spacing tokens (dual theme)
    lib/theme.py         CSS/webfont injection, icons, capability detection
    lib/copy.py          all narrative text
    lib/data.py          cached queries, metric registry, live semantic metadata
    lib/analyst.py       Cortex Analyst client (governed) + siloed agent (ungoverned)
    lib/viz.py           Altair specs, including the answer number line
    lib/components.py    rendering: toggle, persona chips, panels, trace sidebar

Runtime note
------------
Deployed as a FROM-based object on a container runtime, which is what permits
the module layout above and modern Streamlit APIs. Optional APIs are still
feature-detected in lib/theme.capabilities() so the app degrades rather than
raising if it is ever hosted on a warehouse runtime.

All data is synthetic.
"""

from __future__ import annotations

import json

import streamlit as st

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

from lib import analyst as A          # noqa: E402
from lib import components as UI      # noqa: E402
from lib import copy as C             # noqa: E402
from lib import data as D             # noqa: E402
from lib import theme as TH           # noqa: E402


# ---------------------------------------------------------------------------
# Runtime fact recording
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _record_runtime(caps: dict) -> str:
    """Persist detected runtime facts once per container."""
    try:
        payload = json.dumps({"app": "governed_answer_engine", **caps}).replace("'", "''")
        D.session().sql(f"""
            CREATE TABLE IF NOT EXISTS {D.DB}.SEMANTIC_MODELS.RUNTIME_PROBE (
                probed_at TIMESTAMP_LTZ, facts VARIANT
            )
        """).collect()
        D.session().sql(f"""
            INSERT INTO {D.DB}.SEMANTIC_MODELS.RUNTIME_PROBE (probed_at, facts)
            SELECT CURRENT_TIMESTAMP(), PARSE_JSON('{payload}')
        """).collect()
        return "recorded"
    except Exception as exc:
        return f"skipped: {exc}"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def init_state() -> None:
    st.session_state.setdefault("theme", "dark")
    st.session_state.setdefault("mode", "ungoverned")
    st.session_state.setdefault("metric", "otd")
    st.session_state.setdefault("trace", [])       # append-only, newest first
    st.session_state.setdefault("trace_seq", 0)
    st.session_state.setdefault("revealed", {})     # metric_key -> set(team)


def latest_entry(trace: list[dict], mode: str, metric_key: str) -> dict | None:
    for e in trace:
        if e["mode"] == mode and e["metric_key"] == metric_key:
            return e
    return None


# ---------------------------------------------------------------------------
# The ask -> trace loop
# ---------------------------------------------------------------------------

def on_ask(mode: str, metric_key: str, spec: dict, question: str,
          team_label: str, system_label: str, legacy_entry: dict | None) -> None:
    """Resolve one ask and append its trace to the sidebar log.

    Ungoverned: a real Cortex Complete call rephrases the question scoped to
    one department's system, then that system's fixed canned SQL runs.
    Governed: the question routes through the existing Cortex Analyst
    transport chain against the semantic view, unchanged from before.
    """
    precision = 3 if spec["fmt"] == "pct" else (2 if spec["fmt"] == "usd" else 1)

    if mode == "ungoverned":
        if legacy_entry is None:
            return
        if hasattr(st, "status"):
            with st.status(f"Asking {system_label}…", expanded=False) as s:
                st.write(f"{team_label} agent — scoped to {system_label} only")
                result = A.siloed_ask(question, legacy_entry)
                s.update(label=f"{system_label} answered", state="complete")
        else:
            with st.spinner(f"Asking {system_label}…"):
                result = A.siloed_ask(question, legacy_entry)

        st.session_state["revealed"].setdefault(metric_key, set()).add(team_label)

        shown = D.fmt(result.value, spec["fmt"], precision)
        steps = [
            {"label": C.TRACE_STEP_UNDERSTAND, "detail": result.text, "kind": "text"},
            {"label": C.TRACE_STEP_SCOPE_UNGOVERNED.format(system=system_label),
             "detail": C.SCOPE_NOTE_UNGOVERNED.format(system=system_label), "kind": "text"},
            {"label": C.TRACE_STEP_SQL_UNGOVERNED.format(system=system_label),
             "detail": result.sql, "kind": "sql"},
            {"label": C.TRACE_STEP_ANSWER, "detail": shown, "kind": "text"},
        ]
    else:
        if hasattr(st, "status"):
            with st.status(f"Routing “{question}” through the semantic view…", expanded=False) as s:
                result = A.ask(question, metric_key)
                s.update(label="Resolved via the semantic view", state="complete")
        else:
            with st.spinner("Routing through the semantic view…"):
                result = A.ask(question, metric_key)

        shown = D.fmt(result.value, spec["fmt"], precision)
        steps = [
            {"label": C.TRACE_STEP_UNDERSTAND, "detail": result.text or "—", "kind": "text"},
            {"label": C.TRACE_STEP_SCOPE_GOVERNED, "detail": C.SCOPE_NOTE_GOVERNED, "kind": "text"},
            {"label": C.TRACE_STEP_SQL_GOVERNED,
             "detail": result.sql or D.governed_sql(spec["metric"]), "kind": "sql"},
            {"label": C.TRACE_STEP_ANSWER, "detail": shown, "kind": "text"},
        ]

    entry = {
        "mode": mode,
        "metric_key": metric_key,
        "metric_label": spec["label"],
        "team": team_label,
        "system": system_label,
        "question": question,
        "question_echo": result.text or "",
        "steps": steps,
        "value": result.value,
        "shown": shown,
        "source": result.source,
        "latency_ms": result.latency_ms,
        "result": result,
    }
    st.session_state["trace_seq"] += 1
    entry["id"] = st.session_state["trace_seq"]
    st.session_state["trace"].insert(0, entry)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    init_state()

    caps = TH.capabilities()
    c = TH.inject(st.session_state["theme"])
    _record_runtime(caps)

    with st.sidebar:
        UI.trace_sidebar(c, st.session_state["trace"])

    UI.masthead(c)
    UI.gap(18)

    metric_key = UI.metric_selector(c, caps)
    st.session_state["metric"] = metric_key
    spec = D.METRICS[metric_key]

    UI.gap(10)
    mode = UI.mode_toggle(c, caps)
    st.session_state["mode"] = mode

    UI.gap(16)
    clicked = UI.persona_chips(c, spec, mode)

    typed_question = None
    if mode == "governed":
        UI.gap(6)
        typed_question = UI.governed_ask_box(caps)

    if clicked is not None:
        on_ask(mode, metric_key, spec, clicked["ask"], clicked["team"], clicked["system"], clicked)
        TH.rerun()
    elif typed_question:
        routed_metric, _ = A.route(typed_question, default=metric_key)
        if routed_metric != metric_key:
            st.session_state["metric"] = routed_metric
        on_ask("governed", routed_metric, D.METRICS[routed_metric],
               typed_question, "You", "Cortex Analyst", None)
        TH.rerun()

    UI.gap(20)

    all_legacy = D.legacy_answers(metric_key)
    revealed_teams = st.session_state["revealed"].get(metric_key, set())
    revealed = [l for l in all_legacy if l["team"] in revealed_teams]
    sample = D.iot_sample() if metric_key == "otd" else None

    if mode == "ungoverned":
        entry = latest_entry(st.session_state["trace"], "ungoverned", metric_key)
    else:
        gov_entries = [e for e in st.session_state["trace"]
                      if e["mode"] == "governed" and e["metric_key"] == metric_key]
        entry = gov_entries[0] if gov_entries else None

    if entry is not None:
        UI.question_banner(entry, mode)
        UI.gap(20)

    if mode == "ungoverned":
        UI.ungoverned_panel(c, spec, entry, revealed, sample)
    else:
        governed_marker = entry["value"] if entry else None
        UI.governed_panel(c, spec, entry, revealed, sample, governed_marker, caps)

    _footer(caps)


def _footer(caps: dict) -> None:
    UI.gap(30)
    UI.h(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                border-top:1px solid var(--ge-hairline);padding-top:14px;gap:16px">
      <span class="ge-small">{C.SYNTHETIC_NOTE}</span>
      <span class="ge-mono" style="font-size:10.5px;color:var(--ge-muted)">
        {D.SEMANTIC_VIEW} · Streamlit {caps.get('version', '?')}
      </span>
    </div>
    """)


main()
