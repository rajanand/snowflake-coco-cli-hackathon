"""Theme engine: webfonts, CSS custom properties, icons, capability detection.

Two responsibilities:

1. ``inject()`` emits one ``<style>`` block per run containing the @font-face
   declarations, the active theme's tokens as CSS custom properties, and the
   component styles. Because every colour is a custom property sourced from
   ``tokens.py``, switching theme is a matter of re-emitting the block - and
   the Altair specs read the same dict, so charts can never drift from the page.

2. ``capabilities()`` feature-detects the Streamlit APIs the UI would like to
   use. The deployed object's runtime was verified as a container runtime
   (Streamlit 1.50+), but detecting rather than assuming means the app also
   renders correctly on the legacy warehouse runtime instead of raising
   AttributeError mid-demo.
"""

from __future__ import annotations

import inspect

import streamlit as st

from lib import tokens as T


# ---------------------------------------------------------------------------
# Capability detection
# ---------------------------------------------------------------------------

@st.cache_resource
def capabilities() -> dict:
    """Detect optional Streamlit APIs once per container."""

    def has(name: str) -> bool:
        return hasattr(st, name)

    caps = {
        "segmented_control": has("segmented_control"),
        "pills": has("pills"),
        "fragment": has("fragment"),
        "tabs": has("tabs"),
        "rerun": has("rerun"),
        "chat_input": has("chat_input"),
        "popover": has("popover"),
        "status": has("status"),
        "toast": has("toast"),
        "divider": has("divider"),
        "version": st.__version__,
    }

    try:
        caps["metric_border"] = "border" in inspect.signature(st.metric).parameters
    except (TypeError, ValueError):
        caps["metric_border"] = False

    return caps


def rerun() -> None:
    """Rerun on either runtime (st.rerun is absent on older Streamlit)."""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def _font_faces() -> str:
    return "\n".join(
        f"""@font-face{{font-family:'{fam}';src:url('{url}') format('woff2');
font-weight:{wt};font-style:normal;font-display:swap;}}"""
        for fam, wt, url in T.FONT_FACES
    )


def _vars(c: dict) -> str:
    """Emit the token set as CSS custom properties."""
    pairs = [f"--ge-{k.replace('_', '-')}:{v}" for k, v in c.items() if k != "name"]
    pairs.append(f"--ge-shadow:{T.SHADOW[c['name']]}")
    pairs.append(f"--ge-font:{T.FONT_SANS}")
    pairs.append(f"--ge-mono:{T.FONT_MONO}")
    pairs.append(f"--ge-max:{T.MAX_WIDTH}")
    for k, v in T.RADIUS.items():
        pairs.append(f"--ge-r-{k}:{v}")
    return ":root{" + ";".join(pairs) + "}"


def _t(key: str) -> str:
    """Expand a type token into CSS declarations."""
    s = T.TYPE[key]
    return (
        f"font-size:{s['size']};font-weight:{s['weight']};"
        f"letter-spacing:{s['tracking']};line-height:{s['leading']}"
    )


