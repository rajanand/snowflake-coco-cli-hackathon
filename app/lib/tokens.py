"""Design tokens for the Governed Answer Engine.

A single source of truth for colour, type and spacing, shared by the injected
CSS and the Altair chart specs. Charts read the same dict the CSS does, so a
theme switch can never leave the charts out of sync with the page.

Design intent
-------------
Restraint carries the argument. The accent colour is reserved *exclusively*
for the governed answer; legacy answers are rendered in a deliberately
low-contrast "noise" tone so that the eye resolves the governed number first
and reads the rest as disagreement. `warn` appears exactly once, on the
divergence annotation. Nothing else competes.
"""

# --------------------------------------------------------------------------
# Colour
# --------------------------------------------------------------------------

DARK = {
    "name": "dark",
    "bg": "#0B0E14",
    "surface": "#12161F",
    "surface_raised": "#171D28",
    "hairline": "rgba(255,255,255,0.09)",
    "hairline_strong": "rgba(255,255,255,0.16)",
    "text": "#E6EAF2",
    "text_dim": "#A7B1C2",
    "muted": "#7C8798",
    # Reserved for governed truth only.
    "accent": "#29B5E8",
    "accent_dim": "#1B8FBC",
    "accent_wash": "rgba(41,181,232,0.10)",
    # Legacy / ungoverned answers. Intentionally recessive.
    "noise": "#4A5567",
    "noise_dim": "#333C4B",
    "noise_wash": "rgba(124,135,152,0.13)",
    # Divergence callout. Used once.
    "warn": "#F0806C",
    "ok": "#4FD1A5",
    # Chart furniture
    "grid": "rgba(255,255,255,0.055)",
    "axis": "#5A6575",
}

LIGHT = {
    "name": "light",
    "bg": "#FAFAF9",
    "surface": "#FFFFFF",
    "surface_raised": "#F4F5F7",
    "hairline": "rgba(15,23,42,0.11)",
    "hairline_strong": "rgba(15,23,42,0.20)",
    "text": "#0F172A",
    "text_dim": "#3B475C",
    "muted": "#64748B",
    "accent": "#0E7FA8",
    "accent_dim": "#0B6688",
    "accent_wash": "rgba(14,127,168,0.09)",
    "noise": "#94A3B8",
    "noise_dim": "#C2CBD6",
    "noise_wash": "rgba(100,116,139,0.12)",
    "warn": "#DC2626",
    "ok": "#0F9268",
    "grid": "rgba(15,23,42,0.07)",
    "axis": "#8A97A8",
}

THEMES = {"dark": DARK, "light": LIGHT}


def theme(name: str) -> dict:
    """Return a token set, defaulting to dark (the demo default)."""
    return THEMES.get(name, DARK)


# --------------------------------------------------------------------------
# Typography
# --------------------------------------------------------------------------
# Geist for UI, Geist Mono for anything that is an identifier, a SQL
# fragment, or evidence. Negative tracking on large sizes only - Geist is
# already tight at text sizes and over-tightening hurts legibility.

FONT_SANS = "'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
FONT_MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

TYPE = {
    # The governed number. Typeset, not st.metric-ed.
    "hero":    {"size": "64px", "weight": 600, "tracking": "-0.035em", "leading": "1.0"},
    "display": {"size": "34px", "weight": 600, "tracking": "-0.022em", "leading": "1.15"},
    "title":   {"size": "20px", "weight": 600, "tracking": "-0.012em", "leading": "1.3"},
    "subtitle":{"size": "16px", "weight": 500, "tracking": "-0.006em", "leading": "1.45"},
    "body":    {"size": "14px", "weight": 400, "tracking": "0",        "leading": "1.55"},
    "small":   {"size": "12.5px", "weight": 400, "tracking": "0",      "leading": "1.5"},
    # Section eyebrows / labels.
    "micro":   {"size": "11px", "weight": 500, "tracking": "0.085em",  "leading": "1.4"},
    "mono":    {"size": "13px", "weight": 400, "tracking": "0",        "leading": "1.6"},
    "mono_sm": {"size": "11.5px", "weight": 400, "tracking": "0",      "leading": "1.55"},
}

# --------------------------------------------------------------------------
# Space, radius, elevation
# --------------------------------------------------------------------------
# 4px base scale. One shadow token, used sparingly - hairline borders are the
# primary means of separation, which keeps the surface calm.

SPACE = {"0": "0", "1": "4px", "2": "8px", "3": "12px", "4": "16px",
         "5": "20px", "6": "24px", "7": "32px", "8": "40px", "9": "56px", "10": "72px"}

RADIUS = {"sm": "6px", "md": "10px", "lg": "14px", "pill": "999px"}

SHADOW = {
    "dark": "0 1px 2px rgba(0,0,0,0.5), 0 8px 28px rgba(0,0,0,0.34)",
    "light": "0 1px 2px rgba(15,23,42,0.05), 0 8px 24px rgba(15,23,42,0.07)",
}

MAX_WIDTH = "1180px"

# --------------------------------------------------------------------------
# Webfonts
# --------------------------------------------------------------------------
# Loaded with @font-face rather than Streamlit's [[theme.fontFaces]] so the
# result does not depend on the Streamlit version (fontFaces needs 1.45+).
# The SiS Content Security Policy blocks external scripts and stylesheets but
# explicitly permits fonts from any HTTPS domain. Every URL below was verified
# to return content-type font/woff2.

_FS = "https://cdn.jsdelivr.net/npm/@fontsource"

FONT_FACES = [
    ("Geist", 400, f"{_FS}/geist-sans@5/files/geist-sans-latin-400-normal.woff2"),
    ("Geist", 500, f"{_FS}/geist-sans@5/files/geist-sans-latin-500-normal.woff2"),
    ("Geist", 600, f"{_FS}/geist-sans@5/files/geist-sans-latin-600-normal.woff2"),
    ("Geist Mono", 400, f"{_FS}/geist-mono@5/files/geist-mono-latin-400-normal.woff2"),
]
