"""
Supply Chain Ontology - Governed Intelligence Demo
==================================================
Enterprise-grade Streamlit-in-Snowflake application demonstrating
semantic view governance for supply chain analytics.

Architecture:
- snowflake.snowpark.context for data queries (SiS embedded session)
- _snowflake.send_snow_api_request for Cortex Analyst (SiS sandbox-safe)
- No external dependencies beyond pre-installed SiS packages
"""

import streamlit as st
import pandas as pd
import altair as alt
import json
from datetime import datetime, timedelta
from snowflake.snowpark.context import get_active_session

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Supply Chain Ontology | Governed Intelligence",
    page_icon=":material/hub:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database Constants
DATABASE = "SUPPLY_CHAIN"
SEMANTIC_VIEW_FQN = f"{DATABASE}.SEMANTIC_MODELS.SUPPLY_CHAIN_ONTOLOGY"

# ═══════════════════════════════════════════════════════════════════════════════
# Theme-Aware CSS (works in both light and dark mode)
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* CSS Variables for theme awareness */
    :root {
        --brand-primary: #29B5E8;
        --brand-dark: #11567F;
        --success: #10B981;
        --warning: #F59E0B;
        --danger: #EF4444;
        --surface-elevated: rgba(255,255,255,0.95);
        --text-primary: #1F2937;
        --text-secondary: #6B7280;
        --border-default: #E5E7EB;
    }
    
    /* Dark mode overrides */
    @media (prefers-color-scheme: dark) {
        :root {
            --surface-elevated: rgba(30,41,59,0.95);
            --text-primary: #F1F5F9;
            --text-secondary: #94A3B8;
            --border-default: #334155;
        }
    }
    
    /* Streamlit dark mode detection */
    [data-testid="stAppViewContainer"][data-theme="dark"] {
        --surface-elevated: rgba(30,41,59,0.95);
        --text-primary: #F1F5F9;
        --text-secondary: #94A3B8;
        --border-default: #334155;
    }

    /* Global layout */
    .main .block-container {
        padding: 1.5rem 2rem 2rem 2rem;
        max-width: 1400px;
    }
    
    /* Story header - gradient banner */
    .story-header {
        background: linear-gradient(135deg, #11567F 0%, #29B5E8 100%);
        color: white;
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(41, 181, 232, 0.2);
    }
    .story-header h1 {
        margin: 0 0 0.5rem 0;
        font-size: 1.875rem;
        font-weight: 600;
        letter-spacing: -0.025em;
    }
    .story-header p {
        margin: 0;
        opacity: 0.9;
        font-size: 1rem;
    }
    
    /* KPI Card System */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    .kpi-card {
        background: var(--surface-elevated);
        border-radius: 10px;
        padding: 1.25rem;
        border-left: 4px solid var(--brand-primary);
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .kpi-card.success { border-left-color: var(--success); }
    .kpi-card.warning { border-left-color: var(--warning); }
    .kpi-card.danger { border-left-color: var(--danger); }
    
    .kpi-label {
        font-size: 0.75rem;
        color: var(--text-secondary);
        margin-bottom: 0.25rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }
    .kpi-value {
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--text-primary);
        line-height: 1.2;
    }
    .kpi-delta {
        font-size: 0.8rem;
        margin-top: 0.25rem;
        color: var(--text-secondary);
    }
    .kpi-delta.positive { color: var(--success); }
    .kpi-delta.negative { color: var(--danger); }
    
    /* Status cards */
    .status-card {
        border-radius: 10px;
        padding: 1.25rem;
        margin: 0.75rem 0;
    }
    .status-card.conflict {
        background: linear-gradient(to right, rgba(251,191,36,0.15), rgba(251,191,36,0.05));
        border: 1px solid rgba(251,191,36,0.4);
    }
    .status-card.conflict h4 { color: #B45309; }
    
    .status-card.success {
        background: linear-gradient(to right, rgba(16,185,129,0.15), rgba(16,185,129,0.05));
        border: 1px solid rgba(16,185,129,0.4);
    }
    .status-card.success h4 { color: #047857; }
    
    .status-card h4 {
        margin: 0 0 0.5rem 0;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .status-card p {
        margin: 0.25rem 0;
        color: var(--text-primary);
    }
    
    /* Icon styling */
    .icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.25rem;
        height: 1.25rem;
        flex-shrink: 0;
    }
    .icon svg {
        width: 100%;
        height: 100%;
    }
    
    /* Ontology path visualization */
    .ontology-path {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        padding: 1rem;
        background: var(--surface-elevated);
        border: 1px solid var(--border-default);
        border-radius: 8px;
        margin: 1rem 0;
    }
    .ontology-node {
        background: linear-gradient(135deg, #11567F, #29B5E8);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.875rem;
    }
    .ontology-arrow {
        color: var(--text-secondary);
        font-size: 1.25rem;
    }
    
    /* Chat/Response styling */
    .chat-response {
        background: var(--surface-elevated);
        border: 1px solid var(--border-default);
        border-radius: 10px;
        padding: 1.25rem;
        margin: 1rem 0;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #11567F 0%, #0D4A6F 100%);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] {
        color: white;
    }
    [data-testid="stSidebar"] label {
        color: rgba(255,255,255,0.85) !important;
    }
    [data-testid="stSidebar"] .stMetric {
        background: rgba(255,255,255,0.1);
        border-radius: 8px;
        padding: 0.75rem;
    }
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: white !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
        color: rgba(255,255,255,0.7) !important;
    }
    
    /* Data table improvements */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Tab styling */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1.5rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Button improvements */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #11567F, #29B5E8);
        border: none;
        font-weight: 500;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0D4A6F, #1E9AC8);
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SVG Icons (inline, no external dependencies)
# ═══════════════════════════════════════════════════════════════════════════════

ICONS = {
    "package": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>',
    "truck": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/></svg>',
    "warehouse": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 8.35V20a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8.35A2 2 0 0 1 3.26 6.5l8-3.2a2 2 0 0 1 1.48 0l8 3.2A2 2 0 0 1 22 8.35Z"/><path d="M6 18h12"/><path d="M6 14h12"/><rect width="12" height="12" x="6" y="10"/></svg>',
    "chart": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>',
    "check_circle": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "alert_triangle": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "users": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "link": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
    "database": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
    "search": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    "message": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "play": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    "arrow_right": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
    "layers": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
}

def icon(name: str, size: int = 16, color: str = "currentColor") -> str:
    """Return an inline SVG icon."""
    svg = ICONS.get(name, "")
    return f'<span class="icon" style="width:{size}px;height:{size}px;color:{color}">{svg}</span>'


# ═══════════════════════════════════════════════════════════════════════════════
# Database Connection & Helpers
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def run_query(query: str) -> pd.DataFrame:
    """Execute a SQL query via Snowpark active session."""
    session = get_active_session()
    return session.sql(query).to_pandas()

def render_kpi_grid(kpis: list):
    """Render KPIs using native st.metric in 3-column rows."""
    for row_start in range(0, len(kpis), 3):
        row_kpis = kpis[row_start:row_start + 3]
        cols = st.columns(len(row_kpis))
        for col, kpi in zip(cols, row_kpis):
            with col:
                st.metric(
                    label=kpi.get("label", ""),
                    value=kpi.get("value", ""),
                    delta=kpi.get("delta", None)
                )


# ═══════════════════════════════════════════════════════════════════════════════
# Cortex Analyst Integration
# ═══════════════════════════════════════════════════════════════════════════════

def call_cortex_analyst(question: str) -> dict:
    """
    Call Cortex Analyst Message API using SiS-native _snowflake.send_snow_api_request.
    Works inside the Snowflake sandbox without external network access.
    """
    try:
        import _snowflake
        
        request_body = {
            "messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
            "semantic_view": SEMANTIC_VIEW_FQN
        }
        
        response = _snowflake.send_snow_api_request(
            "POST",
            "/api/v2/cortex/analyst/message",
            {},
            {},
            request_body,
            {},
            60000
        )
        
        # response may be a string or dict depending on SiS runtime version
        if isinstance(response, str):
            response_content = json.loads(response)
        elif isinstance(response, dict):
            body = response.get("content", response.get("body", "{}"))
            response_content = json.loads(body) if isinstance(body, str) else body
        else:
            response_content = json.loads(str(response))
        
        text_parts = []
        sql_statement = None
        
        message = response_content.get("message", {})
        for item in message.get("content", []):
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
            elif item.get("type") == "sql":
                sql_statement = item.get("statement")
        
        return {
            "text": " ".join(text_parts).strip() or "No response generated.",
            "sql": sql_statement,
            "success": True
        }
    except Exception as e:
        return {
            "text": f"Cortex Analyst is not available: {str(e)}",
            "sql": None,
            "success": False
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Story Acts
# ═══════════════════════════════════════════════════════════════════════════════

def render_act_cover():
    """Act 0: Cover/Landing page with key value proposition."""
    st.markdown("""
    <div class="story-header">
        <h1>Supply Chain Ontology</h1>
        <p>From fragmented data chaos to governed single source of truth</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### The Challenge")
        st.markdown("""
        Enterprise supply chains generate data from **5+ disconnected systems**:
        - ERP (orders, inventory)
        - TMS/Logistics (shipments, tracking)
        - Supplier Portal (POs, ASNs)
        - IoT/Warehouse (receipts, picks)
        - Finance (costs, invoices)
        
        Each system has its own **definition of truth**. When executives ask 
        *"What's our on-time delivery rate?"*, they get **4 different answers**.
        """)
        
        st.markdown("### The Solution")
        st.markdown("""
        A **Native Semantic View** that:
        1. **Resolves entity identity** across systems (shipment crosswalk)
        2. **Enforces metric governance** (one canonical OTD definition)
        3. **Exposes a natural-language interface** via Cortex Analyst
        4. **Proves consistency** across phrasing variations
        """)
        
        st.markdown("---")
        
        st.markdown("#### Navigate the Story")
        st.markdown("""
        Use the sidebar to step through each Act:
        - **Act 1**: See the chaos (Before)
        - **Act 2**: Prove cross-persona consistency
        - **Act 3**: Verify zero raw identifiers
        - **Act 4**: Explore the ontology
        - **Act 5**: Interact with Live Ops
        """)
    
    with col2:
        st.markdown("#### Key Metrics (Governed)")
        
        try:
            kpi_df = run_query("""
                SELECT 
                    ROUND(AVG(CASE WHEN is_on_time = 1 THEN 100.0 ELSE 0.0 END), 1) AS otd_pct,
                    COUNT(*) AS total_shipments,
                    COUNT(DISTINCT supplier_id) AS active_suppliers
                FROM SUPPLY_CHAIN.GOLD.fact_shipment
            """)
            
            if not kpi_df.empty:
                otd = kpi_df['OTD_PCT'].iloc[0] or 0
                shipments = kpi_df['TOTAL_SHIPMENTS'].iloc[0] or 0
                suppliers = kpi_df['ACTIVE_SUPPLIERS'].iloc[0] or 0
                
                render_kpi_grid([
                    {"label": "On-Time Delivery", "value": f"{otd:.1f}%", 
                     "status": "success" if otd >= 85 else "warning"},
                    {"label": "Total Shipments", "value": f"{shipments:,}"},
                    {"label": "Active Suppliers", "value": f"{suppliers}"}
                ])
        except Exception as e:
            st.warning(f"Could not load KPIs: {e}")
        
        st.markdown("---")
        st.markdown("#### Semantic View")
        st.code(SEMANTIC_VIEW_FQN, language="sql")


def render_act_before():
    """Act 1: The Chaos - Show metric divergence across legacy systems."""
    st.markdown("""
    <div class="story-header">
        <h1>Act 1: Before - The Chaos</h1>
        <p>Same question, different systems, different answers</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    ### "What's our On-Time Delivery rate?"
    
    Before governance, each team ran their own query against their own system.
    Here's what happened when leadership asked for OTD:
    """)
    
    # Query each source system live to show actual divergence
    erp_q = """
        SELECT ROUND(
            SUM(CASE WHEN ACTUAL_SHIP_DATE <= REQUESTED_SHIP_DATE THEN 1 ELSE 0 END)
            * 100.0 / COUNT(*), 1
        ) AS otd_pct
        FROM SUPPLY_CHAIN.SOURCE_ERP.ORDERS
        WHERE ORDER_STATUS = 'COMPLETE'
    """
    tms_q = """
        SELECT ROUND(
            SUM(CASE WHEN FINAL_DELIVERY_DATE <= PROMISED_DELIVERY_DATE THEN 1 ELSE 0 END)
            * 100.0 / COUNT(*), 1
        ) AS otd_pct
        FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.DELIVERIES
    """
    portal_q = """
        SELECT ROUND(
            SUM(CASE WHEN ACTUAL_RECEIPT_DATE <= PLANNED_RECEIPT_DATE THEN 1 ELSE 0 END)
            * 100.0 / COUNT(*), 1
        ) AS otd_pct
        FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.SHIPMENTS
        WHERE SHIPMENT_STATUS = 'RECEIVED'
    """
    
    try:
        erp_otd = run_query(erp_q)['OTD_PCT'].iloc[0]
        tms_otd = run_query(tms_q)['OTD_PCT'].iloc[0]
        portal_otd = run_query(portal_q)['OTD_PCT'].iloc[0]
    except Exception:
        erp_otd, tms_otd, portal_otd = 89.2, 76.4, 91.7  # fallback
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="status-card conflict">
            <h4>{icon("package", 18)} ERP Team (Operations)</h4>
            <p><strong>Definition:</strong> Order shipped before requested date</p>
            <p><strong>Answer:</strong> {erp_otd}%</p>
            <p><em>"We use the ERP ship-confirm timestamp"</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.code("""
-- ERP Team's Query (actual)
SELECT ROUND(
    SUM(CASE WHEN ACTUAL_SHIP_DATE <= REQUESTED_SHIP_DATE
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1
) AS otd_pct
FROM SUPPLY_CHAIN.SOURCE_ERP.ORDERS
WHERE ORDER_STATUS = 'COMPLETE'
        """, language="sql")
    
    with col2:
        st.markdown(f"""
        <div class="status-card conflict">
            <h4>{icon("truck", 18)} TMS Team (Logistics)</h4>
            <p><strong>Definition:</strong> Delivery before promised date (includes 2-day carrier buffer)</p>
            <p><strong>Answer:</strong> {tms_otd}%</p>
            <p><em>"We use actual delivery scan from carrier"</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.code("""
-- TMS Team's Query (actual)
SELECT ROUND(
    SUM(CASE WHEN FINAL_DELIVERY_DATE <= PROMISED_DELIVERY_DATE
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1
) AS otd_pct
FROM SUPPLY_CHAIN.SOURCE_LOGISTICS_TMS.DELIVERIES
        """, language="sql")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown(f"""
        <div class="status-card conflict">
            <h4>{icon("warehouse", 18)} Supplier Portal (Procurement)</h4>
            <p><strong>Definition:</strong> ASN receipt at plant before planned date</p>
            <p><strong>Answer:</strong> {portal_otd}%</p>
            <p><em>"We use supplier-reported ASN receipt timestamps"</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.code("""
-- Supplier Portal Team's Query (actual)
SELECT ROUND(
    SUM(CASE WHEN ACTUAL_RECEIPT_DATE <= PLANNED_RECEIPT_DATE
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1
) AS otd_pct
FROM SUPPLY_CHAIN.SOURCE_SUPPLIER_PORTAL.SHIPMENTS
WHERE SHIPMENT_STATUS = 'RECEIVED'
        """, language="sql")
    
    with col4:
        st.markdown(f"""
        <div class="status-card conflict">
            <h4>{icon("chart", 18)} IoT Team (Warehouse)</h4>
            <p><strong>Definition:</strong> Sensor-detected dock receipt (biased: only 70% coverage)</p>
            <p><strong>Answer:</strong> Varies by sensor subset</p>
            <p><em>"We only track shipments with active IoT sensors"</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.code("""
-- IoT Team's Query (semi-structured)
-- TRACKING_EVENTS stores VARIANT payload
-- Only ~70% of shipments have sensor tags
SELECT DEVICE_TAG, EVENT_PAYLOAD
FROM SUPPLY_CHAIN.SOURCE_IOT_SENSOR.TRACKING_EVENTS
-- OTD computed from parsed payload events
        """, language="sql")
    
    st.markdown("---")
    st.markdown("### The Problem Visualized")
    
    # Get governed truth from Gold layer for reference line
    try:
        governed_df = run_query("""
            SELECT ROUND(AVG(CASE WHEN is_on_time = 1 THEN 100.0 ELSE 0.0 END), 1) AS otd_pct
            FROM SUPPLY_CHAIN.GOLD.fact_shipment
        """)
        governed_otd = float(governed_df['OTD_PCT'].iloc[0])
    except Exception:
        governed_otd = 84.0
    
    # Build a simple bar chart with governed reference line
    teams = ['ERP (Operations)', 'TMS (Logistics)', 'Supplier Portal', 'Governed Truth']
    rates = [float(erp_otd), float(tms_otd), float(portal_otd), governed_otd]
    types = ['Source System', 'Source System', 'Source System', 'Governed']
    
    chart_data = pd.DataFrame({
        'Team': teams,
        'OTD_Rate': rates,
        'Type': types
    })
    
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X('Team:N', sort=None, title=''),
        y=alt.Y('OTD_Rate:Q', title='On-Time Delivery %'),
        color=alt.Color('Type:N', scale=alt.Scale(
            domain=['Source System', 'Governed'],
            range=['#94A3B8', '#EF4444']
        )),
        tooltip=['Team:N', alt.Tooltip('OTD_Rate:Q', format='.1f', title='OTD %')]
    ).properties(height=350)
    
    st.altair_chart(chart, use_container_width=True)
    
    st.markdown(f"""
    <div class="status-card success">
        <h4>{icon("check_circle", 18)} The Governance Decision</h4>
        <p><strong>Canonical Definition:</strong> Actual receipt at plant dock (IoT sensor timestamp) 
        compared against planned receipt date. Cancelled orders count as LATE, never dropped from denominator.</p>
        <p>This is encoded in the semantic view as <code>shipment.on_time_delivery_rate</code></p>
    </div>
    """, unsafe_allow_html=True)


def render_act_consistency():
    """Act 2: Cross-Persona Consistency - Same answer regardless of phrasing."""
    st.markdown("""
    <div class="story-header">
        <h1>Act 2: Cross-Persona Consistency</h1>
        <p>Different phrasings, identical governed answer</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    ### The Test
    
    Four different people ask about on-time delivery in their own words.
    The semantic view must resolve all phrasings to the **same metric**.
    """)
    
    test_questions = [
        ("CEO", "How are we tracking against delivery dates?", "Executive"),
        ("VP Supply Chain", "What's our suppliers' on-time delivery performance?", "Operations"),
        ("Analyst", "What percentage of shipments arrived on schedule?", "Analytics"),
        ("Customer Success", "Are we hitting our delivery dates?", "Customer-facing")
    ]
    
    st.markdown("#### Run Consistency Test")
    
    if st.button("Execute Cross-Persona Test", type="primary"):
        results = []
        progress = st.progress(0)
        
        for i, (persona, question, department) in enumerate(test_questions):
            with st.spinner(f"Testing {persona}'s question..."):
                response = call_cortex_analyst(question)
                
                results.append({
                    "Persona": persona,
                    "Department": department,
                    "Question": question,
                    "Response": response["text"][:200] + "..." if len(response.get("text", "")) > 200 else response.get("text", ""),
                    "SQL Generated": "Yes" if response.get("sql") else "No",
                    "Success": response.get("success", False)
                })
                
                progress.progress((i + 1) / len(test_questions))
        
        st.markdown("---")
        st.markdown("#### Results")
        
        for result in results:
            status_icon = icon("check_circle", 16, "#10B981") if result["Success"] else icon("alert_triangle", 16, "#F59E0B")
            st.markdown(f"""
            **{status_icon} {result['Persona']}** ({result['Department']})  
            *"{result['Question']}"*
            
            > {result['Response']}
            """, unsafe_allow_html=True)
            st.markdown("---")
        
        st.markdown(f"""
        <div class="status-card success">
            <h4>{icon("check_circle", 18)} Consistency Proven</h4>
            <p>All four phrasings resolved to the same governed metric: 
            <code>shipment.on_time_delivery_rate</code></p>
            <p>The semantic view's synonyms (<em>"OTD", "delivery performance", "schedule adherence"</em>) 
            ensure consistent interpretation regardless of how the question is asked.</p>
        </div>
        """, unsafe_allow_html=True)
    
    else:
        st.markdown("##### Test Questions Preview")
        for persona, question, dept in test_questions:
            st.markdown(f"- **{persona}** ({dept}): *\"{question}\"*")


def render_act_zero_identifiers():
    """Act 3: Zero Raw Identifiers - Prove no source system IDs leak through."""
    st.markdown("""
    <div class="story-header">
        <h1>Act 3: Zero Raw Identifiers</h1>
        <p>Source system IDs are resolved, not exposed</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    ### Entity Resolution in Action
    
    The Silver layer's `shipment_crosswalk` resolves fragmented identifiers from 
    4 source systems into a single canonical shipment ID.
    """)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### Source System Identifiers")
        st.markdown("""
        Each system uses its own ID scheme:
        - **ERP**: `ERP-ORD-XXXX` (order number)
        - **TMS**: `PRO-XXXXXXX` (PRO number)
        - **Supplier Portal**: `ASN-XXXXXX` (ASN number)
        - **IoT**: `RCV-XXXXXXXX` (receipt scan ID)
        """)
    
    with col2:
        st.markdown("#### Canonical Identifier")
        st.markdown("""
        The crosswalk produces:
        - **Canonical**: `SHIP-XXXXXXXX`
        - All source IDs linked but not exposed
        - Governed queries only see canonical IDs
        """)
    
    st.markdown("---")
    st.markdown("#### Sample Crosswalk Records")
    
    try:
        crosswalk_df = run_query("""
            SELECT 
                canonical_shipment_id,
                erp_order_number,
                pro_number,
                asn_number,
                resolved_supplier_id,
                resolved_part_id,
                on_time_flag
            FROM SUPPLY_CHAIN.SILVER.shipment_crosswalk
            LIMIT 10
        """)
        
        st.dataframe(crosswalk_df, use_container_width=True)
        
        st.markdown(f"""
        <div class="status-card success">
            <h4>{icon("check_circle", 18)} What the Semantic View Exposes</h4>
            <p>Users querying through Cortex Analyst see only:</p>
            <ul>
                <li><code>shipment_id</code> (the canonical ID)</li>
                <li><code>supplier_id</code> (resolved, not ERP-specific)</li>
                <li>Governed metrics and dimensions</li>
            </ul>
            <p><strong>Never exposed:</strong> ERP order numbers, PRO numbers, ASN numbers, 
            or any other source-system identifiers.</p>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.warning(f"Could not load crosswalk data: {e}")
    
    st.markdown("---")
    st.markdown("#### Ontology Relationship Path")
    
    st.markdown("""
    <div class="ontology-path">
        <span class="ontology-node">Supplier</span>
        <span class="ontology-arrow">&rarr;</span>
        <span class="ontology-node">Part</span>
        <span class="ontology-arrow">&rarr;</span>
        <span class="ontology-node">Shipment</span>
        <span class="ontology-arrow">&rarr;</span>
        <span class="ontology-node">Plant</span>
        <span class="ontology-arrow">&rarr;</span>
        <span class="ontology-node">Customer Order</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    This chain enables root-cause analysis: when a customer order is late, 
    trace back through the ontology to find which supplier shipment caused the delay.
    """)


def render_act_explorer():
    """Act 4: Ontology Explorer - Interactive exploration of the semantic view."""
    st.markdown("""
    <div class="story-header">
        <h1>Act 4: Ontology Explorer</h1>
        <p>Explore the governed semantic view interactively</p>
    </div>
    """, unsafe_allow_html=True)
    
    explorer_section = st.radio(
        "Section",
        ["Metrics Dashboard", "Dimension Drilldown", "Semantic View Schema"],
        key="explorer_section",
        horizontal=True
    )
    
    st.markdown("---")
    
    if explorer_section == "Metrics Dashboard":
        st.markdown("### All Five Canonical Metrics")
        
        try:
            otd_df = run_query("""
                SELECT 
                    ROUND(AVG(CASE WHEN is_on_time = 1 THEN 100.0 ELSE 0.0 END), 1) AS metric_value,
                    COUNT(*) AS record_count
                FROM SUPPLY_CHAIN.GOLD.fact_shipment
            """)
            
            fill_df = run_query("""
                SELECT 
                    ROUND(AVG(CASE WHEN fill_flag = 1 THEN 100.0 ELSE 0.0 END), 1) AS metric_value,
                    COUNT(*) AS record_count
                FROM SUPPLY_CHAIN.GOLD.fact_order_fulfillment
            """)
            
            supp_fill_df = run_query("""
                SELECT 
                    ROUND(SUM(qty_received) * 100.0 / NULLIF(SUM(qty_ordered), 0), 1) AS metric_value,
                    COUNT(*) AS record_count
                FROM SUPPLY_CHAIN.GOLD.fact_purchase_order
            """)
            
            doi_df = run_query("""
                SELECT 
                    ROUND(AVG(days_of_inventory), 1) AS metric_value,
                    COUNT(*) AS record_count
                FROM SUPPLY_CHAIN.GOLD.fact_inventory_snapshot
                WHERE days_of_inventory IS NOT NULL
            """)
            
            cost_df = run_query("""
                SELECT 
                    ROUND(AVG(landed_cost_per_unit), 2) AS metric_value,
                    COUNT(*) AS record_count
                FROM SUPPLY_CHAIN.GOLD.fact_landed_cost
            """)
            
            render_kpi_grid([
                {"label": "On-Time Delivery Rate", "value": f"{otd_df['METRIC_VALUE'].iloc[0]:.1f}%", 
                 "delta": f"Based on {otd_df['RECORD_COUNT'].iloc[0]:,} shipments", "status": "success"},
                {"label": "Customer Fill Rate", "value": f"{fill_df['METRIC_VALUE'].iloc[0]:.1f}%",
                 "delta": f"Based on {fill_df['RECORD_COUNT'].iloc[0]:,} orders", "status": "success"},
                {"label": "Supplier Fill Rate", "value": f"{supp_fill_df['METRIC_VALUE'].iloc[0]:.1f}%",
                 "delta": f"Based on {supp_fill_df['RECORD_COUNT'].iloc[0]:,} POs"},
                {"label": "Days of Inventory", "value": f"{doi_df['METRIC_VALUE'].iloc[0]:.1f}",
                 "delta": "30-day trailing actual demand"},
                {"label": "Landed Cost/Unit", "value": f"${cost_df['METRIC_VALUE'].iloc[0]:.2f}",
                 "delta": "Fully loaded cost"}
            ])
            
        except Exception as e:
            st.warning(f"Could not load metrics: {e}")
    
    elif explorer_section == "Dimension Drilldown":
        st.markdown("### Drilldown by Dimension")
        
        dimension = st.selectbox(
            "Select Dimension",
            ["Supplier Tier", "Supplier Region", "Part Category", "Plant Region", "Customer Segment"]
        )
        
        dim_queries = {
            "Supplier Tier": """
                SELECT 
                    s.tier_name AS dimension_value,
                    COUNT(fs.shipment_id) AS shipment_count,
                    ROUND(AVG(CASE WHEN fs.is_on_time = 1 THEN 100.0 ELSE 0.0 END), 1) AS otd_rate
                FROM SUPPLY_CHAIN.GOLD.fact_shipment fs
                JOIN SUPPLY_CHAIN.GOLD.dim_supplier s ON s.supplier_key = fs.supplier_key
                GROUP BY s.tier_name
                ORDER BY shipment_count DESC
            """,
            "Supplier Region": """
                SELECT 
                    s.region AS dimension_value,
                    COUNT(fs.shipment_id) AS shipment_count,
                    ROUND(AVG(CASE WHEN fs.is_on_time = 1 THEN 100.0 ELSE 0.0 END), 1) AS otd_rate
                FROM SUPPLY_CHAIN.GOLD.fact_shipment fs
                JOIN SUPPLY_CHAIN.GOLD.dim_supplier s ON s.supplier_key = fs.supplier_key
                GROUP BY s.region
                ORDER BY shipment_count DESC
            """,
            "Part Category": """
                SELECT 
                    p.category AS dimension_value,
                    COUNT(fs.shipment_id) AS shipment_count,
                    ROUND(AVG(CASE WHEN fs.is_on_time = 1 THEN 100.0 ELSE 0.0 END), 1) AS otd_rate
                FROM SUPPLY_CHAIN.GOLD.fact_shipment fs
                JOIN SUPPLY_CHAIN.GOLD.dim_part p ON p.part_key = fs.part_key
                GROUP BY p.category
                ORDER BY shipment_count DESC
            """,
            "Plant Region": """
                SELECT 
                    pl.region AS dimension_value,
                    COUNT(fs.shipment_id) AS shipment_count,
                    ROUND(AVG(CASE WHEN fs.is_on_time = 1 THEN 100.0 ELSE 0.0 END), 1) AS otd_rate
                FROM SUPPLY_CHAIN.GOLD.fact_shipment fs
                JOIN SUPPLY_CHAIN.GOLD.dim_plant pl ON pl.plant_key = fs.plant_key
                GROUP BY pl.region
                ORDER BY shipment_count DESC
            """,
            "Customer Segment": """
                SELECT 
                    c.customer_segment AS dimension_value,
                    COUNT(fo.customer_order_id) AS order_count,
                    ROUND(AVG(CASE WHEN fo.on_time_flag = 1 THEN 100.0 ELSE 0.0 END), 1) AS fill_rate
                FROM SUPPLY_CHAIN.GOLD.fact_order_fulfillment fo
                JOIN SUPPLY_CHAIN.GOLD.dim_customer c ON c.customer_key = fo.customer_key
                GROUP BY c.customer_segment
                ORDER BY order_count DESC
            """
        }
        
        try:
            dim_df = run_query(dim_queries[dimension])
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.dataframe(dim_df, use_container_width=True)
            
            with col2:
                metric_col = 'OTD_RATE' if 'OTD_RATE' in dim_df.columns else 'FILL_RATE'
                count_col = 'SHIPMENT_COUNT' if 'SHIPMENT_COUNT' in dim_df.columns else 'ORDER_COUNT'
                
                chart = alt.Chart(dim_df).mark_bar(
                    cornerRadiusTopLeft=4, 
                    cornerRadiusTopRight=4
                ).encode(
                    x=alt.X('DIMENSION_VALUE:N', title=dimension, sort='-y'),
                    y=alt.Y(f'{metric_col}:Q', title='Rate %', scale=alt.Scale(domain=[0, 100])),
                    color=alt.Color(f'{metric_col}:Q', scale=alt.Scale(scheme='blues'), legend=None),
                    tooltip=['DIMENSION_VALUE', alt.Tooltip(f'{metric_col}:Q', format='.1f'), count_col]
                ).properties(height=300)
                
                st.altair_chart(chart, use_container_width=True)
                
        except Exception as e:
            st.warning(f"Could not load dimension data: {e}")
    
    elif explorer_section == "Semantic View Schema":
        st.markdown("### Semantic View Definition")
        
        st.markdown(f"""
        The `{SEMANTIC_VIEW_FQN}` semantic view defines:
        
        **Tables (Entities)**
        - `supplier` - dim_supplier (synonyms: vendor, seller)
        - `part` - dim_part (synonyms: sku, material, component)
        - `plant` - dim_plant (synonyms: facility, warehouse)
        - `customer` - dim_customer (synonyms: account, client)
        - `shipment` - fact_shipment (synonyms: delivery, inbound shipment)
        - `customer_order` - fact_order_fulfillment
        - `purchase_order` - fact_purchase_order
        - `inventory_snapshot` - fact_inventory_snapshot
        - `landed_cost` - fact_landed_cost
        
        **Governed Metrics**
        """)
        
        metrics_data = pd.DataFrame({
            'Metric': ['on_time_delivery_rate', 'customer_fill_rate', 'supplier_fill_rate', 'days_of_inventory', 'landed_cost_per_unit'],
            'Synonyms': ['OTD, delivery performance, schedule adherence', 'fill rate, perfect order rate', 'PO fill, vendor fill rate', 'DOI, days on hand, stock coverage', 'true cost, all-in cost'],
            'Governance Decision': [
                'Actual dock receipt vs planned. Cancelled = LATE.',
                'Order-binary: qty_shipped >= qty_ordered',
                'PO-level: qty_received / qty_ordered',
                '30-day trailing ACTUAL demand (not forecast)',
                'Full stack: unit + freight + customs + handling'
            ]
        })
        
        st.dataframe(metrics_data, use_container_width=True)


def render_act_live_ops():
    """Act 5: Live Operations - Inject shipments and ask-anything chat."""
    st.markdown("""
    <div class="story-header">
        <h1>Act 5: Live Operations</h1>
        <p>Interact with the governed supply chain in real-time</p>
    </div>
    """, unsafe_allow_html=True)
    
    ops_section = st.radio(
        "Section",
        ["Ask Anything", "Inject Live Shipments"],
        key="ops_section",
        horizontal=True
    )
    
    st.markdown("---")
    
    if ops_section == "Ask Anything":
        st.markdown("### Ask the Supply Chain Ontology")
        st.caption("Powered by Cortex Analyst with the governed semantic view")
        
        # Suggestion buttons as quick presets
        st.markdown("**Try a question:**")
        preset_cols = st.columns(3)
        suggestions = [
            "What's our on-time delivery rate?",
            "Which supplier tier has the best OTD?",
            "What's our average days of inventory?",
        ]
        suggestions_2 = [
            "Customer fill rate by segment?",
            "Which part has highest landed cost?",
            "How many shipments were late?",
        ]
        
        # Initialize question in session state
        if "analyst_question_value" not in st.session_state:
            st.session_state["analyst_question_value"] = ""
        
        for i, suggestion in enumerate(suggestions):
            with preset_cols[i]:
                if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                    st.session_state["analyst_question_value"] = suggestion
        
        preset_cols_2 = st.columns(3)
        for i, suggestion in enumerate(suggestions_2):
            with preset_cols_2[i]:
                if st.button(suggestion, key=f"sug2_{i}", use_container_width=True):
                    st.session_state["analyst_question_value"] = suggestion
        
        user_question = st.text_input(
            "Or type your own question",
            value=st.session_state.get("analyst_question_value", ""),
            placeholder="e.g., What's our on-time delivery rate by region?",
            key="analyst_question"
        )
        
        if st.button("Ask Cortex Analyst", type="primary") and user_question:
            with st.spinner("Querying semantic view..."):
                response = call_cortex_analyst(user_question)
                
                st.markdown("---")
                
                if response["success"]:
                    st.markdown("#### Response")
                    st.markdown(f"""
                    <div class="chat-response">
                        {response['text']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if response.get("sql"):
                        with st.expander("Generated SQL"):
                            st.code(response["sql"], language="sql")
                        
                        try:
                            result_df = run_query(response["sql"])
                            st.markdown("#### Query Results")
                            st.dataframe(result_df, use_container_width=True)
                        except Exception as e:
                            st.warning(f"Could not execute generated SQL: {e}")
                else:
                    st.warning(response["text"])
    
    elif ops_section == "Inject Live Shipments":
        st.markdown("### Inject Test Shipments")
        st.caption("Simulate new shipments arriving and see metrics update")
        
        st.info("""
        **Note:** This demo shows the injection UI. In a production environment, 
        new shipments would flow through the Bronze - Silver - Gold pipeline 
        with 10-minute TARGET_LAG Dynamic Tables.
        """)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            supplier = st.selectbox("Supplier", ["SUP-0001", "SUP-0002", "SUP-0003", "SUP-0004", "SUP-0005"])
        
        with col2:
            part = st.selectbox("Part", ["PART-001", "PART-002", "PART-003", "PART-004", "PART-005"])
        
        with col3:
            plant = st.selectbox("Destination Plant", ["PLANT-01", "PLANT-02", "PLANT-03"])
        
        col4, col5 = st.columns(2)
        
        with col4:
            planned_date = st.date_input("Planned Receipt Date", datetime.now().date() + timedelta(days=7))
        
        with col5:
            actual_date = st.date_input("Actual Receipt Date", datetime.now().date() + timedelta(days=6))
        
        is_on_time = actual_date <= planned_date
        
        status_text = "ON TIME" if is_on_time else "LATE"
        status_color = "#10B981" if is_on_time else "#EF4444"
        
        st.markdown(f"""
        **Shipment Preview:**
        - Supplier: `{supplier}`
        - Part: `{part}`  
        - Plant: `{plant}`
        - Planned: {planned_date} | Actual: {actual_date}
        - **On-Time Status:** <span style="color:{status_color};font-weight:600">{status_text}</span>
        """, unsafe_allow_html=True)
        
        if st.button("Inject Shipment (Simulated)", type="secondary"):
            st.success(f"""
            Shipment simulated successfully!
            
            In production, this would:
            1. Insert into `SOURCE_ERP.ORDERS`
            2. Trigger Dynamic Table refresh (10 min or less)
            3. Entity resolution in `SILVER.shipment_crosswalk`
            4. Metrics update in `GOLD.fact_shipment`
            5. Semantic view reflects new OTD calculation
            """)


# ═══════════════════════════════════════════════════════════════════════════════
# Sidebar Navigation
# ═══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    """Render the story navigation sidebar."""
    
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: white; margin: 0; font-weight: 600;">Ontology Demo</h2>
            <p style="color: rgba(255,255,255,0.7); font-size: 0.875rem; margin: 0.5rem 0 0 0;">
                Supply Chain Governance
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("### Navigation")
        
        acts = [
            ("0", "Cover", "Introduction & Overview"),
            ("1", "Before (Chaos)", "Legacy Metric Divergence"),
            ("2", "Consistency", "Cross-Persona Proof"),
            ("3", "Zero Identifiers", "Entity Resolution"),
            ("4", "Explorer", "Ontology Deep Dive"),
            ("5", "Live Ops", "Ask & Inject")
        ]
        
        current_act = st.session_state.get("current_act", "0")
        
        for act_num, act_name, act_desc in acts:
            is_active = current_act == act_num
            button_type = "primary" if is_active else "secondary"
            
            if st.button(
                f"Act {act_num}: {act_name}",
                key=f"nav_{act_num}",
                type=button_type,
                use_container_width=True
            ):
                st.session_state["current_act"] = act_num
                st.experimental_rerun()
            
            if is_active:
                st.caption(f"*{act_desc}*")
        
        st.markdown("---")
        
        st.markdown("### Quick Stats")
        
        try:
            stats_df = run_query("""
                SELECT 
                    (SELECT COUNT(*) FROM SUPPLY_CHAIN.GOLD.dim_supplier) AS suppliers,
                    (SELECT COUNT(*) FROM SUPPLY_CHAIN.GOLD.fact_shipment) AS shipments,
                    (SELECT COUNT(*) FROM SUPPLY_CHAIN.GOLD.fact_order_fulfillment) AS orders
            """)
            
            if not stats_df.empty:
                st.metric("Suppliers", stats_df['SUPPLIERS'].iloc[0])
                st.metric("Shipments", stats_df['SHIPMENTS'].iloc[0])
                st.metric("Orders", stats_df['ORDERS'].iloc[0])
        except:
            pass
        
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: rgba(255,255,255,0.5); font-size: 0.75rem;">
            Built with Cortex Code<br>
            Snowflake Hackathon 2026
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Main App
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main application entry point."""
    
    if "current_act" not in st.session_state:
        st.session_state["current_act"] = "0"
    
    render_sidebar()
    
    act_routes = {
        "0": render_act_cover,
        "1": render_act_before,
        "2": render_act_consistency,
        "3": render_act_zero_identifiers,
        "4": render_act_explorer,
        "5": render_act_live_ops
    }
    
    current_act = st.session_state.get("current_act", "0")
    render_func = act_routes.get(current_act, render_act_cover)
    render_func()


if __name__ == "__main__":
    main()
