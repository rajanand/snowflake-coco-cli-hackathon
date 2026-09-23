CALL SUPPLY_CHAIN.SEMANTIC_MODELS.WRITE_APP_FILE('lib/components.py', $$"""Rendering components.

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
# Metric selector + mode toggle
# ---------------------------------------------------------------------------

def metric_selector(c: dict, caps: dict) -> str:
    """Pills for the four canonical metrics. Returns the active metric key."""
    order = D.METRIC_ORDER
    labels = [D.METRICS[k]["label"] for k in order]
    current = st.session_state["metric"]
    key = f"metric_widget_{current}"

    h(TH.eyebrow("Metric", "target"))
    if caps.get("pills"):
        picked = st.pills("Metric", labels, default=D.METRICS[current]["label"],
                          selection_mode="single", key=key, label_visibility="collapsed")
    else:
        picked = st.radio("Metric", labels, index=order.index(current), horizontal=True,
                          key=key, label_visibility="collapsed")

    for k, lbl in zip(order, labels):
        if lbl == picked:
            return k
    return current


def mode_toggle(c: dict, caps: dict) -> str:
    """The dominant Ungoverned/Governed control. Returns the active mode."""
    current = st.session_state["mode"]
    key = f"mode_widget_{current}"
    options = ["Ungoverned", "Governed"]
    default_label = "Governed" if current == "governed" else "Ungoverned"

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        if caps.get("segmented_control"):
            picked = st.segmented_control("Mode", options, default=default_label,
                                          key=key, label_visibility="collapsed")
        elif caps.get("pills"):
            picked = st.pills("Mode", options, default=default_label,
                              selection_mode="single", key=key, label_visibility="collapsed")
        else:
            picked = st.radio("Mode", options, index=0 if current == "ungoverned" else 1,
                              horizontal=True, key=key, label_visibility="collapsed")

    if picked == "Governed":
        return "governed"
    if picked == "Ungoverned":
        return "ungoverned"
    return current


# ---------------------------------------------------------------------------
# Persona chips Ã¢â‚¬â€ one per legacy claimant team, dynamic per metric
# ---------------------------------------------------------------------------

def persona_chips(c: dict, spec: dict, mode: str) -> dict | None:
    """One button per department that claims this metric. Returns the clicked
    legacy entry, or None if nothing was clicked this run."""
    h(TH.eyebrow(f"Ask as a department Ã¢â‚¬â€ {spec['label']}", "target"))
    entries = spec["legacy"]
    cols = st.columns(len(entries))
    clicked = None
    for col, entry in zip(cols, entries):
        with col:
            label = f"{entry['team']} Ã‚Â· {entry['system']}"
            if st.button(label, key=f"persona_{mode}_{spec['key']}_{entry['team']}",
                        width="stretch"):
                clicked = entry
    return clicked


def governed_ask_box(caps: dict) -> str | None:
    """Optional free-text ask, governed mode only."""
    if caps.get("chat_input"):
        return st.chat_input("Or ask anything, in your own words")
    typed = None
    with st.form("gov_ask_form", clear_on_submit=True):
        box = st.text_input("Question", label_visibility="collapsed",
                            placeholder="Or ask anything, in your own words")
        if st.form_submit_button("Ask") and box.strip():
            typed = box.strip()
    return typed


# ---------------------------------------------------------------------------
# Main-stage panels
# ---------------------------------------------------------------------------

def _chart_precision(spec: dict) -> int:
    return 2 if spec["fmt"] == "usd" else 1


def ungoverned_panel(c: dict, spec: dict, entry: dict | None,
                     revealed: list[dict], sample: dict | None) -> None:
    badge = f"<span class='ge-badge ungoverned'>{TH.icon('alert', 12)} ungoverned</span>"
    h(f"""
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
      <div>{TH.eyebrow(spec['label'], 'target')}<div class="ge-display">{C.UNGOVERNED_HEADLINE}</div></div>
      <div>{badge}</div>
    </div>
    """)
    gap(6)
    h(f"<div class='ge-body' style='max-width:74ch'>{C.UNGOVERNED_LEAD}</div>")
    gap(10)

    chart = V.answer_number_line(
        c, revealed, None, spec["domain"], spec["unit"], sample,
        beat=2, fmt_precision=_chart_precision(spec),
    )
    st.altair_chart(chart, width="stretch")

    if entry is None:
        gap(8)
        h(f"""
        <div class="ge-card" style="border-left:2px solid var(--ge-warn)">
          <div class="ge-body">{C.UNGOVERNED_EMPTY_HINT}</div>
        </div>
        """)
        return

    legacy_entry = next(l for l in spec["legacy"] if l["team"] == entry["team"])
    gap(16)
    left, right = st.columns([1.4, 2])
    with left:
        h(TH.eyebrow(f"{entry['team']} Ã‚Â· {entry['system']}", "alert"))
        h(f"<div class='ge-legacy-num'>{entry['shown']}</div>")
        h(f"""
        <div class="ge-small" style="margin-top:10px;color:var(--ge-text-dim)">
          {legacy_entry['definition']}
        </div>
        <div style="height:1px;background:var(--ge-hairline);margin:10px 0"></div>
        <div style="display:flex;gap:6px;align-items:flex-start">
          <span style="color:var(--ge-warn);margin-top:1px">{TH.icon('alert', 12)}</span>
          <span class="ge-small" style="color:var(--ge-warn)">{legacy_entry['flaw']}</span>
        </div>
        """)
    with right:
        h(TH.eyebrow("What their agent said", "search"))
        h(f"<div class='ge-body'>{entry['question_echo']}</div>")
        gap(8)
        h(TH.eyebrow("Scope", "route"))
        h(f"<div class='ge-body'>{C.SCOPE_NOTE_UNGOVERNED.format(system=entry['system'])}</div>")

    gap(18)
    h(f"<div class='ge-small' style='text-align:center;color:var(--ge-muted)'>{C.UNGOVERNED_NUDGE}</div>")


def governed_panel(c: dict, spec: dict, entry: dict | None, revealed: list[dict],
                   sample: dict | None, governed_marker: float | None, caps: dict) -> None:
    badge = f"<span class='ge-badge governed'>{TH.icon('shield', 12)} governed</span>"
    h(f"""
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
      <div>{TH.eyebrow(spec['label'], 'target')}<div class="ge-display">{C.GOVERNED_HEADLINE}</div></div>
      <div>{badge}</div>
    </div>
    """)
    gap(6)
    h(f"<div class='ge-body' style='max-width:74ch'>{C.GOVERNED_LEAD}</div>")
    gap(10)

    chart = V.answer_number_line(
        c, revealed, governed_marker, spec["domain"], spec["unit"], sample,
        beat=3, fmt_precision=_chart_precision(spec),
    )
    st.altair_chart(chart, width="stretch")

    if entry is None:
        gap(8)
        h(f"""
        <div class="ge-card" style="border-left:2px solid var(--ge-accent)">
          <div class="ge-body">{C.GOVERNED_EMPTY_HINT}</div>
        </div>
        """)
        return

    gap(16)
    answer_block(c, spec, entry["result"])
    gap(20)
    receipt(c, spec, entry["result"])

    gap(16)
    h(f"<div class='ge-small' style='text-align:center;color:var(--ge-accent)'>{C.GOVERNED_EMPHASIS}</div>")

    gap(28)
    h("<hr class='ge-rule'/>")
    h(TH.eyebrow("Underneath the answer", "layers"))
    gap(6)

    titles = ["Metrics board", "Dimension drilldown", "Ontology", "Zero identifiers"]
    panels = [metrics_board, drilldown_panel, ontology_panel, zero_id_panel]
    if caps.get("tabs"):
        for tab, panel in zip(st.tabs(titles), panels):
            with tab:
                gap(8)
                panel(c)
    else:
        choice = st.radio("Section", titles, horizontal=True,
                          label_visibility="collapsed", key="depth_drawer")
        gap(8)
        panels[titles.index(choice)](c)


# ---------------------------------------------------------------------------
# Trace sidebar Ã¢â‚¬â€ "behind the scenes"
# ---------------------------------------------------------------------------

def _trace_steps(entry: dict) -> None:
    for step in entry["steps"]:
        h(f"<div class='ge-eyebrow' style='margin:8px 0 2px'>{step['label']}</div>")
        if step["kind"] == "sql":
            st.code(step["detail"], language="sql")
        else:
            h(f"<div class='ge-small' style='color:var(--ge-text-dim)'>{step['detail']}</div>")


def trace_sidebar(c: dict, trace: list[dict]) -> None:
    """Append-only behind-the-scenes log. Call inside ``with st.sidebar:``."""
    h(f"<div class='ge-eyebrow'>{TH.icon('layers', 12)} {C.TRACE_HEADER}</div>")

    if not trace:
        gap(4)
        h(f"<div class='ge-small' style='color:var(--ge-muted)'>{C.TRACE_EMPTY_HINT}</div>")
        return

    if st.button(C.CLEAR_TRACE_LABEL, width="stretch", key="clear_trace"):
        st.session_state["trace"] = []
        st.session_state["revealed"] = {}
        TH.rerun()

    gap(10)
    for i, entry in enumerate(trace):
        border = "var(--ge-accent)" if entry["mode"] == "governed" else "var(--ge-warn)"
        badge_cls = "governed" if entry["mode"] == "governed" else "ungoverned"

        header = f"""
        <div style="border-left:2px solid {border};padding-left:10px">
          <span class="ge-badge {badge_cls}">{entry['mode']}</span>
          <div class="ge-small" style="margin-top:4px;color:var(--ge-text)">
            {entry['team']} Ã‚Â· {entry['metric_label']}
          </div>
          <div class="ge-mono" style="font-size:11px;color:var(--ge-muted)">{entry['shown']}</div>
        </div>
        """

        if i == 0:
            h(header)
            gap(4)
            h(f"<div class='ge-small' style='color:var(--ge-text-dim)'>\u201c{entry['question']}\u201d</div>")
            _trace_steps(entry)
            gap(6)
            h("<hr class='ge-rule' style='margin:10px 0'/>")
        else:
            h(header)
            with st.expander("Steps", expanded=False):
                h(f"<div class='ge-small' style='margin-bottom:6px'>\u201c{entry['question']}\u201d</div>")
                _trace_steps(entry)
            gap(8)


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
        transport = f" Ã‚Â· {result.transport}" if result.transport else ""
        if result.source == "analyst_sql":
            path = f"Cortex Analyst Ã¢â€ â€™ generated SQL{transport}"
            tone = "var(--ge-accent)"
        elif result.source == "analyst":
            path = f"Cortex Analyst Ã¢â€ â€™ semantic view{transport}"
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
          <span class="ge-small" style="color:var(--ge-muted)">Ã‚Â· {result.latency_ms} ms</span>
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
          unaffected Ã¢â‚¬â€ only the path to it changed.</div>
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
    decision = meta.get("comment") or "Ã¢â‚¬â€"
    expression = meta.get("expression") or "Ã¢â‚¬â€"
    counts = D.entity_counts()

    rows = [
        ("metric", spec["metric"], True),
        ("semantic view", D.SEMANTIC_VIEW, False),
        ("expression", expression, False),
        ("governance decision", decision, False),
        ("entity resolution",
         "ERP Ã¢â€¹Ë† TMS Ã¢â€¹Ë† Supplier Portal Ã¢â€¹Ë† IoT Ã¢â€ â€™ 1 canonical shipment", False),
        ("ontology",
         f"{counts['tables']} tables Ã‚Â· {counts['relationships']} relationships Ã‚Â· "
         f"{counts['metrics']} metrics Ã‚Â· {counts['dimensions']} dimensions", False),
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
        width="stretch",
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
        st.dataframe(rdf, width="stretch", hide_index=True)

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
        st.dataframe(mdf, width="stretch", hide_index=True)


def zero_id_panel(c: dict) -> None:
    h(f"<div class='ge-body'>{C.ZERO_ID_NOTE}</div>")
    gap(6)

    try:
        df = D.crosswalk_sample()
    except Exception as exc:
        st.warning(f"Crosswalk unavailable: {exc}")
        return

    h(TH.eyebrow("Silver crosswalk Ã¢â‚¬â€ source identifiers resolved", "layers"))
    st.dataframe(df, width="stretch", hide_index=True)

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
            Canonical keys only Ã¢â‚¬â€ zero source-system identifiers.
          </div>
        </div>
        """)
$$);