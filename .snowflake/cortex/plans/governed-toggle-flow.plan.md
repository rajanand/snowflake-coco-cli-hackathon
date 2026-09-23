## Goal

Rebuild the core interaction around **one toggle**. The screen shows a single supply-chain metric and flips between two modes:

- **Ungoverned** (default landing — "the problem"): each department answers from its own system. Operations (ERP), Logistics (TMS), Procurement (Supplier Portal) each show a **different number**, a **different definition**, and the **actual SQL they ran**. A spread callout makes the disagreement concrete.
- **Governed** ("the fix"): one request goes to the **semantic view** (not the individual tables) via Cortex Analyst, returning a single governed number with live provenance.

The toggle is the star control, always visible. Flipping it re-answers the *same* question two different ways on the *same* chart axis, so the governed marker resolving the spread is the payoff moment.

## What stays (reused as-is)

- `lib/data.py` — the `METRICS` registry already carries per-team `definition`, `flaw`, and `sql` for every metric, plus live `governed_value`, `semantic_meta`, `drilldown`, `iot_sample`. No changes needed.
- `lib/analyst.py` — 3-tier transport chain + guaranteed fallback. Reused unchanged.
- `lib/viz.py` — `answer_number_line` already gates layers by `beat`. Map **ungoverned → beat 2** (band + hollow legacy points + spread callout + IoT interval, no governed marker) and **governed → beat 3** (adds the governed marker). No viz change required.
- `lib/theme.py`, `lib/tokens.py` — design system, fonts, `.ge-badge.governed/.ungoverned` styles already exist. Reused.

## What changes

### 1. `streamlit_app.py` — state + main flow
- Drop the `beat` state machine (`MAX_BEAT`, `_reveal_control`, progress dots, `on_question`'s beat-arming).
- New state: `mode` (`"ungoverned"` default), `metric` (`"otd"` default), `question`, `result`.
- `main()` becomes: masthead → **metric selector** (pills) → **mode toggle** (segmented control, the dominant control) → render `ungoverned_panel` or `governed_panel` → footer.
- Resolve the governed value eagerly via `D.governed_value` (always safe); fire Cortex Analyst only when in Governed mode, keyed/cached by `(metric, question)`, wrapped in `st.status`/spinner. Fallback guarantees a number.

### 2. `lib/components.py` — new panels
- `mode_toggle(c, caps)` — a large centered `st.segmented_control` (fallback: two buttons) with **⚠ Ungoverned** and **🛡 Governed** options, styled via existing badge/segmented CSS. Returns the mode.
- `metric_selector(c, caps)` — pills for On-Time Delivery / Days of Inventory / Landed Cost / Fill Rate (fallback: buttons). Returns metric key.
- `ungoverned_panel(c, spec, legacy, sample)`:
  - Headline: "Same question. N systems. N different answers."
  - Number line chart at beat 2 (spread visible, no governed marker).
  - One column per department: team + system, their number (recessive/warn weight), their definition, the flaw, and an **`st.expander("The SQL {team} ran")` with `st.code(sql, "sql")`** — this is the "definitions and SQL differ" point the user asked for, shown literally.
  - A spread callout card + a nudge: "→ Flip to Governed to resolve this against the semantic view."
- `governed_panel(c, spec, result, governed, legacy, sample)`:
  - Reuse `answer_block` (hero number, metric expression, Analyst prose + SQL, transport/latency path) and `receipt` (live provenance from DESCRIBE).
  - Number line chart at beat 3 (governed marker + IoT interval resolves the spread).
  - Emphasis line: "One query. The semantic view — not the source tables."
  - Optional plain-English ask box (governed mode only) that routes via `A.route` and re-runs Analyst, contrasting NL governance against Ungoverned's rigid per-team SQL.
  - Depth (drilldown / ontology / zero-identifiers) behind tabs or an expander — no longer gated behind a reveal.
- Keep `masthead`; **remove** `how_it_works`, `question_bar` (persona-only), `stage`, and beat-specific rendering.

### 3. `lib/copy.py` — two-mode narrative
- New `SUBTITLE` framing the toggle ("Flip between how each team answers today and how the governed semantic view answers.").
- `UNGOVERNED_LEAD`, `GOVERNED_LEAD`, spread/nudge strings, governed emphasis line.
- Drop `HOW_IT_WORKS`, `BEAT_CTA`, `NEXT_HINT`, `DEPTH_LOCKED_HINT`, `EMPTY_HINT`, `BEAT_LABELS` (or trim to what remains referenced).

## Deploy + verify

- CLI (`snow streamlit deploy`) is blocked by the interactive-OAuth issue, so redeploy via the working SQL pipeline: `WRITE_FILE_TO_STAGE` proc → `@DEPLOY_TRANSIT` → `COPY FILES` into the Streamlit object's `versions/live/`. Only 3 files change: `streamlit_app.py`, `lib/components.py`, `lib/copy.py`.
- If the container serves stale modules, force a restart so the new `lib/*.py` takes effect.
- Smoke test: (a) Ungoverned shows N department cards each with distinct number + distinct SQL in the expander; (b) spread callout renders; (c) toggle to Governed shows the hero number, Analyst prose/SQL or semantic-view fallback, transport label, and the governed marker on the chart; (d) each of the 4 metrics behaves; (e) NL ask in governed mode re-routes and re-answers.

## Notes / defaults I chose (tell me to change any)
- **Default mode = Ungoverned** so the problem lands first (per "first I should be able to show the problem").
- Kept a metric selector so the toggle has a subject; the same-question-different-words persona idea is folded into the optional governed-mode ask box rather than a separate strip.
- One metric on screen at a time; the toggle governs the whole screen.
