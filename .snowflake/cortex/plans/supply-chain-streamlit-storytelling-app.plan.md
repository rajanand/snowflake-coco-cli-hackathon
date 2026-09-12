---
name: "supply-chain-streamlit-storytelling-app"
created: "2026-09-12T11:07:17.365Z"
status: pending
---

# Supply Chain Ontology — Streamlit-in-Snowflake Storytelling App (Phase 7)

## Context already confirmed in Snowflake (account `sc23256.ap-northeast-1.aws`)

- Full medallion pipeline is live: `SUPPLY_CHAIN.{SOURCE_*, BRONZE, SILVER, GOLD, SEMANTIC_MODELS, GOVERNANCE, AUTOMATION}`.
- `SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY` native Semantic View exists and is queryable.
- Real data volumes: `fact_shipment`=800, `fact_order_fulfillment`=500, `dim_supplier`=50, `agg_supplier_performance`=50, `fact_landed_cost`=800, `fact_inventory_snapshot`=20,000.
- `agents/agent_router.py` already implements `SupplyChainAgentRouter`, `CortexAnalystClient`, `SimulationAgent`, `EvidenceTraceAgent`, `DocumentQAAgent`, `PreQueryValidator`, `PostQueryEnricher` — logic will be reused/adapted, not rebuilt, inside the app.
- `streamlit_app.py` does not exist yet — this plan creates it at the repo root per the master plan's target structure (Phase 7).

This plan is the **detailed design for Phase 7** of `.snowflake/cortex/plans/supply-chain-ontology-revised.plan.md`, upgraded with advanced UI/UX + storytelling per your brief.

## Confirmed design decisions (from brainstorming)

1. **Visual style**: Hybrid — light, clean enterprise base (Snowflake blue `#29B5E8` accents on off-white) for data/analysis surfaces, with **dark "spotlight" panels** (deep navy `#0E1123`, light text, subtle glow) reserved for narrative story beats (headline hook, act transitions, root-cause reveal) — creates visual rhythm between "explaining" and "showing."
2. **Navigation**: **Guided story mode + free explore, hybrid**. Sidebar always lists all Acts (click any, any time = free explore); each Act page ends with a "Continue to next act →" button for a suggested linear path. A progress stepper (Act 0–5) shows where you are. No hard locking — nothing blocks a judge from jumping around.
   - *Alternative considered*: a single-page "scrollytelling" layout (data-journalism style, scroll-triggered reveals). Rejected for the primary build — Streamlit has no native scroll-trigger/animation-on-scroll primitive, so it would need fragile custom JS components, which is risky for a **live** demo (Section 4.5(c) requires live, not recorded). The Act-based stepper gets 90% of the narrative payoff with far less live-demo risk. Worth a stretch experiment only if time remains after P1/P2 tasks in the master plan are done.
3. **Live chat**: constrained — a bank of pre-tested, safe suggested-question chips (one-click) **plus** a free-text fallback input, both routed through the same adapter. This keeps the live demo reliable while preserving the "ask anything" wow factor for Q\&A.
4. **Live injection**: an in-app "Inject Live Shipments" control (Phase 6) that runs the dual-source insert, triggers a Dynamic Table refresh, and animates the before/after OTD% shift — turns Phase 6 into a first-class in-app story beat instead of an out-of-band script.

## App structure — "Acts" (maps onto the master plan's 4 required tabs + narrative bookends)

| Act | Working title                        | Maps to master plan   | Core content                                                                                                                                                                                                                                                   |
| --- | ------------------------------------ | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0   | **The Problem** (Cover)              | headline story opener | 3 conflicting OTD numbers side by side, one-line hook ("Three teams, three answers — which one is right?"), CTA into Act 1                                                                                                                                     |
| 1   | **Before — The Chaos**               | Tab 1                 | Per-metric selector (OTD / Fill Rate / DOI / Landed Cost), live legacy queries against `SOURCE_*`, divergence chart, failure-mode badges (data-quality bug / conceptual collision / methodology mismatch / incomplete assembly), SQL + plain-English expanders |
| 2   | **After — One Ontology, One Answer** | Tab 2                 | 3 persona columns (Planning/Procurement/Logistics), differently-worded questions → Cortex Analyst → generated SQL + number; "Run All Three" consistency banner (value delta + base\_table/measure\_name match)                                                 |
| 3   | **Zero Raw Identifiers**             | Tab 3                 | Pre-filled business-language question, generated SQL panel, preset chips, free-text override — proves semantic-view synonyms resolve vocabulary with no table/column names                                                                                     |
| 4   | **Ontology Explorer**                | Tab 4                 | Graphviz Supplier→Part→Plant→CustomerOrder→Customer diagram, entity picker → root-cause trace walk, "why this number is trustworthy" governance/RBAC panel                                                                                                     |
| 5   | **Live Ops & Ask Anything**          | Phase 6 + 8 tie-in    | Inject-shipments control with before/after animation, at-risk orders live table, constrained chat, token/cost usage footer                                                                                                                                     |