def inject(theme_name: str) -> dict:
    """Inject the stylesheet for ``theme_name`` and return its token dict."""
    c = T.theme(theme_name)
    dark = c["name"] == "dark"

    css = f"""
{_font_faces()}
{_vars(c)}

/* ---------- base ---------- */
html, body, [class*="css"], [data-testid="stAppViewContainer"] {{
  font-family: var(--ge-font);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-feature-settings: 'cv11' 1, 'ss01' 1;
}}
[data-testid="stAppViewContainer"], [data-testid="stApp"] {{
  background: var(--ge-bg);
  color: var(--ge-text);
}}
/* Streamlit's own header bar would sit above our composition. */
[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stToolbar"] {{ right: 8px; }}
#MainMenu, footer, [data-testid="stStatusWidget"] {{ visibility: hidden; }}

[data-testid="stMainBlockContainer"], .block-container {{
  max-width: var(--ge-max);
  padding: {T.SPACE['6']} {T.SPACE['6']} {T.SPACE['10']};
}}

/* ---------- sidebar (behind-the-scenes trace log) ---------- */
/* Wider than Streamlit's cramped default so labels, SQL and prose all get
   room to breathe; min-width only, so the user can still drag it wider. */
[data-testid="stSidebar"] {{
  background: var(--ge-surface);
  border-right: 1px solid var(--ge-hairline);
  min-width: 380px !important;
}}
[data-testid="stSidebar"] > div {{
  padding-top: {T.SPACE['5']};
  padding-left: {T.SPACE['5']};
  padding-right: {T.SPACE['5']};
}}
/* Sidebar's own vertical rhythm - looser than the dense main content. */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: {T.SPACE['4']}; }}
[data-testid="stSidebar"] [data-testid="stExpander"] {{ background: var(--ge-surface-raised); }}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {{
  font-size: 13px; padding: {T.SPACE['3']} {T.SPACE['4']};
}}
[data-testid="stSidebar"] [data-testid="stExpanderDetails"] {{
  padding: {T.SPACE['1']} {T.SPACE['4']} {T.SPACE['3']};
}}
[data-testid="stSidebar"] [data-testid="stCode"], [data-testid="stSidebar"] pre {{
  font-size: 12.5px !important;
  line-height: 1.6 !important;
}}
[data-testid="stSidebar"] [data-testid="stCode"] pre {{
  padding: {T.SPACE['3']} {T.SPACE['4']} !important;
}}
/* Text set inside the trace log reads larger and looser than the compact
   .ge-small default used elsewhere, so entries don't feel stacked on top of
   one another. */
[data-testid="stSidebar"] .ge-eyebrow {{ font-size: 11.5px; margin-bottom: {T.SPACE['1']}; }}
[data-testid="stSidebar"] .ge-small {{ font-size: 13.5px; line-height: 1.6; }}
[data-testid="stSidebar"] .ge-mono {{ font-size: 12px; line-height: 1.6; }}
[data-testid="stSidebar"] .ge-badge {{ padding: 5px 12px; font-size: 11px; }}
[data-testid="stSidebar"] .stButton {{ margin-bottom: {T.SPACE['2']}; }}
[data-testid="stSidebar"] hr.ge-rule {{ margin: {T.SPACE['5']} 0; }}
[data-testid="stSidebarCollapseButton"] button {{ color: var(--ge-muted) !important; }}

/* Tighten Streamlit's default vertical rhythm; our own spacing governs. */
[data-testid="stVerticalBlock"] {{ gap: {T.SPACE['3']}; }}
[data-testid="stElementContainer"] {{ margin: 0; }}

h1, h2, h3, h4, h5, h6 {{ color: var(--ge-text); font-family: var(--ge-font); }}
p, li, span, div {{ color: var(--ge-text); }}
code, pre, kbd {{ font-family: var(--ge-mono) !important; }}
a {{ color: var(--ge-accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* ---------- typography primitives ---------- */
.ge-eyebrow {{
  {_t('micro')};
  text-transform: uppercase;
  color: var(--ge-muted);
  margin: 0 0 {T.SPACE['2']};
}}
.ge-display {{ {_t('display')}; color: var(--ge-text); margin: 0; }}
.ge-title   {{ {_t('title')};   color: var(--ge-text); margin: 0; }}
.ge-sub     {{ {_t('subtitle')};color: var(--ge-text-dim); margin: 0; }}
.ge-body    {{ {_t('body')};    color: var(--ge-text-dim); margin: 0; }}
.ge-small   {{ {_t('small')};   color: var(--ge-muted); margin: 0; }}
.ge-mono    {{ {_t('mono')};    font-family: var(--ge-mono); color: var(--ge-text-dim); }}

/* ---------- the question just asked ---------- */
/* The literal question is the thing being contrasted (silo vs. governed), so
   it gets its own large, quoted treatment - not just a line inside a card. */
.ge-question {{
  font-size: 30px; font-weight: 600; letter-spacing: -0.018em; line-height: 1.3;
  font-style: italic; color: var(--ge-text); margin: 0;
}}

/* ---------- surfaces ---------- */
.ge-card {{
  background: var(--ge-surface);
  border: 1px solid var(--ge-hairline);
  border-radius: var(--ge-r-md);
  padding: {T.SPACE['5']} {T.SPACE['5']};
}}
.ge-card-quiet {{ background: transparent; }}
.ge-rule {{ height: 1px; background: var(--ge-hairline); border: 0; margin: {T.SPACE['6']} 0; }}

/* ---------- the governed number ---------- */
/* Typeset rather than rendered through st.metric: tabular figures, tight
   tracking, and the accent reserved for this element alone. */
.ge-hero-num {{
  {_t('hero')};
  font-variant-numeric: tabular-nums;
  color: var(--ge-accent);
  margin: 0;
}}
.ge-hero-unit {{ font-size: 26px; font-weight: 500; letter-spacing: -0.01em; }}

/* Legacy answers are deliberately recessive. */
.ge-legacy-num {{
  {_t('display')};
  font-variant-numeric: tabular-nums;
  color: var(--ge-noise);
  margin: 0;
}}

/* ---------- provenance receipt ---------- */
.ge-receipt {{
  font-family: var(--ge-mono);
  {_t('mono_sm')};
  background: {'rgba(255,255,255,0.022)' if dark else 'rgba(15,23,42,0.022)'};
  border: 1px solid var(--ge-hairline);
  border-radius: var(--ge-r-md);
  padding: {T.SPACE['4']} {T.SPACE['5']};
  color: var(--ge-text-dim);
}}
.ge-receipt-row {{
  display: flex; gap: {T.SPACE['4']};
  padding: {T.SPACE['2']} 0;
  border-bottom: 1px dashed var(--ge-hairline);
}}
.ge-receipt-row:last-child {{ border-bottom: 0; }}
.ge-receipt-key {{
  color: var(--ge-muted); text-transform: uppercase;
  letter-spacing: 0.07em; font-size: 10px;
  min-width: 128px; flex-shrink: 0; padding-top: 2px;
}}
.ge-receipt-val {{ color: var(--ge-text); word-break: break-word; }}
.ge-receipt-val.accent {{ color: var(--ge-accent); }}

/* ---------- badges ---------- */
.ge-badge {{
  display: inline-flex; align-items: center; gap: 6px;
  {_t('micro')}; text-transform: uppercase;
  padding: 4px 10px; border-radius: var(--ge-r-pill);
  border: 1px solid var(--ge-hairline-strong); color: var(--ge-muted);
}}
.ge-badge.governed {{
  color: var(--ge-accent); border-color: var(--ge-accent);
  background: var(--ge-accent-wash);
}}
.ge-badge.ungoverned {{ color: var(--ge-warn); border-color: var(--ge-warn); }}

/* ---------- native widget chrome ---------- */
/* config.toml sets a static dark base, so light mode must restyle Streamlit's
   own widgets explicitly or they would stay dark against a light page. */
.stButton > button, .stDownloadButton > button {{
  font-family: var(--ge-font); font-weight: 500; font-size: 13.5px;
  border-radius: var(--ge-r-sm);
  border: 1px solid var(--ge-hairline-strong);
  background: var(--ge-surface-raised);
  color: var(--ge-text);
  transition: border-color .14s ease, background .14s ease;
}}
.stButton > button:hover {{ border-color: var(--ge-accent); color: var(--ge-accent); }}
.stButton > button[kind="primary"] {{
  background: var(--ge-accent); border-color: var(--ge-accent);
  color: {'#04141C' if dark else '#FFFFFF'}; font-weight: 600;
}}
.stButton > button[kind="primary"]:hover {{
  background: var(--ge-accent-dim); border-color: var(--ge-accent-dim);
  color: {'#04141C' if dark else '#FFFFFF'};
}}

[data-baseweb="select"] > div, [data-baseweb="input"] > div,
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {{
  background: var(--ge-surface) !important;
  border-color: var(--ge-hairline) !important;
  color: var(--ge-text) !important;
  font-family: var(--ge-font) !important;
  border-radius: var(--ge-r-sm) !important;
}}
[data-baseweb="popover"] li {{ font-family: var(--ge-font); }}

/* Segmented control / pills */
[data-testid="stSegmentedControl"] button,
[data-testid="stPills"] button {{
  font-family: var(--ge-font) !important; font-weight: 500;
  border-radius: var(--ge-r-sm) !important;
  background: var(--ge-surface) !important;
  border: 1px solid var(--ge-hairline) !important;
  color: var(--ge-muted) !important;
}}
[data-testid="stSegmentedControl"] button[aria-checked="true"],
[data-testid="stPills"] button[aria-checked="true"] {{
  background: var(--ge-accent-wash) !important;
  border-color: var(--ge-accent) !important;
  color: var(--ge-accent) !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
  gap: {T.SPACE['5']}; border-bottom: 1px solid var(--ge-hairline);
  background: transparent;
}}
.stTabs [data-baseweb="tab"] {{
  font-family: var(--ge-font); font-size: 13px; font-weight: 500;
  letter-spacing: 0.01em; color: var(--ge-muted);
  background: transparent; padding: {T.SPACE['3']} 0;
}}
.stTabs [aria-selected="true"] {{ color: var(--ge-accent) !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: var(--ge-accent); }}
.stTabs [data-baseweb="tab-border"] {{ background: transparent; }}

/* Chat input */
[data-testid="stChatInput"] {{
  background: var(--ge-surface); border: 1px solid var(--ge-hairline);
  border-radius: var(--ge-r-md);
}}
[data-testid="stChatInput"] textarea {{
  font-family: var(--ge-font) !important; font-size: 15px !important;
  color: var(--ge-text) !important;
}}
[data-testid="stChatInput"]:focus-within {{ border-color: var(--ge-accent); }}

/* Dataframes */
[data-testid="stDataFrame"], [data-testid="stTable"] {{
  border: 1px solid var(--ge-hairline); border-radius: var(--ge-r-md);
  overflow: hidden;
}}
[data-testid="stDataFrame"] * {{ font-family: var(--ge-font) !important; font-size: 12.5px !important; }}

/* Code blocks read as evidence, not decoration. */
[data-testid="stCode"], pre {{
  background: {'rgba(255,255,255,0.03)' if dark else 'rgba(15,23,42,0.035)'} !important;
  border: 1px solid var(--ge-hairline) !important;
  border-radius: var(--ge-r-md) !important;
}}
[data-testid="stCode"] code, pre code {{ font-size: 12.5px !important; }}

/* Expanders */
[data-testid="stExpander"] {{
  border: 1px solid var(--ge-hairline) !important;
  border-radius: var(--ge-r-md) !important;
  background: var(--ge-surface);
}}
[data-testid="stExpander"] summary {{ font-family: var(--ge-font); font-size: 13px; color: var(--ge-text-dim); }}

/* Metrics */
[data-testid="stMetric"] {{
  background: var(--ge-surface); border: 1px solid var(--ge-hairline);
  border-radius: var(--ge-r-md); padding: {T.SPACE['4']};
}}
[data-testid="stMetricLabel"] * {{
  {_t('micro')}; text-transform: uppercase; color: var(--ge-muted) !important;
}}
[data-testid="stMetricValue"] {{
  font-family: var(--ge-font) !important; font-weight: 600 !important;
  font-variant-numeric: tabular-nums; color: var(--ge-text) !important;
  letter-spacing: -0.02em;
}}

/* Alerts, toned down to fit the surface. */
[data-testid="stAlert"] {{
  border-radius: var(--ge-r-md); border: 1px solid var(--ge-hairline);
  font-family: var(--ge-font); font-size: 13px;
}}

/* Spinner + progress adopt the accent. */
[data-testid="stSpinner"] > div {{ border-top-color: var(--ge-accent) !important; }}
[data-testid="stProgress"] > div > div > div {{ background: var(--ge-accent); }}

/* Charts inherit the page background rather than painting their own. */
[data-testid="stVegaLiteChart"], .vega-embed {{ background: transparent !important; }}
.vega-embed summary {{ display: none; }}
"""

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    return c


