# Plan: The Governed Answer Engine

A from-scratch SiS app built for a live demo you drive. Design-led, not template-led.

## Runtime correction (important)
Project memory's SiS constraints (`no st.tabs`, `no st.rerun`, "HTML gets stripped") are from the **warehouse runtime**. `snowflake.yml` uses **`SYSTEM$ST_CONTAINER_RUNTIME_PY3_11`**, which per Snowflake docs gives us:

- **Streamlit 1.50+** (any version) → `st.segmented_control`, `st.pills`, `st.fragment`, `st.metric(border=True)`, `st.write_stream`, `st.column_config`, `st.tabs`, `st.rerun`, `st.popover`, `st.html`
- **Components v2 supported**, **static file serving supported**, **cross-session caching**
- **Entrypoint in subdirectories + real module structure**

Hard limits that stay:
- **CSP blocks external scripts/stylesheets**; inline CSS is fine. **Fonts/images load from any HTTPS domain.**
- **No External Access Integration on this trial account** → **no `pyproject.toml`, zero new PyPI deps.** Build on the base image only: `streamlit`, `pandas`, `altair`, `snowflake.snowpark`.
- `st.set_page_config`'s `page_title`/`page_icon` are ignored in SiS.

**Because memory and docs conflict, task 1 is an empirical probe — we design to a verified ceiling, not an assumed one.**

## Design system

**Typography — Geist + Geist Mono** via `[[theme.fontFaces]]` (HTTPS woff2, CSP-permitted), with a system-stack fallback and a base64-embedded plan B if the CDN load fails under probe.
- Display 32/36 tight (-0.02em) · Title 20/28 · Body 14/20 · Micro 11/16 uppercase +0.08em tracking · Mono 13/20 for SQL, IDs, the trust receipt.
- The governed number renders at ~64px, tabular-nums, tight tracking. It should feel *typeset*, not `st.metric`-ed.

**Tokens (dual theme, both first-class)**

| Token | Dark | Light |
|---|---|---|
| `bg` | `#0B0E14` | `#FAFAF9` |
| `surface` | `#12161F` | `#FFFFFF` |
| `hairline` | `rgba(255,255,255,.08)` | `rgba(15,23,42,.10)` |
| `text` | `#E6EAF2` | `#0F172A` |
| `muted` | `#7C8798` | `#64748B` |
| `accent` (governed) | `#29B5E8` | `#0E7FA8` |
| `noise` (legacy) | `#4A5567` | `#94A3B8` |
| `warn` (divergence) | `#F0806C` | `#DC2626` |

Rules: one accent, used only for governed truth. Legacy answers are deliberately low-contrast — they should read as *noise*. `warn` appears only on the divergence annotation. 8px spacing scale, 10px cards / 6px controls, exactly one shadow token used sparingly, hairline borders preferred. **No emoji.** One inline SVG icon family (Lucide-style, ~10 icons, stroke 1.5).

**Theme toggle — honest caveat.** `config.toml` sets the static base (dark); the toggle re-injects `:root` custom properties from `lib/tokens.py` and passes the same dict into Altair so charts stay in sync. Streamlit's *native* widget chrome won't follow automatically, so light mode needs explicit CSS overrides for inputs/buttons/selectbox. Budgeted as real work; if light mode can't reach the same fidelity, dark ships as default and light is labeled secondary rather than shipped half-done.

## The centerpiece: Answer Number Line

A single 0–100% horizontal axis, ~200px tall, no y-axis. Layered Altair:

1. **Argued-range band** — `mark_rect` from 78.6 → 91.3, `noise` fill at ~12% opacity.
2. **Legacy answers** — hollow `mark_point` (filled=False, size ~160) at ERP 89.4, TMS 91.3, Portal 78.6, in `noise`; labels above in micro type.
3. **IoT as an uncertainty band, not a point** — it's a ~70%-coverage biased sample, so it's drawn as a low-opacity range. Honest *and* visually distinct.
4. **Divergence annotation** — `12.7 points of disagreement` centered over the band in `warn`.
5. **Governed marker** — thick `mark_rule` + large filled `mark_point` at **64.875** in `accent`, with `GOVERNED 64.875%` set in display type.
6. **The punchline label** — *"The governed truth isn't even in the range they were arguing about."*

