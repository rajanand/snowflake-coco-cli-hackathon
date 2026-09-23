"""Data access for the Governed Answer Engine.

Two ideas underpin this module.

**Nothing is hardcoded that can be read from Snowflake.** The governed numbers
come from ``SELECT * FROM SEMANTIC_VIEW(...)``. The governance decisions,
metric expressions and synonyms come from ``DESCRIBE SEMANTIC VIEW``, so the
provenance panel quotes the live object rather than a transcription that could
drift out of date. The legacy numbers are computed by re-running each team's
actual query.

**The divergence is a registry, not a special case.** Every canonical metric
declares its own legacy claimants, so the hero screen tells four different
divergence stories from one code path.

All values in this project are synthetic (see ``data_generation/``).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

DB = "SUPPLY_CHAIN"
SEMANTIC_VIEW = f"{DB}.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY"
ANALYST_ROLE = "SUPPLY_CHAIN_ANALYST_RO"

TTL = 900


# ---------------------------------------------------------------------------
# Core execution
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _session():
    """Resolve a Snowpark session appropriate to the runtime.

    On a container runtime the Streamlit server serves every viewer from one
    process, and ``get_active_session()`` is not thread-safe there - Snowflake's
    migration guidance is to use ``st.connection`` instead. The fallback keeps
    the app working on a warehouse runtime, where ``st.connection`` may be
    unavailable.
    """
    try:
        return st.connection("snowflake").session()
    except Exception:
        from snowflake.snowpark.context import get_active_session

        return get_active_session()


def session():
    return _session()


@st.cache_data(ttl=TTL, show_spinner=False)
def run(sql: str) -> pd.DataFrame:
    """Execute SQL and return a DataFrame. Cached across viewer sessions."""
    return session().sql(sql).to_pandas()


def scalar(sql: str, default=None):
    """First cell of the first row, or ``default`` if the query yields nothing."""
    try:
        df = run(sql)
        if df.empty:
            return default
        return df.iloc[0, 0]
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Live semantic-view metadata
# ---------------------------------------------------------------------------

@st.cache_data(ttl=TTL, show_spinner=False)
def semantic_meta() -> dict:
    """Parse DESCRIBE SEMANTIC VIEW into a structured dict.

    Yields the governance COMMENT, SQL expression and synonyms for every
    metric, plus the table and relationship graph - all read from the live
    object so the UI cannot assert something the object does not say.
    """
    try:
        df = run(f"DESCRIBE SEMANTIC VIEW {SEMANTIC_VIEW}")
    except Exception:
        return {"metrics": {}, "tables": {}, "relationships": {},
                "dimensions": {}, "facts": {}, "comment": ""}

    out = {"metrics": {}, "tables": {}, "relationships": {},
           "dimensions": {}, "facts": {}, "comment": ""}

    for _, r in df.iterrows():
        kind = (r.get("object_kind") or "").strip()
        name = (r.get("object_name") or "").strip()
        parent = (r.get("parent_entity") or "").strip()
        prop = (r.get("property") or "").strip()
        val = r.get("property_value")

        if not kind and prop == "COMMENT":
            out["comment"] = val
            continue

        bucket = {
            "METRIC": "metrics", "TABLE": "tables",
            "RELATIONSHIP": "relationships", "DIMENSION": "dimensions",
            "FACT": "facts",
        }.get(kind)
        if not bucket:
            continue

        entry = out[bucket].setdefault(name, {"name": name, "parent": parent})
        entry[prop.lower()] = val

    return out


def metric_meta(metric_name: str) -> dict:
    """Live metadata for one metric, keyed by its unqualified upper-case name."""
    return semantic_meta()["metrics"].get(metric_name.upper(), {})


# ---------------------------------------------------------------------------
# Governed values
# ---------------------------------------------------------------------------

@st.cache_data(ttl=TTL, show_spinner=False)
def governed_all() -> dict:
    """All five canonical metrics in a single semantic-view query."""
    sql = f"""
        SELECT * FROM SEMANTIC_VIEW(
          {SEMANTIC_VIEW}
          METRICS shipment.on_time_delivery_rate,
                  customer_order.customer_fill_rate,
                  purchase_order.supplier_fill_rate,
                  inventory_snapshot.days_of_inventory,
                  landed_cost.landed_cost_per_unit
        )
    """
    df = run(sql)
    if df.empty:
        return {}
    row = df.iloc[0]
    return {c.upper(): (None if pd.isna(row[c]) else float(row[c])) for c in df.columns}


def governed_value(metric_key: str):
    """One governed value. This is the fallback that makes the demo safe:
    if Cortex Analyst is slow or errors, the number still comes from the
    semantic view over plain SQL."""
    return governed_all().get(metric_key.upper())


def governed_sql(metric: str) -> str:
    """The semantic-view query for a single metric, shown to the audience."""
    return (
        f"SELECT * FROM SEMANTIC_VIEW(\n"
        f"  {SEMANTIC_VIEW}\n"
        f"  METRICS {metric}\n"
        f")"
    )


# ---------------------------------------------------------------------------
# Metric registry: who claimed what, and why they were wrong
# ---------------------------------------------------------------------------
# `flaw` states the specific loophole each legacy definition used. This is the
# substance of the demo - not that the numbers differ, but that each one is
# defensible on its own terms and still wrong for the business.

METRICS = {
    "otd": {
        "key": "otd",
        "label": "On-Time Delivery",
        "metric": "shipment.on_time_delivery_rate",
        "metric_name": "ON_TIME_DELIVERY_RATE",
        "result_col": "ON_TIME_DELIVERY_RATE",
        "unit": "%",
        "fmt": "pct",
        "domain": [55, 100],
        "questions": [
            "What's our on-time delivery rate?",
            "Are we hitting our delivery dates?",
            "How is supplier delivery performance tracking?",
            "What percentage of shipments arrived on schedule?",
        ],
        "legacy": [
            {
                "team": "Operations",
                "system": "ERP",
                "definition": "Ship-confirm before requested date",
                "flaw": "Excludes cancelled and backorder rows from the denominator",
                "sql": """SELECT ROUND(SUM(CASE WHEN ACTUAL_SHIP_DATE <= REQUESTED_SHIP_DATE
       THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 3) AS v
FROM SUPPLY_CHAIN.SOURCE_ERP.ORDERS
WHERE ORDER_STATUS = 'COMPLETE'""",
            },
            {
                "team": "Logistics",
                "system": "TMS",
                "definition": "Delivery before promised date",
                "flaw": "Promised date already contains a 2-day carrier buffer",
                "sql": """SELECT ROUND(SUM(CASE WHEN FINAL_DELIVERY_DATE <= PROMISED_DELIVERY_DATE
       THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 3) AS v
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.DELIVERIES""",
            },
            {
                "team": "Procurement",
                "system": "Supplier Portal",
                "definition": "ASN receipt before planned date",
                "flaw": "Drops in-transit shipments, hiding the worst cases",
                "sql": """SELECT ROUND(SUM(CASE WHEN ACTUAL_RECEIPT_DATE <= PLANNED_RECEIPT_DATE
       THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 3) AS v
FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.SHIPMENTS
WHERE SHIPMENT_STATUS = 'RECEIVED'""",
            },
        ],
        # IoT is modelled as an interval rather than a point: it measures the
        # right event but only covers ~70% of shipments, so a single number
        # would overstate its precision.
        "sample": {
            "team": "Warehouse",
            "system": "IoT sensors",
            "definition": "Sensor-detected dock receipt",
            "flaw": "Only ~70% of shipments carry an active sensor tag",
        },
    },
    "doi": {
        "key": "doi",
        "label": "Days of Inventory",
        "metric": "inventory_snapshot.days_of_inventory",
        "metric_name": "DAYS_OF_INVENTORY",
        "result_col": "DAYS_OF_INVENTORY",
        "unit": " days",
        "fmt": "days",
        "domain": [0, 540],
        "questions": [
            "How many days of inventory are we holding?",
            "What's our stock coverage?",
            "What is days on hand across plants?",
        ],
        "legacy": [
            {
                "team": "Planning",
                "system": "ERP forecast",
                "definition": "Stock divided by forecast daily demand",
                "flaw": "Forecast carries optimism bias, so coverage looks tighter than it is",
                "sql": """SELECT ROUND(AVG(inv.current_stock
       / NULLIF(f.forecasted_daily_demand, 0)), 3) AS v
FROM SUPPLY_CHAIN.GOLD.fact_inventory_snapshot inv
JOIN SUPPLY_CHAIN.SOURCE_ERP.demand_forecast f
  ON inv.part_id = f.part_sku
 AND DATE_TRUNC('MONTH', inv.snapshot_date) = f.forecast_month""",
            },
            {
                "team": "Finance",
                "system": "Finance ledger",
                "definition": "Inventory value divided by daily COGS",
                "flaw": "Dollar-based, not unit-based - same word 'days', different scale entirely",
                "sql": """SELECT ROUND(AVG(inv.inventory_value
       / NULLIF(cogs.daily_cogs, 0)), 3) AS v
FROM SUPPLY_CHAIN.GOLD.fact_inventory_snapshot inv
JOIN SUPPLY_CHAIN.SOURCE_FINANCE.daily_cogs cogs
  ON inv.part_id = cogs.part_id
 AND inv.snapshot_date = cogs.cogs_date""",
            },
        ],
        "sample": None,
    },
    "landed_cost": {
        "key": "landed_cost",
        "label": "Landed Cost per Unit",
        "metric": "landed_cost.landed_cost_per_unit",
        "metric_name": "LANDED_COST_PER_UNIT",
        "result_col": "LANDED_COST_PER_UNIT",
        "unit": "",
        "fmt": "usd",
        "domain": [200, 520],
        "questions": [
            "What's our true landed cost per unit?",
            "What is the all-in cost per unit?",
            "How much do we actually pay per unit delivered?",
        ],
        "legacy": [
            {
                "team": "Procurement",
                "system": "Supplier Portal",
                "definition": "PO price plus quoted freight",
                "flaw": "Omits customs duty and handling, understating true cost",
                "sql": """SELECT ROUND(AVG(dp.unit_cost
       + COALESCE(fq.freight_estimate, 0)), 3) AS v
FROM SUPPLY_CHAIN.GOLD.dim_part dp
LEFT JOIN SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.freight_quotes fq
  ON fq.part_id = dp.part_id""",
            },
            {
                "team": "Logistics",
                "system": "Freight invoices",
                "definition": "Actual freight plus customs",
                "flaw": "Contains no purchase price at all - not a landed cost in any real sense",
                "sql": """SELECT ROUND(AVG(fi.freight_cost + fi.customs_duty), 3) AS v
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.freight_invoices fi""",
            },
        ],
        "sample": None,
    },
    "fill": {
        "key": "fill",
        "label": "Fill Rate",
        "metric": "customer_order.customer_fill_rate",
        "metric_name": "CUSTOMER_FILL_RATE",
        "result_col": "CUSTOMER_FILL_RATE",
        "unit": "%",
        "fmt": "pct",
        "domain": [80, 100],
        "questions": [
            "What's our fill rate?",
            "What is our perfect order rate?",
            "How often do we ship orders complete?",
        ],
        "legacy": [
            {
                "team": "Procurement",
                "system": "Supplier Portal",
                "definition": "Units received over units ordered on POs",
                "flaw": "Measures supplier-to-us flow, not us-to-customer - a different concept wearing the same name",
                "sql": """SELECT ROUND(SUM(qty_received)
       / NULLIF(SUM(qty_ordered), 0) * 100, 3) AS v
FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.purchase_orders""",
            },
            {
                "team": "Warehouse",
                "system": "TMS pick ops",
                "definition": "Units picked over units ordered on pick lists",
                "flaw": "Measures warehouse execution, not whether the customer got a complete order",
                "sql": """SELECT ROUND(SUM(units_picked)
       / NULLIF(SUM(units_ordered), 0) * 100, 3) AS v
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.pick_operations""",
            },
        ],
        "sample": None,
        # Governance kept two measures rather than blending them into one.
        "note": (
            "Governance resolved this by refusing to blend: customer_fill_rate "
            "and supplier_fill_rate remain two separate canonical measures, "
            "because they describe opposite directions of flow."
        ),
    },
}

METRIC_ORDER = ["otd", "doi", "landed_cost", "fill"]


# ---------------------------------------------------------------------------
# Legacy + sample computation
# ---------------------------------------------------------------------------

@st.cache_data(ttl=TTL, show_spinner=False)
def legacy_answers(metric_key: str) -> list[dict]:
    """Re-run each team's own query so the divergence is computed, not claimed."""
    spec = METRICS[metric_key]
    out = []
    for src in spec["legacy"]:
        val = scalar(src["sql"])
        out.append({**src, "value": None if val is None else float(val)})
    return out


@st.cache_data(ttl=TTL, show_spinner=False)
def iot_sample() -> dict | None:
    """The IoT sensor subset as an interval, with a Wilson 95% CI.

    The sensor source measured the *right* event (plant-dock receipt) but only
    covered ~70% of shipments, so it was dismissed. Representing it as an
    interval rather than a point is both statistically honest and the crux of
    the story: the governed answer lands inside this interval, meaning the
    answer was already present in the source nobody trusted.
    """
    sql = """
    WITH s AS (
      SELECT COUNT(*) AS n,
             SUM(CASE WHEN ON_TIME_FLAG = 1 THEN 1 ELSE 0 END) AS k
      FROM SUPPLY_CHAIN.SILVER.SHIPMENT_CROSSWALK
      WHERE HAS_IOT_TRACKING = TRUE
    ), w AS (
      SELECT n, k, k / NULLIF(n, 0)::FLOAT AS p, 1.959964 AS z FROM s
    )
    SELECT n,
           p * 100 AS point,
           ((p + z*z/(2*n) - z*SQRT((p*(1-p) + z*z/(4*n))/n)) / (1 + z*z/n)) * 100 AS lo,
           ((p + z*z/(2*n) + z*SQRT((p*(1-p) + z*z/(4*n))/n)) / (1 + z*z/n)) * 100 AS hi,
           (SELECT COUNT(*) FROM SUPPLY_CHAIN.SILVER.SHIPMENT_CROSSWALK) AS total
    FROM w
    """
    try:
        df = run(sql)
        if df.empty:
            return None
        r = df.iloc[0]
        n, total = int(r["N"]), int(r["TOTAL"])
        return {
            "n": n,
            "total": total,
            "coverage": round(n * 100.0 / total, 1) if total else 0.0,
            "point": float(r["POINT"]),
            "lo": float(r["LO"]),
            "hi": float(r["HI"]),
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Supporting datasets
# ---------------------------------------------------------------------------

@st.cache_data(ttl=TTL, show_spinner=False)
def crosswalk_sample(limit: int = 8) -> pd.DataFrame:
    return run(f"""
        SELECT canonical_shipment_id, erp_order_number, pro_number,
               asn_number, device_tag, resolved_supplier_id, on_time_flag
        FROM {DB}.SILVER.shipment_crosswalk
        ORDER BY canonical_shipment_id
        LIMIT {int(limit)}
    """)


DIMENSIONS = {
    "Supplier tier": "supplier.tier_name",
    "Supplier region": "supplier.supplier_region",
    "Part category": "part.category",
    "Plant region": "plant.plant_region",
    "Customer segment": "customer.customer_segment",
}

# Which dimensions each metric's fact table can actually reach through the
# relationship graph. Offering an unreachable pair would produce a confusing
# SQL error mid-demo, so the UI constrains the choice instead.
REACHABLE = {
    "otd": ["supplier.tier_name", "supplier.supplier_region",
            "part.category", "plant.plant_region"],
    "fill": ["part.category", "customer.customer_segment"],
    "doi": ["part.category", "plant.plant_region"],
    "landed_cost": ["supplier.tier_name", "supplier.supplier_region",
                    "part.category", "plant.plant_region"],
}


@st.cache_data(ttl=TTL, show_spinner=False)
def drilldown(dimension: str, metric: str) -> pd.DataFrame:
    """Dimension breakdown queried *through the semantic view*.

    Deliberately not a hand-written GROUP BY against GOLD: the point is that
    the same governed metric definition is reused when slicing.
    """
    return run(f"""
        SELECT * FROM SEMANTIC_VIEW(
          {SEMANTIC_VIEW}
          DIMENSIONS {dimension}
          METRICS {metric}
        ) ORDER BY 1
    """)


@st.cache_data(ttl=TTL, show_spinner=False)
def entity_counts() -> dict:
    m = semantic_meta()
    return {
        "tables": len(m["tables"]),
        "relationships": len(m["relationships"]),
        "metrics": len(m["metrics"]),
        "dimensions": len(m["dimensions"]),
        "facts": len(m["facts"]),
    }


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def fmt(value, kind: str, precision: int | None = None) -> str:
    """Format a metric value for display. Returns an em dash for None."""
    if value is None:
        return "—"
    if kind == "pct":
        p = 3 if precision is None else precision
        return f"{value:.{p}f}%"
    if kind == "usd":
        return f"${value:,.2f}"
    if kind == "days":
        p = 1 if precision is None else precision
        return f"{value:.{p}f}"
    return f"{value:,.2f}"
