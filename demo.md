# Demo

Links to the recorded end-to-end demo for the Supply Chain Ontology & Governed
Conversational Analytics submission (Snowflake CoCo CLI Hackathon 2026 for GCCs).

## Links

- Demo video: 
- Live app (Governed Answer Engine): [GOVERNED_ANSWER_ENGINE](https://app.snowflake.com/ehntqrv/gc94671/#/streamlit-apps/SUPPLY_CHAIN.SEMANTIC_MODELS.GOVERNED_ANSWER_ENGINE)

## What the demo covers

1. **The problem** — five fragmented systems (ERP, TMS, Supplier Portal, IoT,
   Finance) each compute "On-Time Delivery" differently (89.4% / 91.3% /
   78.6% / biased sample), and every team believes its own number.
2. **Architecture, briefly** — Bronze → Silver (entity resolution) → Gold →
   governed Semantic View → Cortex Analyst.
3. **Live demo** — in the Governed Answer Engine app
   (`SUPPLY_CHAIN.SEMANTIC_MODELS.GOVERNED_ANSWER_ENGINE`): ask the same
   question as three different departments in Ungoverned mode (answers
   disagree), then flip to Governed mode (one number, 64.875%, routed
   through the semantic view).
4. **Why it's not just "different," it's stricter** — the governed number
   closes loopholes each legacy system used to look better than reality
   (cancelled/overdue-in-transit rows always count as late).
5. **Close** — native Snowflake end to end (Dynamic Tables, Semantic View,
   Cortex Analyst), nothing cached or pre-rendered.

Full run-of-show / talking points: see the brainstorm thread with Cortex Code
(not yet committed as a standalone doc — ask to have it written out if needed).