# ---------------------------------------------------------------------------
# Icons
# ---------------------------------------------------------------------------
# One family, 1.5px stroke, currentColor. Inline so nothing is fetched at
# runtime (the CSP blocks external scripts, and icon fonts are a liability).

_ICON_PATHS = {
    "split": '<path d="M16 3h5v5"/><path d="M8 3H3v5"/><path d="M12 22V12"/><path d="M21 3l-9 9-9-9"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
    "route": '<circle cx="6" cy="19" r="3"/><circle cx="18" cy="5" r="3"/><path d="M9 19h5a4 4 0 0 0 0-8H9a4 4 0 0 1 0-8h2"/>',
    "alert": '<path d="M12 9v4"/><path d="M12 17h.01"/><circle cx="12" cy="12" r="9"/>',
    "layers": '<path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M6.3 17.7l-1.4 1.4M19.1 4.9l-1.4 1.4"/>',
    "moon": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z"/>',
    "arrow_right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
}


def icon(name: str, size: int = 15, color: str = "currentColor") -> str:
    """Return an inline SVG string for ``name``."""
    path = _ICON_PATHS.get(name)
    if not path:
        return ""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.5" stroke-linecap="round" '
        f'stroke-linejoin="round" style="vertical-align:-2px;flex-shrink:0">{path}</svg>'
    )


def eyebrow(text: str, icon_name: str | None = None) -> str:
    """Small uppercase section label, optionally icon-led."""
    glyph = f"{icon(icon_name, 12)} " if icon_name else ""
    return (
        f'<div class="ge-eyebrow" style="display:flex;align-items:center;gap:6px">'
        f"{glyph}<span>{text}</span></div>"
    )