## Detailed build plan by task

### 1. App shell, theme, session (streamlit\_app.py + .streamlit/config.toml)

- `.streamlit/config.toml`: set `[theme]` base="light", primaryColor="#29B5E8", backgroundColor="#F7F9FC", secondaryBackgroundColor="#FFFFFF", textColor="#1A1F36", font="sans serif".
- `session = get_active_session()`; log/display active role — should be `SUPPLY_CHAIN_ANALYST_RO` (governance story point, surfaced in a small sidebar badge: "🔒 Connected as SUPPLY\_CHAIN\_ANALYST\_RO — read-only, semantic layer only").
- Shared design tokens (Python dict/consts): metric color map `{OTD: "#29B5E8", FillRate: "#3BB273", DOI: "#8E5AC8", LandedCost: "#E8871E"}`, entity icon map `{Supplier:"🚚", Part:"🔧", Plant:"🏭", CustomerOrder:"🧾", Customer:"👤"}`.
- Reusable render helpers: `story_panel(html)` (dark spotlight container via `st.markdown` + custom CSS class), `kpi_card(label, value, delta=None, color=...)`, `failure_badge(kind)`.
- Sidebar: story stepper — `st.sidebar.radio` or manual button list for Acts 0–5 with icons + current-position highlight; progress bar (`st.sidebar.progress(act_index/5)`); "Free Explore" is implicit (any act clickable at any time).
- `st.session_state` init: `act` (current act index), `chat_history`, `injected_demo_ran`, `last_injection_result`.

### 2. Act 0 (Cover) + Act 1 (Before/Chaos)

- Act 0: full-width dark story panel with the headline diagram (small Graphviz or styled text arrows: `Supplier —ships→ Part —delivered to→ Plant —fulfills→ CustomerOrder —placed by→ Customer`), 3 KPI cards showing ERP/TMS/Supplier-Portal OTD numbers with mismatched-red styling, one-sentence problem statement, "Start the Story →" button that sets `st.session_state.act = 1` and reruns.

- Act 1: `st.selectbox` or segmented control for the 4 metrics. For the selected metric, run the corresponding legacy query/queries live against `SOURCE_*` (reuse SQL blocks from the master plan Phase 0 section) via `session.sql(...).to_pandas()`, cached with `st.cache_data(ttl=300)`.

  - Bar chart (Plotly) showing each source system's number side by side, colored red/amber where it diverges from the Gold canonical value (fetch canonical value from the Semantic View for reference line).
  - Below the chart: one `st.expander` per source system with the raw SQL (`st.code(sql, language="sql")`) + one-line plain-English "why it diverges" + a colored `failure_badge()` (data-quality bug / conceptual collision / methodology mismatch / incomplete assembly).

### 3. Act 2 (Cross-Persona Consistency) + Act 3 (Zero Raw Identifiers)

- **Cortex Analyst adapter for native SiS**: since the app runs *inside* Snowflake (not as an external client), replace `agent_router.py`'s `requests` + bearer-token REST calls with the SiS-native pattern:
  ```python
  import _snowflake
  def call_cortex_analyst(question: str, semantic_view: str) -> dict:
      resp = _snowflake.send_snow_api_request(
          "POST", "/api/v2/cortex/analyst/message", {}, {},
          {"messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
           "semantic_view": semantic_view},
          {}, 30000,
      )
      return json.loads(resp["content"])
  ```
  Parse text/sql/confidence the same way `CortexAnalystClient._parse` already does — port that parsing function in, don't rebuild it.
- Act 2: 3 `st.columns`, one per persona (Planning/Procurement/Logistics) with their differently-worded question pre-filled (editable). "Run All Three" button fires all 3 through the adapter, displays question → generated SQL (`st.code`) → big number per column, then a consistency banner: green "✅ Identical answer, identical base table & measure" or red diff callout if any value/base\_table/measure\_name differs (reuse `_extract_sql_targets` logic).
- Act 3: single text input pre-filled with *"Are we hitting our delivery dates?"*, editable; below it, 4–5 clickable "preset chip" buttons with other safe phrasings tested in advance; result shows generated SQL with **no raw table/column names visible to the user's typed question** highlighted, plus the resolved KPI value in a large `kpi_card`.

