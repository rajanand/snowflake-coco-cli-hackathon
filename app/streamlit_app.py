"""Governed Answer Engine — Streamlit in Snowflake.

A live demonstration that a governed semantic layer is what makes
conversational analytics trustworthy. Ask a supply-chain question in plain
English; the app shows what each source system would have answered, how far
apart those answers are, and what the single governed metric returns — with the
provenance of that governed number quoted from the deployed object itself.

Structure
---------
    streamlit_app.py    this file: state, beat sequencing, layout
    lib/tokens.py       colour, type and spacing tokens (dual theme)
    lib/theme.py        CSS/webfont injection, icons, capability detection
    lib/copy.py         all narrative text
    lib/data.py         cached queries, metric registry, live semantic metadata
    lib/analyst.py      Cortex Analyst client + guaranteed fallback
    lib/viz.py          Altair specs, including the answer number line
    lib/components.py   rendering

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

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

from lib import analyst as A          # noqa: E402
from lib import components as UI      # noqa: E402
from lib import copy as C             # noqa: E402
from lib import data as D             # noqa: E402
from lib import theme as TH           # noqa: E402

MAX_BEAT = 3


# ---------------------------------------------------------------------------
# Runtime fact recording
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _record_runtime(caps: dict) -> str:
    """Persist detected runtime facts once per container.

    Project memory recorded warehouse-runtime limitations for the older app
    object; the docs describe a very different container-runtime ceiling. This
    writes what is actually true of *this* deployment so the question is
    settled by evidence rather than by either source being taken on trust.
    """
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
    st.session_state.setdefault("beat", 0)
    st.session_state.setdefault("metric", "otd")
    st.session_state.setdefault("question", None)
    st.session_state.setdefault("result", None)


def on_question(question: str) -> None:
    """Route the question, resolve the governed answer, arm the first beat.

    The Analyst call happens here rather than at the reveal so that the reveal
    is instantaneous on stage. Latency is absorbed while the presenter is still
    talking about the claims.
    """
    metric_key, _ = A.route(question, default=st.session_state["metric"])
    st.session_state["metric"] = metric_key
    st.session_state["question"] = question

    label = D.METRICS[metric_key]["label"]
    if hasattr(st, "status"):
        with st.status(f"Resolving “{question}”", expanded=False) as s:
            st.write(f"Routed to **{label}** via semantic-view synonyms")
            st.write("Querying each source system as that team would have")
            D.legacy_answers(metric_key)
            st.write("Asking Cortex Analyst against the governed semantic view")
            st.session_state["result"] = A.ask(question, metric_key)
            s.update(label=f"Resolved · {label}", state="complete")
    else:
        with st.spinner(f"Resolving “{question}”"):
            D.legacy_answers(metric_key)
            st.session_state["result"] = A.ask(question, metric_key)

    st.session_state["beat"] = 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    init_state()

    caps = TH.capabilities()
    c = TH.inject(st.session_state["theme"])
    _record_runtime(caps)

    UI.masthead(c)
    UI.gap(18)

    beat = st.session_state["beat"]

    # Before the first question, orient the viewer instead of showing an empty
    # chart. This is what makes the interaction self-explanatory.
    if beat == 0:
        UI.how_it_works(c)
        UI.gap(16)
        UI.h(
            f"<div class='ge-card' style='border-left:2px solid var(--ge-accent)'>"
            f"<div class='ge-body' style='color:var(--ge-text)'>{C.EMPTY_HINT}</div></div>"
        )
        UI.gap(12)

    asked = UI.question_bar(c, caps)
    if asked:
        on_question(asked)
        beat = st.session_state["beat"]

    # Nothing more to show until a question has been asked.
    if beat == 0:
        _footer(caps)
        return

    UI.gap(16)

    metric_key = st.session_state["metric"]
    spec = D.METRICS[metric_key]

    # Data for the stage. Legacy values are computed, never asserted.
    try:
        legacy = D.legacy_answers(metric_key)
    except Exception as exc:
        legacy = []
        st.warning(f"Could not compute legacy answers: {exc}")

    sample = D.iot_sample() if metric_key == "otd" else None
    result = st.session_state.get("result")
    governed = result.value if result else D.governed_value(spec["result_col"])

    UI.stage(c, spec, legacy, governed, sample, beat, st.session_state["question"])

    # --- reveal control: the single, obvious way forward --------------------
    UI.gap(12)
    _reveal_control(beat)

    # --- claims -------------------------------------------------------------
    if legacy:
        UI.gap(20)
        UI.claims(c, legacy, spec)
        if spec.get("note"):
            UI.gap(8)
            UI.h(f"<div class='ge-card ge-card-quiet' style='border-style:dashed'>"
                 f"<div class='ge-small'>{spec['note']}</div></div>")

    # --- governed answer + provenance ---------------------------------------
    if beat >= MAX_BEAT and result:
        UI.h("<hr class='ge-rule'/>")
        UI.answer_block(c, spec, result)
        UI.gap(20)
        UI.receipt(c, spec, result)

    # --- depth: unlocks only after the governed answer is revealed ----------
    if beat >= MAX_BEAT:
        UI.gap(28)
        UI.h("<hr class='ge-rule'/>")
        UI.h(TH.eyebrow("Underneath the answer", "layers"))
        UI.gap(6)

        titles = ["Metrics board", "Dimension drilldown", "Ontology", "Zero identifiers"]
        panels = [UI.metrics_board, UI.drilldown_panel, UI.ontology_panel, UI.zero_id_panel]

        if caps.get("tabs"):
            for tab, panel in zip(st.tabs(titles), panels):
                with tab:
                    UI.gap(8)
                    panel(c)
        else:
            choice = st.radio("Section", titles, horizontal=True,
                              label_visibility="collapsed", key="drawer")
            UI.gap(8)
            panels[titles.index(choice)](c)
    else:
        UI.gap(16)
        UI.h(f"<div class='ge-small' style='text-align:center;color:var(--ge-muted)'>"
             f"{C.DEPTH_LOCKED_HINT}</div>")

    _footer(caps)


def _reveal_control(beat: int) -> None:
    """The one control that drives the demo. Deliberately prominent and centred,
    with a step indicator and a caption saying what the next click does."""
    # Progress dots + step label.
    dots = "".join(
        f"<span style='display:inline-block;width:30px;height:4px;border-radius:2px;"
        f"margin:0 4px;background:"
        f"{'var(--ge-accent)' if i <= beat else 'var(--ge-hairline)'}'></span>"
        for i in range(1, MAX_BEAT + 1)
    )
    UI.h(
        f"<div style='text-align:center'>"
        f"<div class='ge-eyebrow' style='margin-bottom:8px'>Step {min(beat, MAX_BEAT)} of {MAX_BEAT}</div>"
        f"<div>{dots}</div></div>"
    )
    UI.gap(10)

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        if beat < MAX_BEAT:
            if st.button(C.BEAT_CTA[beat], type="primary", use_container_width=True):
                st.session_state["beat"] = beat + 1
                TH.rerun()
            hint = C.NEXT_HINT.get(beat)
            if hint:
                UI.h(f"<div class='ge-small' style='text-align:center;margin-top:8px;"
                     f"color:var(--ge-muted)'>{hint}</div>")
        else:
            if st.button("↺  Ask another question", use_container_width=True):
                st.session_state.update(beat=0, question=None, result=None)
                st.session_state.pop("_last_persona", None)
                TH.rerun()


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
