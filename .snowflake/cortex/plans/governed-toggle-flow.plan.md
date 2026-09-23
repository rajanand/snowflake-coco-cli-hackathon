## Goal

Rebuild the core interaction around **one toggle** plus a **live "behind the scenes" trace log in the native left sidebar**. The screen shows a single supply-chain metric and flips between two modes:

- **Ungoverned** (default landing — "the problem"): the viewer asks *as* a department (Operations, Logistics, Procurement, ...). Each department has its own siloed agent that can only see its own system, rephrases the question with a real Cortex Complete call, and runs that system's fixed canned SQL. Different departments -> different definitions, different SQL, different answers.
- **Governed** ("the fix"): the viewer asks *as* any department, but now the question routes through Cortex Analyst against the **semantic view** — one object, one SQL shape, one answer, no matter who asks or how they phrase it.

The toggle is the star control on the main stage. `st.sidebar` (native, left) is the second star: every ask, in either mode, appends a step-by-step trace entry to the sidebar that is never cleared automatically — so by the end of a demo the sidebar is a literal, growing proof that ungoverned asks diverge and governed asks converge.

## Interaction model

1. Viewer picks a **metric** (On-Time Delivery / Days of Inventory / Landed Cost / Fill Rate) on the main stage.
2. Viewer flips the **mode toggle** (Ungoverned default) on the main stage.
3. Viewer clicks a **persona chip** — one chip per legacy claimant *team* for that metric (dynamic per metric: OTD -> Operations/Logistics/Procurement; DOI -> Planning/Finance; etc.).
4. The app resolves the answer for that click and:
   - Updates the main stage's "current answer" (big number + framing for the mode).
   - Appends one entry to the sidebar trace log, expanded, with the mode's colour and steps.
   - Updates the number-line chart with the newly revealed point (ungoverned) or the governed marker (governed).
5. Repeat with a different persona and/or toggle the mode. Nothing resets except an explicit "Clear trace" button in the sidebar.

### Confirmed decisions
- Ungoverned "understand & rephrase" step is a **real Cortex Complete call**, scoped to that one department, with a templated fallback if the call fails or times out. The trace entry's `source` field records which happened (`llm_rephrase` vs `template_fallback`) — never silently pretend the LLM ran when it didn't.
- **Persona chips = the metric's legacy-claimant teams**, not a fixed Executive/Supply Chain/Analyst/Procurement list. The chip set changes per metric.
- **Trace log persists across metric switches.** One continuous session log in the sidebar, each entry tagged with its metric label.
- **Sidebar is native `st.sidebar` (left)**, not a synthetic right column. `initial_sidebar_state` changes from `"collapsed"` to `"expanded"` so the trace log is visible from the first run, and `lib/theme.py`'s injected CSS gains a `[data-testid="stSidebar"]` block (background/border using existing `--ge-*` tokens) so the sidebar matches the rest of the design system instead of looking like default Streamlit chrome.

## What stays (reused as-is)

- `lib/data.py`'s `METRICS` registry structure (per-team `definition`, `flaw`, `sql`) — extended, not replaced.
- `lib/analyst.py`'s governed transport chain (`ask()`, `call_analyst()`, 3-tier fallback) — reused unchanged for Governed-mode asks.
- `lib/viz.py`'s `answer_number_line` — reused, fed an *accumulating* legacy list (only teams actually asked-about so far this session) instead of a static full list.
- `lib/theme.py` / `lib/tokens.py` — design tokens and the existing `.ge-badge.governed` / `.ge-badge.ungoverned` classes are reused to colour trace entries.

## What changes

### 1. [app/lib/data.py](app/lib/data.py)
- Add an `"ask"` field to every legacy claimant dict — a natural-language question phrased in that team's own voice (e.g. Operations: "Are we hitting our ship dates?"; Procurement: "What's our receiving on-time rate?"). This replaces the old fixed `PERSONAS` dict in `copy.py`.
- No other structural changes — `sql`, `definition`, `flaw`, `team`, `system` are already what the trace needs.

### 2. [app/lib/analyst.py](app/lib/analyst.py)
- New `siloed_ask(question: str, entry: dict) -> Result`:
  - Calls `SNOWFLAKE.CORTEX.COMPLETE(<model>, ...)` via `session().sql(..., params=[...])` (bind params, not string interpolation) with a system prompt scoping the model to *only* `entry["system"]`/`entry["team"]`, instructed not to reference any other system or a shared semantic layer. Short timeout (~8s).
  - Success: `Result.text` = the rephrase, `Result.source = "llm_rephrase"`.
  - Failure/timeout: `Result.text` = a templated line, `Result.source = "template_fallback"`. Never raises.
  - Always then runs `entry["sql"]` via `D.scalar` for `Result.value` (deterministic, unaffected by the LLM step).