That last beat is the whole thesis in one image, and it's earned by the data rather than asserted.

## Choreography — click-driven beats (not timed animation)
You control pacing; nothing auto-advances, nothing sleeps. `st.session_state.beat` + `st.fragment` so only the chart region re-renders:

- **Beat 0** — question set, empty axis. Calm.
- **Beat 1** — four legacy answers appear + argued band.
- **Beat 2** — divergence annotation.
- **Beat 3** — governed marker lands; trust receipt unfolds.

Timed animation is a liability on stage; a primary **Reveal** button (plus the Governed/Ungoverned `st.segmented_control`) is reliable and lets you talk over each beat.

## Trust receipt (treated as an artifact, not a table)
Monospace, hairline rules, deliberately receipt-like:

```
GOVERNED ANSWER · PROVENANCE
─────────────────────────────────────────────
metric         shipment.on_time_delivery_rate
semantic view  SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY
decision       CANONICAL. Actual date = plant-dock receipt.
               Cancelled orders count as late, never dropped
               from the denominator.
entity resolve ERP ⋈ TMS ⋈ Portal ⋈ IoT → 1 canonical shipment
role           SUPPLY_CHAIN_ANALYST_RO
raw ids        0 exposed
```

`decision` text is pulled **verbatim** from the metric `COMMENT` in `sql/04_semantic_view/supply_chain_ontology_semantic_view.sql` — the governance claim is quoted from the object itself, not retyped.

## File structure (container runtime supports modules)
```
streamlit_app.py        entrypoint, router, beat state, hero orchestration
lib/tokens.py           dual-theme tokens, type scale, spacing
lib/theme.py            CSS builder, fontFaces, SVG icon set
lib/copy.py             all demo copy, preset questions, personas, governance text
lib/data.py             cached queries: legacy sources, governed view, drilldowns
lib/analyst.py          Cortex Analyst (send_snow_api_request) + SEMANTIC_VIEW SQL fallback
lib/viz.py              Altair builders incl. answer_number_line()
lib/components.py       hero, chaos panel, governed panel, trust receipt, drawers
.streamlit/config.toml  base theme, fontFaces, server opts
```
`snowflake.yml` `artifacts` must gain `lib/` (verify directory-artifact syntax during deploy).

## Screen architecture
- **Hero (always visible):** question input (`st.chat_input`, fallback `st.text_input`), persona `st.pills` (CEO / VP Supply Chain / Procurement / Analyst), Governed↔Ungoverned `st.segmented_control`, the number line, the governed number, the generated SQL, the trust receipt.
- **Depth drawers (`st.tabs`, verified):** Metrics Board (all 5 canonical metrics) · Dimension Drilldown (supplier tier/region, part category, plant region, customer segment) · Ontology Explorer (9 tables, 10 relationships) · Zero-Identifiers proof (`SILVER.shipment_crosswalk`).

## Robustness (demo must not fail)
- Every Analyst call paired with a direct `SELECT * FROM SEMANTIC_VIEW(... METRICS ...)` — the governed number renders from SQL even if NL is slow or 401s. No red error ever reaches the screen.
- `st.status` shows Analyst progress (intent → SQL → result) so latency reads as *transparency* instead of lag.
- `@st.cache_data(ttl=...)` on every query; warm the preset question on first load. Cross-session caching works here.
- Pre-demo: `sql/09_ops/resume_compute.sql` to wake the 28 Dynamic Tables + warehouse.

## Verification
1. **Probe first** (task 1): report `st.__version__`; assert existence of `segmented_control`/`pills`/`fragment`/`tabs`/`metric(border=)`/`chat_input`; confirm inline CSS survives; confirm Geist renders via `fontFaces`; confirm `lib/` imports; confirm Cortex Analyst returns live. Design to what this actually proves.
2. Post-build smoke test: all 4 beats, both themes, both toggle states, every drawer, Analyst + fallback path.

## Out of scope
- Local/CLI REST 401 in `agents/agent_router.py` — demo uses the SiS transport.
- SQL/data changes — app consumes existing objects only.
- `docs/hackathon-review-*.md` sync — do once the app is final, per doc-conventions memory.