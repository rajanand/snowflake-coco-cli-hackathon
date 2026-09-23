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
TAGLINE = "Ask as a department. Watch the answers disagree. Then govern it."

SUBTITLE = (
    "Ask as a department and its own siloed agent answers from its own "
    "system. Flip to Governed and the same question, from any department, "
    "routes through one semantic view instead - and converges on one answer."
)

# ---------------------------------------------------------------------------
# Mode framing
# ---------------------------------------------------------------------------

UNGOVERNED_HEADLINE = "Same question. Different systems. Different answers."
GOVERNED_HEADLINE = "One question. One semantic view. One answer."

UNGOVERNED_LEAD = (
    "Each department's agent can see only its own system. It rephrases the "
    "question, runs that system's one canned report, and answers - "
    "confidently and correctly, by its own definition."
)
GOVERNED_LEAD = (
    "The same question, asked by any department in any words, now routes "
    "through Cortex Analyst against the governed semantic view - not the "
    "source tables - so every ask resolves to the same number."
)

UNGOVERNED_EMPTY_HINT = "Ask as a department above to see how its own agent answers."
GOVERNED_EMPTY_HINT = "Ask as a department above to route this through the semantic view."

UNGOVERNED_NUDGE = "→ Flip to Governed to resolve this against the semantic view."
GOVERNED_EMPHASIS = "One query. The semantic view — not the source tables."

# ---------------------------------------------------------------------------
# Scope framing, shown beside every ask
# ---------------------------------------------------------------------------

SCOPE_NOTE_UNGOVERNED = (
    "No access to the semantic view or any other department's system - "
    "only {system}."
)
SCOPE_NOTE_GOVERNED = "Same semantic view, regardless of who asks or how."

# ---------------------------------------------------------------------------
# Trace sidebar — the "behind the scenes" log
# ---------------------------------------------------------------------------

TRACE_HEADER = "Behind the scenes"
TRACE_EMPTY_HINT = "Ask a question to see what happens behind the scenes."
CLEAR_TRACE_LABEL = "Clear trace"

TRACE_STEP_UNDERSTAND = "Understanding the question"
TRACE_STEP_SCOPE_UNGOVERNED = "Scope: {system} only"
TRACE_STEP_SCOPE_GOVERNED = "Scope: governed semantic view"
TRACE_STEP_SQL_UNGOVERNED = "Running {system}'s canned report"
TRACE_STEP_SQL_GOVERNED = "Resolving against the semantic view"
TRACE_STEP_ANSWER = "Answer"

# Shown in the trace when the ungoverned "understand" step used a real
# Cortex Complete call vs. a templated line taken because the call failed or
# was slow. The distinction is stated, never hidden.
TRACE_SOURCE_NOTE = {
    "llm_rephrase": "Cortex Complete",
    "template_fallback": "template fallback — Cortex Complete unavailable",
}

# ---------------------------------------------------------------------------
# Depth section (governed mode)
# ---------------------------------------------------------------------------

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