- `ask()` (governed) unchanged — its `text`/`sql`/`value`/`source`/`transport`/`latency_ms` map directly onto the governed trace steps.

### 3. [app/lib/components.py](app/lib/components.py)
- `persona_chips(c, spec, mode)` — one chip per `spec["legacy"]` entry (dynamic per metric), reused in both modes. Replaces `question_bar`.
- `on_persona_ask(entry, mode, metric_key)` (called from `streamlit_app.py`, dispatching to `A.siloed_ask` or `A.ask`) — builds and appends the trace entry, updates `revealed` state.
- `trace_sidebar(c, trace: list[dict])` — rendered inside `with st.sidebar:`:
  - Newest entry expanded with all 4 steps (`Understanding the question` -> `Scope` -> SQL step (`st.code`) -> `Answer`).
  - Older entries collapsed to a one-line chip (mode badge, persona, metric, shown value) inside an `st.expander` for replay.
  - Left-border colour: `var(--ge-warn)` for ungoverned entries, `var(--ge-accent)` for governed entries.
  - Small header ("Behind the scenes") + a "Clear trace" button that resets `session_state["trace"]`/`"revealed"` on demand only.
- `ungoverned_panel` / `governed_panel` simplified to show the *current* ask's answer (fed by the latest matching trace entry) rather than a static all-teams comparison. The number-line chart is fed `[legacy entries in revealed[metric_key]]` for ungoverned points, and the governed marker appears once any governed ask has happened for that metric.

### 4. [app/lib/copy.py](app/lib/copy.py)
- Drop the fixed `PERSONAS` dict (superseded by per-team `ask` text in `data.py`).
- Add: trace step label templates, "Behind the scenes" sidebar header, "Clear trace" button label, siloed-scope framing line ("No access to the semantic view or other departments' systems."), governed-scope framing line ("Same semantic view, regardless of who asks or how.").

### 5. [app/streamlit_app.py](app/streamlit_app.py)
- `st.set_page_config(..., initial_sidebar_state="expanded")` (was `"collapsed"`).
- New session state: `trace` (list, append-only), `trace_seq` (id counter), `revealed` (`dict[metric_key -> set[team]]`), never auto-reset on mode/metric switch.
- Layout: everything ask/toggle/panel-related renders in the main body (masthead -> metric selector -> mode toggle -> persona chips (+ free-text NL box, governed mode only) -> current-answer panel + chart). `with st.sidebar:` calls `UI.trace_sidebar(c, st.session_state["trace"])`.

## Deploy + verify

- Files changing: `streamlit_app.py`, `lib/analyst.py`, `lib/components.py`, `lib/copy.py`, `lib/data.py`, `lib/theme.py` (sidebar CSS) — via the SQL stage pipeline (`WRITE_FILE_TO_STAGE` -> `@DEPLOY_TRANSIT` -> `COPY FILES` into `versions/live/`), since CLI deploy is still blocked by the interactive-OAuth issue. Restart the container if it serves stale modules.
- Verify Cortex Complete model availability in `sc23256.ap-northeast-1.aws` before wiring `siloed_ask` (`SHOW MODELS` / try a cheap model, confirm region support) — pick a fallback-safe default.
- Smoke test:
  1. Ungoverned, OTD: click Operations, Logistics, Procurement in turn — 3 distinct SQL blocks, 3 distinct answers, sidebar trace grows to 3 entries (not reset), chart accumulates 3 hollow points.
  2. Toggle Governed, click 2 different personas — same SQL, same governed number both times, both logged as governed (accent) entries, chart shows one governed marker.
  3. Switch metric to Days of Inventory — persona chips change to Planning/Finance; earlier OTD trace entries remain visible in the sidebar (tagged "On-Time Delivery"); chart scoped to DOI's own revealed points only.
  4. Force/observe a Cortex Complete failure path — trace entry shows `template_fallback` labelling, not a silent/undistinguished rephrase.
  5. "Clear trace" empties the sidebar log and reveal state without breaking the current main-stage panel.
  6. Confirm the sidebar is expanded by default and its styling (background/border/text) matches the rest of the app rather than default Streamlit grey chrome.

## Notes / defaults carried over
- Default mode = Ungoverned so the problem lands first.
- One metric on screen at a time; the toggle + persona chips govern the main stage; the sidebar trace log is the one thing that spans metrics and modes.