### 4. Act 4 (Ontology Explorer)

- `st.graphviz_chart` rendering a `digraph` with the 5 core entities as styled nodes (fill colors from the design-token map, icon-prefixed labels) and directed edges matching the Semantic View `RELATIONSHIPS`.
- Below the diagram: `st.selectbox` "Pick an at-risk order to trace" (populated from a live query against `fact_order_fulfillment` filtered to late/at-risk orders) → on selection, run `EvidenceTraceAgent`-equivalent SQL (ported from `agent_router.py`, swapping `SnowflakeSession.sql` for `session.sql(...).to_pandas()`), render the trace as a vertical step list (CustomerOrder → Shipment → Supplier) with icons and a highlighted "root cause" step.
- "Why this number is trustworthy" expander: pulls the relevant metric's `COMMENT` text directly from the Semantic View (`DESCRIBE SEMANTIC VIEW` or a small lookup table) and displays it alongside the `SUPPLY_CHAIN_ANALYST_RO` role-scope badge — a compact, visible Governance & Security Guardrails proof point.

### 5. Act 5 (Live Ops)

- "🚀 Inject Live Shipments" button: on click, run the Phase 6 logic inline (insert 10 demo shipments into `SOURCE_ERP.orders` + `SOURCE_SUPPLIER_PORTAL.shipments`, `ALTER DYNAMIC TABLE ... REFRESH` on the affected Silver/Gold tables, `time.sleep` short buffer with `st.spinner`), then re-query OTD% and animate a before → after `kpi_card` delta (`st.metric` with `delta=`) plus `st.balloons()` on completion.
- At-risk orders table: live query against `AUTOMATION.at_risk_orders_snapshot` (or the live semantic-view equivalent if the Task hasn't populated it yet — graceful fallback message), `st.dataframe` with conditional row coloring by `risk_level`.
- Constrained chat: `st.chat_message`/`st.chat_input` UI; preset chips render as buttons above the chat input (each pre-fills and submits a tested question); free text goes through `PreQueryValidator`-equivalent checks (port the forbidden-term/length checks) before hitting the adapter; answer bubble shows text + confidence badge + `st.code` SQL + any supporting-evidence citations.
- Footer panel: small query against `SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY` (token usage this session/day) + a static note on warehouse sizing (`X-SMALL`, `AUTO_SUSPEND=60`) — ties directly to the master plan's System Design & Engineering token-tracking requirement.

### 6. Polish, caching, resilience

- `st.cache_data(ttl=...)` on every read-only metric/dimension query; never cache the injection action, chat calls, or at-risk snapshot (must be live).
- Wrap all Cortex Analyst/`_snowflake.send_snow_api_request` calls and `st.graphviz_chart` in try/except with a friendly in-panel fallback (e.g., if Graphviz rendering fails in a given SiS runtime, fall back to a styled text/emoji diagram) — protects the live demo from a single API hiccup derailing the whole story.
- Consistent color tokens/icons reused everywhere (Act 1 badges, Act 2 columns, Act 4 diagram, Act 5 chat) so the visual language reinforces the ontology across the whole app.

### 7. Test + deploy

- Run locally first: `streamlit run streamlit_app.py` (or the CoCo local dev flow) against the live `GC94671`/current connection, click through all 6 Acts, fire the injection button once, run 2–3 chat presets + 1 free-text question.
- Deploy as a native Streamlit-in-Snowflake object (`snow streamlit deploy` or CREATE STREAMLIT) so it's runnable directly from Snowsight for the live Grand Finale demo, and open a local browser preview during development.

## Open items to decide during build (not blocking the plan)

- Whether `agents/agent_router.py` gets refactored to share the SiS-adapted `call_cortex_analyst`/trace/simulate functions with `streamlit_app.py` (via import) or whether the app carries lightweight ported copies to avoid coupling the CLI-connector-based router to the SiS runtime. Recommendation: extract the pure-SQL sub-agent logic (`SimulationAgent`, `EvidenceTraceAgent` SQL + parsing) into a small shared module importable by both, and keep the REST-transport difference (`requests`+bearer vs `_snowflake.send_snow_api_request`) as the only divergent piece.
- Whether Act 5's "Inject Live Shipments" needs a "reset demo data" companion control so repeated live rehearsals don't accumulate injected rows indefinitely.
