"""Rendering components.

Layout only - every string comes from ``copy.py``, every colour from
``tokens.py``, every number from ``data.py``. HTML is emitted through ``h()``
which strips indentation, because leading whitespace makes Streamlit's markdown
parser treat a block as code and render the tags literally.
"""

from __future__ import annotations

import textwrap

import pandas as pd
import streamlit as st

from lib import copy as C
from lib import data as D
from lib import theme as TH
from lib import viz as V


def h(markup: str) -> None:
    """Emit HTML with indentation stripped."""
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)


def gap(px: int = 8) -> None:
    st.markdown(f"<div style='height:{px}px'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Masthead
# ---------------------------------------------------------------------------

def masthead(c: dict) -> None:
    """Title block."""
    h(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
      <span style="color:var(--ge-accent)">{TH.icon('split', 18)}</span>
      <span class="ge-eyebrow" style="margin:0">{C.PRODUCT}</span>
    </div>
    <div class="ge-display">{C.TAGLINE}</div>
    """)
    h(f"<div class='ge-body' style='max-width:70ch;margin-top:8px'>{C.SUBTITLE}</div>")


# ---------------------------------------------------------------------------
# How it works — first-run orientation
# ---------------------------------------------------------------------------

def how_it_works(c: dict) -> None:
    """A numbered three-step strip so the interaction is obvious before use."""
    cols = st.columns(3, gap="small")
    for i, (col, (title, desc)) in enumerate(zip(cols, C.HOW_IT_WORKS), start=1):
        with col:
            h(f"""
            <div class="ge-card" style="height:100%">
              <div style="display:flex;align-items:center;gap:9px;margin-bottom:8px">
                <span style="display:inline-flex;align-items:center;justify-content:center;
                             width:22px;height:22px;border-radius:999px;
                             background:var(--ge-accent-wash);border:1px solid var(--ge-accent);
                             color:var(--ge-accent);font-size:11px;font-weight:600">{i}</span>
                <span class="ge-title" style="font-size:15px">{title}</span>
              </div>
              <div class="ge-small" style="color:var(--ge-text-dim)">{desc}</div>
            </div>
            """)


# ---------------------------------------------------------------------------
# Question bar
# ---------------------------------------------------------------------------

def question_bar(c: dict, caps: dict) -> str | None:
    """Persona chips plus a free-text box. Returns a newly asked question."""
    h(TH.eyebrow("Ask as a persona — same metric, different words", "target"))

    asked: str | None = None
    names = list(C.PERSONAS.keys())

    if caps.get("pills"):
        # Chips read as a toolbar rather than a form control.
        picked = st.pills("Persona", names, selection_mode="single",
                          key="persona", label_visibility="collapsed")
        if picked and st.session_state.get("_last_persona") != picked:
            st.session_state["_last_persona"] = picked
            asked = C.PERSONAS[picked]
    else:
        cols = st.columns(len(names))
        for col, name in zip(cols, names):
            with col:
                if st.button(name, key=f"persona_{name}", use_container_width=True):
                    asked = C.PERSONAS[name]

    gap(6)

    if caps.get("chat_input"):
        typed = st.chat_input("Ask anything about delivery, inventory, cost or fill rate")
    else:
        typed = None
        with st.form("q_form", clear_on_submit=False):
            box = st.text_input("Question", placeholder="Ask a question",
                                label_visibility="collapsed")
            if st.form_submit_button("Ask", type="primary") and box.strip():
                typed = box.strip()

    return typed or asked


# ---------------------------------------------------------------------------
# Stage: the number line
# ---------------------------------------------------------------------------

def stage(c: dict, spec: dict, legacy: list[dict], governed: float | None,
          sample: dict | None, beat: int, question: str | None) -> None:
    precision = 1 if spec["fmt"] != "usd" else 2

    head_l, head_r = st.columns([4, 2], vertical_alignment="bottom")
    with head_l:
        h(TH.eyebrow(f"{spec['label']} · {C.BEAT_LABELS.get(beat, '')}", "target"))
        if question:
            h(f"<div class='ge-title'>“{question}”</div>")
        else:
            h(f"<div class='ge-sub'>{C.BEAT_LABELS[0]}</div>")
    with head_r:
        badge = ("<span class='ge-badge governed'>"
                 f"{TH.icon('shield', 12)} governed</span>") if beat >= 3 else (
                 "<span class='ge-badge ungoverned'>"
                 f"{TH.icon('alert', 12)} ungoverned</span>")
        h(f"<div style='text-align:right'>{badge}</div>")

    gap(4)
    chart = V.answer_number_line(
        c, legacy, governed if beat >= 3 else None,
        spec["domain"], spec["unit"], sample, beat, precision,
    )
    st.altair_chart(chart, use_container_width=True)

    note = C.BEAT_NARRATIVE.get(beat)
    if note:
        h(f"<div class='ge-body' style='max-width:78ch'>{note}</div>")

    if beat >= 3 and sample and spec["key"] == "otd":
        gap(6)
        h(f"""
        <div class="ge-card" style="border-left:2px solid var(--ge-accent)">
          <div class="ge-eyebrow" style="margin-bottom:6px">The finding</div>
          <div class="ge-body" style="color:var(--ge-text)">{C.IOT_INSIGHT}</div>
        </div>
        """)


# ---------------------------------------------------------------------------
# Legacy claims
# ---------------------------------------------------------------------------

def claims(c: dict, legacy: list[dict], spec: dict) -> None:
    """One card per claimant. The flaw is the emphasised line, not the number."""
    precision = 1 if spec["fmt"] != "usd" else 2
    h(TH.eyebrow("What each system claimed", "layers"))
    gap(2)

    cols = st.columns(len(legacy))
    for col, src in zip(cols, legacy):
        with col:
            val = src.get("value")
            shown = (f"{val:.{precision}f}{spec['unit']}" if val is not None else "—")
            h(f"""
            <div class="ge-card" style="height:100%">
              <div class="ge-eyebrow" style="margin-bottom:4px">{src['team']}</div>
              <div class="ge-mono" style="font-size:11px;color:var(--ge-muted);margin-bottom:10px">{src['system']}</div>
              <div class="ge-legacy-num">{shown}</div>
              <div class="ge-small" style="margin-top:10px;color:var(--ge-text-dim)">{src['definition']}</div>
              <div style="height:1px;background:var(--ge-hairline);margin:10px 0"></div>
              <div style="display:flex;gap:6px;align-items:flex-start">
                <span style="color:var(--ge-warn);margin-top:1px">{TH.icon('alert', 12)}</span>
                <span class="ge-small" style="color:var(--ge-warn)">{src['flaw']}</span>
              </div>
            </div>
            """)


# ---------------------------------------------------------------------------
# The governed answer
# ---------------------------------------------------------------------------

def answer_block(c: dict, spec: dict, result) -> None:
    """The typeset governed number, its prose, and the SQL behind it."""
    precision = 3 if spec["fmt"] == "pct" else (2 if spec["fmt"] == "usd" else 1)
    shown = D.fmt(result.value, spec["fmt"], precision)

    if spec["fmt"] == "usd":
        num, unit = shown, ""
    elif spec["fmt"] == "pct":
        num, unit = shown.rstrip("%"), "%"
    else:
        num, unit = shown, " days"

    left, right = st.columns([2.05, 3], vertical_alignment="top")

    with left:
        h(TH.eyebrow("Governed answer", "shield"))
        h(f"""
        <div class="ge-hero-num">{num}<span class="ge-hero-unit">{unit}</span></div>
        <div class="ge-mono" style="margin-top:8px;font-size:11.5px;color:var(--ge-muted)">
          {spec['metric']}
        </div>
        """)

        # Provenance of the number itself, stated rather than implied.
        transport = f" · {result.transport}" if result.transport else ""
        if result.source == "analyst_sql":
            path = f"Cortex Analyst → generated SQL{transport}"
            tone = "var(--ge-accent)"
        elif result.source == "analyst":
            path = f"Cortex Analyst → semantic view{transport}"
            tone = "var(--ge-accent)"
        elif result.source == "fallback":
            path = "Semantic view (direct SQL)"
            tone = "var(--ge-muted)"
        else:
            path = "Unavailable"
            tone = "var(--ge-warn)"

        h(f"""
        <div style="margin-top:12px;display:flex;align-items:center;gap:6px">
          <span style="color:{tone}">{TH.icon('route', 12)}</span>
          <span class="ge-small" style="color:{tone}">{path}</span>
          <span class="ge-small" style="color:var(--ge-muted)">· {result.latency_ms} ms</span>
        </div>
        """)

    with right:
        if result.text:
            h(TH.eyebrow("What Cortex Analyst said", "search"))
            h(f"<div class='ge-body' style='color:var(--ge-text)'>{result.text}</div>")
            gap(8)
        if result.sql:
            h(TH.eyebrow("The SQL it ran", "database"))
            st.code(result.sql.strip(), language="sql")

    if result.error:
        gap(4)
        h(f"""
        <div class="ge-card" style="border-color:var(--ge-hairline)">
          <div class="ge-eyebrow" style="margin-bottom:4px">Transport note</div>
          <div class="ge-small">Analyst call did not return usable content, so the
          value was taken directly from the semantic view. The governed number is
          unaffected — only the path to it changed.</div>
          <div class="ge-mono" style="font-size:10.5px;margin-top:8px;color:var(--ge-muted)">{result.error[:300]}</div>
        </div>
        """)


# ---------------------------------------------------------------------------
# Provenance receipt
# ---------------------------------------------------------------------------

def receipt(c: dict, spec: dict, result) -> None:
    """Provenance as an artifact.

    The governance decision and the metric expression are read from
    DESCRIBE SEMANTIC VIEW, so this panel quotes the deployed object verbatim
    instead of repeating a claim typed into the app.
    """
    meta = D.metric_meta(spec["metric_name"])
    decision = meta.get("comment") or "—"
    expression = meta.get("expression") or "—"
    counts = D.entity_counts()

    rows = [
        ("metric", spec["metric"], True),
        ("semantic view", D.SEMANTIC_VIEW, False),
        ("expression", expression, False),
        ("governance decision", decision, False),
        ("entity resolution",
         "ERP ⋈ TMS ⋈ Supplier Portal ⋈ IoT → 1 canonical shipment", False),
        ("ontology",
         f"{counts['tables']} tables · {counts['relationships']} relationships · "
         f"{counts['metrics']} metrics · {counts['dimensions']} dimensions", False),
        ("least-privilege role", D.ANALYST_ROLE, False),
        ("raw identifiers exposed", "0", True),
    ]

    h(TH.eyebrow("Provenance", "shield"))
    gap(2)
    body = "".join(
        f"<div class='ge-receipt-row'>"
        f"<div class='ge-receipt-key'>{k}</div>"
        f"<div class='ge-receipt-val{' accent' if accent else ''}'>{v}</div>"
        f"</div>"
        for k, v, accent in rows
    )
    h(f"<div class='ge-receipt'>{body}</div>")


# ---------------------------------------------------------------------------
# Depth drawers
# ---------------------------------------------------------------------------

def metrics_board(c: dict) -> None:
    h(f"<div class='ge-body'>All five canonical metrics, one semantic-view query.</div>")
    gap(6)

    gov = D.governed_all()
    if not gov:
        st.info("Semantic view returned no rows.")
        return

    items = [
        ("On-Time Delivery", "ON_TIME_DELIVERY_RATE", "pct", 3),
        ("Customer Fill Rate", "CUSTOMER_FILL_RATE", "pct", 1),
        ("Supplier Fill Rate", "SUPPLIER_FILL_RATE", "pct", 3),
        ("Days of Inventory", "DAYS_OF_INVENTORY", "days", 1),
        ("Landed Cost / Unit", "LANDED_COST_PER_UNIT", "usd", 2),
    ]

    for start in (0, 3):
        chunk = items[start:start + 3]
        if not chunk:
            continue
        cols = st.columns(len(chunk))
        for col, (label, key, kind, prec) in zip(cols, chunk):
            meta_key = key
            with col:
                meta = D.semantic_meta()["metrics"].get(meta_key, {})
                h(f"""
                <div class="ge-card" style="height:100%">
                  <div class="ge-eyebrow" style="margin-bottom:8px">{label}</div>
                  <div style="font-size:30px;font-weight:600;letter-spacing:-0.022em;
                              font-variant-numeric:tabular-nums;color:var(--ge-accent)">
                    {D.fmt(gov.get(key), kind, prec)}
                  </div>
                  <div class="ge-small" style="margin-top:10px">{(meta.get('comment') or '')[:150]}</div>
                </div>
                """)
        gap(8)

    gap(2)
    st.code(D.governed_sql(
        "shipment.on_time_delivery_rate, customer_order.customer_fill_rate,\n"
        "          purchase_order.supplier_fill_rate, inventory_snapshot.days_of_inventory,\n"
        "          landed_cost.landed_cost_per_unit"
    ), language="sql")


def drilldown_panel(c: dict) -> None:
    h(f"<div class='ge-body'>{C.DRILLDOWN_NOTE}</div>")
    gap(6)

    left, right = st.columns([1, 1])
    with right:
        metric_label = st.selectbox(
            "Metric",
            [D.METRICS[k]["label"] for k in ["otd", "fill", "landed_cost", "doi"]],
            key="dd_metric",
        )

    metric_key = next(
        k for k in ["otd", "fill", "landed_cost", "doi"]
        if D.METRICS[k]["label"] == metric_label
    )
    spec = D.METRICS[metric_key]

    # Constrain the dimension list to what this metric's fact table can reach
    # through the relationship graph, rather than offering combinations that
    # would fail at query time.
    allowed = D.REACHABLE.get(metric_key, list(D.DIMENSIONS.values()))
    options = [lbl for lbl, expr in D.DIMENSIONS.items() if expr in allowed]

    with left:
        dim_label = st.selectbox("Dimension", options, key=f"dd_dim_{metric_key}")

    dimension = D.DIMENSIONS[dim_label]

    try:
        df = D.drilldown(dimension, spec["metric"])
    except Exception as exc:
        st.warning(f"Drilldown unavailable for this combination: {exc}")
        return

    if df.empty:
        st.info("No rows returned.")
        return

    dim_col, metric_col = df.columns[0], df.columns[-1]
    st.altair_chart(
        V.drilldown_bars(c, df, dim_col, metric_col, spec["unit"]),
        use_container_width=True,
    )
    with st.expander("Query"):
        st.code(
            f"SELECT * FROM SEMANTIC_VIEW(\n  {D.SEMANTIC_VIEW}\n"
            f"  DIMENSIONS {dimension}\n  METRICS {spec['metric']}\n)",
            language="sql",
        )


def ontology_panel(c: dict) -> None:
    h(f"<div class='ge-body'>{C.ONTOLOGY_NOTE}</div>")
    gap(6)

    meta = D.semantic_meta()
    counts = D.entity_counts()

    cols = st.columns(4)
    for col, (label, key) in zip(
        cols, [("Tables", "tables"), ("Relationships", "relationships"),
               ("Metrics", "metrics"), ("Dimensions", "dimensions")]
    ):
        with col:
            h(f"""
            <div class="ge-card">
              <div class="ge-eyebrow" style="margin-bottom:6px">{label}</div>
              <div style="font-size:26px;font-weight:600;letter-spacing:-0.02em;
                          color:var(--ge-text)">{counts[key]}</div>
            </div>
            """)

    gap(10)
    h(TH.eyebrow("Relationship graph", "route"))
    rels = meta["relationships"]
    if rels:
        rdf = pd.DataFrame([
            {
                "Relationship": name.lower(),
                "From": (r.get("table") or "").lower(),
                "To": (r.get("ref_table") or "").lower(),
                "Foreign key": str(r.get("foreign_key") or "").strip('[]"'),
            }
            for name, r in sorted(rels.items())
        ])
        st.dataframe(rdf, use_container_width=True, hide_index=True)

    gap(8)
    h(TH.eyebrow("Metrics and their governance decisions", "shield"))
    mets = meta["metrics"]
    if mets:
        mdf = pd.DataFrame([
            {
                "Metric": f"{(m.get('parent') or '').lower()}.{name.lower()}",
                "Synonyms": str(m.get("synonyms") or "").strip('[]').replace('"', ''),
                "Governance decision": m.get("comment") or "",
            }
            for name, m in sorted(mets.items())
        ])
        st.dataframe(mdf, use_container_width=True, hide_index=True)


def zero_id_panel(c: dict) -> None:
    h(f"<div class='ge-body'>{C.ZERO_ID_NOTE}</div>")
    gap(6)

    try:
        df = D.crosswalk_sample()
    except Exception as exc:
        st.warning(f"Crosswalk unavailable: {exc}")
        return

    h(TH.eyebrow("Silver crosswalk — source identifiers resolved", "layers"))
    st.dataframe(df, use_container_width=True, hide_index=True)

    gap(8)
    left, right = st.columns(2)
    with left:
        h(f"""
        <div class="ge-card">
          <div class="ge-eyebrow" style="margin-bottom:8px">Present in Silver</div>
          <div class="ge-mono" style="font-size:11.5px;line-height:2">
            erp_order_number<br/>pro_number<br/>asn_number<br/>device_tag
          </div>
          <div class="ge-small" style="margin-top:10px">
            Retained for lineage and audit, never surfaced to consumers.
          </div>
        </div>
        """)
    with right:
        h(f"""
        <div class="ge-card" style="border-left:2px solid var(--ge-accent)">
          <div class="ge-eyebrow" style="margin-bottom:8px">Exposed by the semantic view</div>
          <div class="ge-mono" style="font-size:11.5px;line-height:2;color:var(--ge-accent)">
            shipment_id<br/>supplier_key<br/>part_key<br/>plant_key
          </div>
          <div class="ge-small" style="margin-top:10px">
            Canonical keys only — zero source-system identifiers.
          </div>
        </div>
        """)
