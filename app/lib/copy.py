"""All user-facing narrative in one place.

Kept separate from layout so the wording can be tuned for the demo without
touching rendering logic - and so claims stay consistent wherever they appear.

A note on precision of language: the app must not overstate the finding. The
three systems that were *quoted in meetings* (ERP, TMS, Supplier Portal)
disagreed across a wide band. The IoT sensor source actually sat close to the
governed answer but was dismissed for thin coverage. Saying "nobody was right"
would be false and a judge could check. The honest, stronger line is that the
answer was already present in the source nobody trusted.
"""

PRODUCT = "Governed Answer Engine"
TAGLINE = "One question. Four answers. One governed truth."

SUBTITLE = (
    "Five source systems each compute supply-chain metrics their own way, and "
    "every team believes its number is correct. Ask a question below and watch "
    "the disagreement resolve against a single governed Snowflake semantic view."
)

# Personas deliberately ask for the SAME metric in different words. The
# semantic view's declared synonyms are what make them converge, which is the
# cross-persona consistency proof.
PERSONAS = {
    "Executive": "Are we hitting our delivery dates?",
    "Supply Chain": "What is our supplier on-time delivery performance?",
    "Analyst": "What percentage of shipments arrived on schedule?",
    "Procurement": "What is our OTD%?",
}

BEAT_LABELS = {
    0: "Ask a question to begin",
    1: "The claims",
    2: "The disagreement",
    3: "The governed answer",
}

BEAT_CTA = {
    0: "Run the question",
    1: "Show the disagreement",
    2: "Reveal the governed answer",
    3: "Reset",
}

# Three-step orientation shown before the first question, so a first-time
# viewer understands the interaction before touching it.
HOW_IT_WORKS = [
    ("Ask", "Pick a persona below — or type your own question."),
    ("See the disagreement", "Watch each source system answer the same question differently."),
    ("Get the governed truth", "One semantic view resolves them to a single trusted number."),
]

EMPTY_HINT = "Start here — pick a persona below to ask the supply chain a question."

# The caption under the primary button, telling the viewer what the next click
# will do. Keyed by the CURRENT beat.
NEXT_HINT = {
    1: "Next: measure how far apart these answers really are.",
    2: "Next: reveal the one governed answer.",
}

DEPTH_LOCKED_HINT = (
    "The evidence behind the answer — the full metric board, dimension "
    "drilldowns, the ontology and the identity resolution — unlocks once you "
    "reach the governed answer above."
)


# Shown beside the number line as each beat lands.
BEAT_NARRATIVE = {
    1: (
        "Each team ran its own query against its own system. Every number here "
        "is arithmetically correct and defensible by the team that produced it."
    ),
    2: (
        "This is the range leadership was asked to choose between. No amount of "
        "reconciliation meetings resolves it, because the definitions differ - "
        "not the data."
    ),
    3: (
        "The governed metric resolves the definition once, applies it to every "
        "shipment, and closes each loophole the source systems relied on."
    ),
}

IOT_INSIGHT = (
    "The sensor source was closest to the truth all along. It measured the "
    "right event — physical dock receipt — but covered only 70% of shipments, "
    "so it was dismissed as unreliable. Governance adopted its definition and "
    "fixed its coverage through entity resolution."
)

ZERO_ID_NOTE = (
    "Four systems, four identifier schemes, one canonical shipment. Consumers "
    "of the semantic view never see an ERP order number, a PRO number or an "
    "ASN — only the resolved entity."
)

ONTOLOGY_NOTE = (
    "Read live from DESCRIBE SEMANTIC VIEW, not from a hardcoded list. What you "
    "see is what the object actually declares."
)

DRILLDOWN_NOTE = (
    "Each slice is queried through the semantic view, so the governed "
    "definition is reused rather than reimplemented per chart."
)

SYNTHETIC_NOTE = (
    "100% synthetic data. Every row is generated — no proprietary or customer data."
)
