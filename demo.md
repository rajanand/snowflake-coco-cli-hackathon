# Demo

Links to the recorded end-to-end demo for the Supply Chain Ontology & Governed
Conversational Analytics submission (Snowflake CoCo CLI Hackathon 2026 for GCCs).

## Links

- Demo video: https://youtu.be/M_x4EgoHN08
- Live app (Governed Answer Engine): [GOVERNED_ANSWER_ENGINE](https://app.snowflake.com/ehntqrv/gc94671/#/streamlit-apps/SUPPLY_CHAIN.SEMANTIC_MODELS.GOVERNED_ANSWER_ENGINE)

## What the demo covers (summary)

1. **The problem** — five fragmented systems (ERP, TMS, Supplier Portal, IoT,
   Finance) each compute "On-Time Delivery" differently (89.4% / 91.3% /
   78.6% / biased sample), and every team believes its own number.
2. **Architecture, briefly** — walk the medallion flowchart and ER diagram in
   `docs/architecture-and-er-diagram.html`, then briefly show the real
   Snowflake objects behind it (Dynamic Tables, the deployed Semantic View).
3. **Live demo** — in the Governed Answer Engine app
   (`SUPPLY_CHAIN.SEMANTIC_MODELS.GOVERNED_ANSWER_ENGINE`): ask the same
   question as three different departments in Ungoverned mode (answers
   disagree), flip to Governed mode (one number, 64.875%, routed through the
   semantic view), then type an off-topic question and show it gets flagged
   as unmatched instead of silently answering.
4. **Why it's not just "different," it's stricter** — the governed number
   closes loopholes each legacy system used to look better than reality
   (cancelled/overdue-in-transit rows always count as late).
5. **Close** — native Snowflake end to end (Dynamic Tables, Semantic View,
   Cortex Analyst), nothing cached or pre-rendered.

---

## Full recording script

Target run time **~4:40**. Every number and line of UI copy quoted here is
pulled directly from the live app (`app/lib/data.py`, `app/lib/copy.py`) and
`README.md` — say it as written, don't paraphrase the numbers.

Before recording: run `sql/09_ops/resume_compute.sql` so the Dynamic Tables
and warehouse are warm, and open the app once yourself to pre-warm the
Streamlit container (first open after a compute-pool resume is a cold start).

### 0:00–0:20 — Cold open: the problem

> "Ask Operations what our on-time delivery rate is — 89%. Ask Logistics —
> 91%. Ask Procurement — 79%. All three are right, by their own definition.
> This is a governed answer engine, built entirely on Snowflake, that fixes
> that."

**On screen:** title card, or `README.md`'s "The problem, in one table".

### 0:20–1:00 — Architecture walkthrough (HTML)

**On screen:** open `docs/architecture-and-er-diagram.html` in a browser.

> "Here's the shape of it. Five fragmented source systems land in Bronze, get
> entity-resolved in Silver, modeled dimensionally in Gold, then exposed
> through one governed Semantic View."

Scroll to the medallion flowchart, point left-to-right as you say the above.
Scroll down to the ER diagram.

> "Nine entities, ten relationships — this isn't a diagram I drew by hand,
> it's transcribed straight from the live `CREATE SEMANTIC VIEW` DDL."

Point at the "Canonical metrics — validated results" table.

> "64.875% on-time delivery — that's the number we'll see live in a minute."

Keep this under 40 seconds — it's context, not the main event.

### 1:00–1:30 — Snowflake objects, briefly

**On screen:** switch to Snowsight / a worksheet.

> "Before the app — this is real, not a mockup."

Run, narrating while each loads (don't dwell on the output):

```sql
SHOW DYNAMIC TABLES IN SCHEMA SUPPLY_CHAIN.GOLD;
```
> "Twenty-eight Dynamic Tables — this is the actual pipeline."

```sql
DESCRIBE SEMANTIC VIEW SUPPLY_CHAIN.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY;
```
> "And this is the governed object itself — tables, relationships, metrics,
> synonyms, all native Snowflake, nothing bolted on."

### 1:30–1:50 — Open the app

> "This is the Governed Answer Engine, a Streamlit-in-Snowflake app. Nothing
> you're about to see is pre-rendered — every answer is a live query."

**On screen:** open the app URL. Point at the metric selector (On-Time
Delivery default) and the Ungoverned/Governed toggle, currently **Ungoverned**.

### 1:50–2:40 — Ungoverned mode: the disagreement, live

> "Each department's chip asks its own siloed agent — one that can see
> *only* that department's system. Watch the same business question asked
> three different ways."

**Action — click "Operations" (ERP).** → "Eighty-nine point four percent."
**Action — click "Logistics" (TMS).** → "Ninety-one point three percent."
**Action — click "Procurement" (Supplier Portal).** → "Seventy-eight point
six percent."

> "Three systems. Three honest answers. A thirteen-point spread on the exact
> same question — and nobody here is lying."

### 2:40–3:10 — Flip to Governed: one answer

**Action — click the mode toggle to "Governed", ask the same question again.**

> "Sixty-four point eight-seven-five percent. One semantic view, one answer —
> and it's *stricter* than all three, not a compromise between them. ERP
> drops cancelled orders, TMS bakes in a carrier buffer, the Supplier Portal
> drops in-transit shipments. Governance doesn't average the loopholes away —
> it closes them."

### 3:10–3:50 — The guardrail: ask something off-topic

> "This matters as much as the governed answer itself. Watch what happens
> when I ask something this semantic view has no business answering."

**Action — type an off-topic question into "Or ask anything, in your own
words"** — e.g. *"What's the capital of France?"*

**On screen:** a toast appears — *"Couldn't match that to a governed metric —
try asking about On-Time Delivery, Fill Rate…"* — and the sidebar trace log
shows a new entry: **"No governed metric matched."**

> "It doesn't guess. A system that confidently answers questions outside its
> own governed scope isn't trustworthy — this one tells you when a question
> doesn't match any metric's definition, instead of quietly handing back
> whatever was last on screen."

### 3:50–4:15 — Why stricter, not just different (recap)

> "To be clear: the governed number isn't just one more opinion added to the
> pile. It's the one that closes every loophole the other three used to look
> better than reality — at the same time."

### 4:15–4:40 — Close

> "Everything here — the pipeline, the semantic view, the agent routing, this
> app — is native Snowflake, built end-to-end with CoCo CLI. And to be fully
> transparent: every row in this dataset is 100% synthetic, generated for
> this hackathon — no proprietary or customer data anywhere in this project."

**On screen:** footer of the app showing the "100% synthetic data" note —
hold for 2 seconds before cutting.

---

## Recording checklist

- [ ] `sql/09_ops/resume_compute.sql` run beforehand (avoid a cold-start stall
      on camera)
- [ ] App opened once already so the container isn't cold on the first click
- [ ] `docs/architecture-and-er-diagram.html` opens cleanly in a browser (uses
      the CDN mermaid script — needs internet access, not the Snowflake
      report sandbox path)
- [ ] Screen resolution set so the sidebar trace panel is fully legible
- [ ] Capture in this order: HTML architecture → Snowflake objects →
      Ungoverned (Operations → Logistics → Procurement) → toggle Governed →
      off-topic question (no-match flag) → footer
- [ ] Say the numbers exactly as shown on screen (89.4% / 91.3% / 78.6% /
      64.875%) — don't round differently than the UI
- [ ] Confirm the off-topic question actually triggers the toast + sidebar
      "No governed metric matched" entry in a dry run before recording
- [ ] End on the synthetic-data disclosure line — required by the official
      rules (§4.4(e)) and good practice for judge trust

