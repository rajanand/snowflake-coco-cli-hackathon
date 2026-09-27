"""Builds docs/hackathon-deck.pptx for the Snowflake CoCo CLI Hackathon submission.

Design system (from the slides.com "Our Solar System" reference deck study):
  - Alternating black / cream slide backgrounds.
  - Small tracked ALL-CAPS "kicker" label above every headline.
  - Large bold headline, single blue accent color used sparingly.
  - Footer breadcrumb (bottom-left) + "N / TOTAL" counter (bottom-right) +
    a thin blue progress bar along the bottom edge on every slide.
  - No external image assets -- every visual is native pptx shapes/text so the
    file is fully self-contained and portable.

Every fact/number in this file is sourced from a specific file in this repo --
see the inline "source:" comments above each slide function.

Run: python docs/build_hackathon_deck.py
"""

from __future__ import annotations

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

BLACK = RGBColor(0x0A, 0x0A, 0x0A)
CREAM = RGBColor(0xF5, 0xF5, 0xF0)
ACCENT = RGBColor(0x2D, 0x5B, 0xFF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x11, 0x11, 0x11)
GREY_ON_BLACK = RGBColor(0x9A, 0x9A, 0x9A)
GREY_ON_CREAM = RGBColor(0x6B, 0x6B, 0x66)
LINE_ON_BLACK = RGBColor(0x33, 0x33, 0x33)
LINE_ON_CREAM = RGBColor(0xD8, 0xD8, 0xD2)

FONT = "Arial"
FONT_BLACK = "Arial"  # bold weight used via .bold = True (Arial Black not guaranteed cross-platform)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

BREADCRUMB = "SUPPLY CHAIN ONTOLOGY"
TOTAL_SLIDES = 17

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
BLANK = prs.slide_layouts[6]


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def new_slide(bg: RGBColor):
    slide = prs.slides.add_slide(BLANK)
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = bg
    return slide


def _set_no_line(shape):
    shape.line.fill.background()


def textbox(slide, left, top, width, height, word_wrap=True):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = word_wrap
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    return tb, tf


def set_run(run, text, size, color, bold=False, font=FONT, spacing=None, italic=False):
    run.text = text
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font
    if spacing is not None:
        rPr = run._r.get_or_add_rPr()
        rPr.set("spc", str(spacing))


def kicker(slide, text, left, top, on_black=True, width=Inches(10)):
    _, tf = textbox(slide, left, top, width, Inches(0.35))
    p = tf.paragraphs[0]
    r = p.add_run()
    color = WHITE if on_black else INK
    set_run(r, text.upper(), 12, color, bold=True, spacing=180)
    return tf


def headline(slide, text, left, top, on_black=True, size=40, width=Inches(11)):
    _, tf = textbox(slide, left, top, width, Inches(1.6))
    color = WHITE if on_black else INK
    lines = text.split("\n")
    p = tf.paragraphs[0]
    r = p.add_run()
    set_run(r, lines[0], size, color, bold=True)
    p.line_spacing = 1.0
    for line in lines[1:]:
        p2 = tf.add_paragraph()
        r2 = p2.add_run()
        set_run(r2, line, size, color, bold=True)
        p2.line_spacing = 1.0
    return tf


def body_text(slide, text, left, top, width, height, on_black=True, size=14,
              color=None, bold=False, align=PP_ALIGN.LEFT):
    _, tf = textbox(slide, left, top, width, height)
    default_color = (GREY_ON_BLACK if on_black else GREY_ON_CREAM) if color is None else color
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    set_run(r, text, size, default_color, bold=bold)
    return tf


def hline(slide, left, top, width, on_black=True, weight=1.0):
    ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, left, top, left + width, top)
    ln.line.color.rgb = LINE_ON_BLACK if on_black else LINE_ON_CREAM
    ln.line.width = Pt(weight)
    return ln


def footer(slide, page, on_black=True, breadcrumb=BREADCRUMB):
    color = GREY_ON_BLACK if on_black else GREY_ON_CREAM
    _, tf = textbox(slide, Inches(0.6), Inches(7.02), Inches(6), Inches(0.3))
    p = tf.paragraphs[0]
    r = p.add_run()
    set_run(r, breadcrumb, 9.5, color, bold=True, spacing=100)

    _, tf2 = textbox(slide, Inches(11.0), Inches(7.02), Inches(1.75), Inches(0.3))
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.RIGHT
    r2 = p2.add_run()
    set_run(r2, f"{page} / {TOTAL_SLIDES}", 9.5, color, bold=True)

    # progress bar track (faint) + fill (accent)
    track = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(7.42), SLIDE_W, Inches(0.08))
    track.fill.solid()
    track.fill.fore_color.rgb = LINE_ON_BLACK if on_black else LINE_ON_CREAM
    _set_no_line(track)
    fill_w = int(SLIDE_W * (page / TOTAL_SLIDES))
    fill_bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(7.42), fill_w, Inches(0.08))
    fill_bar.fill.solid()
    fill_bar.fill.fore_color.rgb = ACCENT
    _set_no_line(fill_bar)


def rect(slide, left, top, width, height, color=None, line_color=None, line_w=1.0, round_=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if round_ else MSO_SHAPE.RECTANGLE
    sh = slide.shapes.add_shape(shape_type, left, top, width, height)
    if color is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = color
    if line_color is None:
        _set_no_line(sh)
    else:
        sh.line.color.rgb = line_color
        sh.line.width = Pt(line_w)
    sh.shadow.inherit = False
    return sh


def badge_pill(slide, text, left, top, on_black=True, accent=False):
    w = Inches(0.16 * len(text) + 0.35)
    h = Inches(0.32)
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, w, h)
    sh.adjustments[0] = 0.5
    if accent:
        sh.fill.solid()
        sh.fill.fore_color.rgb = ACCENT
        sh.line.fill.background()
        text_color = WHITE
    else:
        sh.fill.background()
        sh.line.color.rgb = WHITE if on_black else INK
        sh.line.width = Pt(1.0)
        text_color = WHITE if on_black else INK
    sh.shadow.inherit = False
    tf = sh.text_frame
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    set_run(r, text.upper(), 9, text_color, bold=True, spacing=60)
    return sh, w


def circle_num(slide, n, left, top, d=Inches(0.5), on_black=True):
    sh = slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top, d, d)
    sh.fill.background()
    sh.line.color.rgb = WHITE if on_black else INK
    sh.line.width = Pt(1.25)
    sh.shadow.inherit = False
    tf = sh.text_frame
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    set_run(r, str(n), 16, WHITE if on_black else INK, bold=True)
    return sh


# ---------------------------------------------------------------------------
# Slide-type layout builders
# ---------------------------------------------------------------------------

def stat_grid(slide, stats, left, top, col_w, row_h, cols=2, on_black=True):
    """stats: list of (label, value, caption) tuples."""
    for i, (label, value, caption) in enumerate(stats):
        c = i % cols
        r = i // cols
        x = left + c * col_w
        y = top + r * row_h
        hline(slide, x, y, Inches(1.9), on_black=on_black, weight=1.25)
        body_text(slide, label.upper(), x, y + Inches(0.08), col_w - Inches(0.3), Inches(0.3),
                   on_black=on_black, size=10.5, bold=True,
                   color=(GREY_ON_BLACK if on_black else GREY_ON_CREAM))
        _, tf = textbox(slide, x, y + Inches(0.38), col_w - Inches(0.2), Inches(0.75))
        p = tf.paragraphs[0]
        rr = p.add_run()
        set_run(rr, value, 34, WHITE if on_black else INK, bold=True)
        body_text(slide, caption, x, y + Inches(1.05), col_w - Inches(0.35), Inches(0.55),
                   on_black=on_black, size=11)


def card_grid(slide, cards, left, top, card_w, gap, height=Inches(4.3), on_black=True):
    """cards: list of dicts with keys: title, meta(list of lines)."""
    x = left
    for card in cards:
        vline = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x, top, x, top + height)
        vline.line.color.rgb = LINE_ON_BLACK if on_black else LINE_ON_CREAM
        vline.line.width = Pt(1.0)
        cx = x + Inches(0.28)
        cw = card_w - Inches(0.5)
        body_text(slide, card.get("eyebrow", ""), cx, top, cw, Inches(0.28), on_black=on_black,
                   size=10, bold=True, color=(GREY_ON_BLACK if on_black else GREY_ON_CREAM))
        _, tf = textbox(slide, cx, top + Inches(0.32), cw, Inches(0.65))
        p = tf.paragraphs[0]
        rr = p.add_run()
        set_run(rr, card["title"], 19, WHITE if on_black else INK, bold=True)
        y = top + Inches(1.0)
        for line in card["meta"]:
            _, tfm = textbox(slide, cx, y, cw, Inches(0.55))
            pm = tfm.paragraphs[0]
            rm = pm.add_run()
            bold = line.startswith("**")
            txt = line.replace("**", "")
            set_run(rm, txt, 11.5, WHITE if on_black else INK, bold=bold)
            pm.line_spacing = 1.15
            y += Inches(0.5) if len(txt) < 45 else Inches(0.75)
        x += card_w


def list_rows(slide, rows, left, top, width, row_h=Inches(0.92), on_black=True, numbered=False):
    """rows: list of dicts: name, desc, right (value/badge text), badge(optional)."""
    y = top
    for i, row in enumerate(rows):
        if numbered:
            circle_num(slide, i + 1, left, y + Inches(0.06), d=Inches(0.42), on_black=on_black)
            text_x = left + Inches(0.62)
        else:
            text_x = left
        text_w = width - Inches(2.3) - (Inches(0.62) if numbered else 0)
        _, tf = textbox(slide, text_x, y, text_w, Inches(0.35))
        p = tf.paragraphs[0]
        r = p.add_run()
        set_run(r, row["name"], 15.5, WHITE if on_black else INK, bold=True)
        _, tf2 = textbox(slide, text_x, y + Inches(0.36), text_w, Inches(0.5))
        p2 = tf2.paragraphs[0]
        r2 = p2.add_run()
        set_run(r2, row["desc"], 11, GREY_ON_BLACK if on_black else GREY_ON_CREAM)
        p2.line_spacing = 1.1
        if row.get("right"):
            _, tf3 = textbox(slide, left + width - Inches(2.1), y + Inches(0.02), Inches(2.0), Inches(0.5))
            p3 = tf3.paragraphs[0]
            p3.alignment = PP_ALIGN.RIGHT
            r3 = p3.add_run()
            set_run(r3, row["right"], 20, ACCENT, bold=True)
        if i < len(rows) - 1:
            hline(slide, left, y + row_h - Inches(0.1), width, on_black=on_black, weight=0.75)
        y += row_h


# ---------------------------------------------------------------------------
# Slide builders (one function per slide, source noted)
# ---------------------------------------------------------------------------

def slide_01_cover():
    # source: README.md title + intro paragraph
    s = new_slide(BLACK)
    kicker(s, "Snowflake CoCo CLI Hackathon 2026 — GCC Edition", Inches(0.7), Inches(2.55))
    headline(s, "Supply Chain Ontology &\nGoverned Conversational Analytics",
             Inches(0.7), Inches(2.95), size=42, width=Inches(11.9))
    body_text(s, "One governed semantic layer that gets Planning, Procurement, and Logistics "
                 "to the same number — every time, no matter how the question is worded.",
              Inches(0.7), Inches(4.75), Inches(9.5), Inches(0.8), size=15)
    # decorative accent rule
    rect(s, Inches(0.7), Inches(2.35), Inches(1.4), Pt(3), color=ACCENT)
    body_text(s, "100% SYNTHETIC DATA  ·  BUILT END-TO-END WITH COCO  ·  DATABASE: SUPPLY_CHAIN",
              Inches(0.7), Inches(6.35), Inches(10), Inches(0.35), size=10.5, bold=True,
              color=GREY_ON_BLACK)
    footer(s, 1)


def slide_02_problem():
    # source: README.md "The problem, in one table"
    s = new_slide(CREAM)
    kicker(s, "The Problem", Inches(0.7), Inches(0.55), on_black=False)
    headline(s, "One question, five answers.", Inches(0.7), Inches(0.92), on_black=False, size=34)
    body_text(s, "The Sun and everything... no — supply chain data is scattered across ERP, "
                 "logistics, supplier, and IoT systems with inconsistent definitions, so the same "
                 "question yields different answers across teams.",
              Inches(0.7), Inches(1.75), Inches(11.6), Inches(0.6), on_black=False, size=13.5)
    stats = [
        ("Source systems", "5", "ERP, TMS, Supplier Portal, IoT sensors, Finance — each with its own definition."),
        ("Divergent OTD answers", "4", "89.4% / 91.3% / 78.6% / a biased IoT sample — before governance."),
        ("Shared definition", "0", "No canonical metric existed before this project."),
        ("Governed truth", "1", "One Semantic View, one number, every persona."),
    ]
    stat_grid(s, stats, Inches(0.7), Inches(2.75), Inches(5.85), Inches(1.85), cols=2, on_black=False)
    footer(s, 2, on_black=False)


def slide_03_approach():
    # source: README.md "Architecture" section
    s = new_slide(BLACK)
    kicker(s, "Our Approach", Inches(0.7), Inches(0.55))
    headline(s, "Ontology \u2192 Semantic View \u2192 Governed Answer", Inches(0.7), Inches(0.92), size=30,
             width=Inches(12))
    stages = [
        ("Source systems", "5 fragmented\nSOURCE_* schemas"),
        ("Bronze", "Unified raw\nlanding zone"),
        ("Silver", "Entity resolution\n+ crosswalk"),
        ("Gold", "9-entity\ndimensional model"),
        ("Semantic View", "Governed metrics\n+ synonyms"),
        ("Agents + App", "Router, guardrails,\nStreamlit"),
    ]
    n = len(stages)
    top = Inches(3.0)
    box_w = Inches(1.85)
    box_h = Inches(1.5)
    gap = (Inches(12.0) - box_w * n) / (n - 1)
    x = Inches(0.7)
    centers = []
    for i, (title, sub) in enumerate(stages):
        box = rect(s, x, top, box_w, box_h, color=None, line_color=WHITE, line_w=1.25, round_=True)
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.1)
        tf.margin_right = Inches(0.1)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        set_run(r, title, 13, WHITE, bold=True)
        for line in sub.split("\n"):
            p2 = tf.add_paragraph()
            p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run()
            set_run(r2, line, 9.5, GREY_ON_BLACK)
        centers.append((x, x + box_w))
        x += box_w + gap
    # arrows between boxes
    mid_y = top + box_h / 2
    for i in range(n - 1):
        x1 = centers[i][1]
        x2 = centers[i + 1][0]
        arrow = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, mid_y, x2, mid_y)
        arrow.line.color.rgb = ACCENT
        arrow.line.width = Pt(1.5)
        line_elem = arrow.line._get_or_add_ln()
        tail = line_elem.makeelement(qn('a:tailEnd'), {'type': 'triangle', 'w': 'med', 'len': 'med'})
        line_elem.append(tail)
    body_text(s, "Five fragmented systems land into one Bronze zone, get resolved into a single "
                 "canonical Silver layer, modeled dimensionally in Gold, exposed as a governed "
                 "Semantic View, and consumed by a multi-agent router and Streamlit app.",
              Inches(0.7), Inches(5.1), Inches(11.6), Inches(0.9), size=13)
    footer(s, 3)


def slide_04_fragmentation():
    # source: sql/00_source_schemas/README.md, README.md problem table
    s = new_slide(CREAM)
    kicker(s, "Phase 0 — Source Systems", Inches(0.7), Inches(0.5), on_black=False)
    headline(s, "Five systems, five genuine flaws.", Inches(0.7), Inches(0.87), on_black=False, size=30)
    body_text(s, "Built deliberately, not staged — every SOURCE_* table carries a KNOWN DATA "
                 "QUALITY ISSUE comment describing its specific real-world flaw.",
              Inches(0.7), Inches(1.55), Inches(11.6), Inches(0.4), on_black=False, size=12.5)
    cards = [
        {"eyebrow": "OPERATIONS", "title": "ERP", "meta": [
            "**89.4%** legacy OTD",
            "Ship-confirm before requested date.",
            "Excludes cancelled / backorder rows.",
        ]},
        {"eyebrow": "LOGISTICS", "title": "TMS", "meta": [
            "**91.3%** legacy OTD",
            "Delivery before promised date.",
            "2-day carrier buffer baked in.",
        ]},
        {"eyebrow": "PROCUREMENT", "title": "Supplier Portal", "meta": [
            "**78.6%** legacy OTD",
            "ASN receipt before planned date.",
            "Drops in-transit shipments.",
        ]},
        {"eyebrow": "WAREHOUSE", "title": "IoT Sensors", "meta": [
            "Biased sample",
            "Sensor-detected dock receipt.",
            "Only ~70% sensor coverage.",
        ]},
    ]
    card_grid(s, cards, Inches(0.7), Inches(2.3), Inches(2.9), 0, height=Inches(3.9), on_black=False)
    footer(s, 4, on_black=False)


def slide_05_entity_resolution():
    # source: sql/02_silver/README.md "Validated results (last run)"
    s = new_slide(BLACK)
    kicker(s, "Phase 2 — Silver", Inches(0.7), Inches(0.55))
    headline(s, "One shipment, four systems,\none identity.", Inches(0.7), Inches(0.95), size=32)
    body_text(s, "The shipment_crosswalk Dynamic Table resolves the same physical shipment across "
                 "ERP order, TMS delivery, Supplier Portal ASN, and IoT tracking tag into one "
                 "canonical_shipment_id — deterministic ID-core matching, not fuzzy guesswork.",
              Inches(0.7), Inches(2.15), Inches(6.6), Inches(1.2), size=13)
    facts = [
        ("800 / 800", "orders matched to a delivery and a shipment (100%)"),
        ("800 / 800", "supplier identity cross-system match (100%)"),
        ("560 / 800", "IoT tracking match rate — the genuine 70% sensor-coverage gap, carried through, not hidden"),
    ]
    y = Inches(3.55)
    for value, cap in facts:
        hline(s, Inches(0.7), y, Inches(6.3), weight=1.25)
        _, tf = textbox(s, Inches(0.7), y + Inches(0.08), Inches(2.2), Inches(0.55))
        p = tf.paragraphs[0]
        r = p.add_run()
        set_run(r, value, 26, WHITE, bold=True)
        body_text(s, cap, Inches(2.95), y + Inches(0.15), Inches(4.05), Inches(0.55), size=11)
        y += Inches(0.85)
    # big callout on right, gauge-like circle
    circ = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(8.3), Inches(2.2), Inches(4.2), Inches(4.2))
    circ.fill.background()
    circ.line.color.rgb = ACCENT
    circ.line.width = Pt(2.5)
    circ.shadow.inherit = False
    tf = circ.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    set_run(r, "100%", 46, WHITE, bold=True)
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    set_run(r2, "entity resolution\nacross 4 systems", 12, GREY_ON_BLACK)
    footer(s, 5)


def slide_06_ontology():
    # source: sql/04_semantic_view/README.md "Structural validation";
    # docs/architecture-and-er-diagram.html ER section
    s = new_slide(CREAM)
    kicker(s, "Phase 3\u20134 \u2014 Gold + Semantic View", Inches(0.7), Inches(0.5), on_black=False)
    headline(s, "9 entities, 10 relationships,\n5 governed metrics.", Inches(0.7), Inches(0.88),
             on_black=False, size=28)
    # entity chain (mirrors the challenge brief's own example)
    chain = ["Supplier", "Part", "Plant", "Shipment", "Order", "Customer"]
    x = Inches(0.7)
    y = Inches(2.35)
    w = Inches(1.75)
    h = Inches(0.55)
    gap = Inches(0.35)
    for i, name in enumerate(chain):
        box = rect(s, x, y, w, h, color=None, line_color=INK, line_w=1.25, round_=True)
        tf = box.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        set_run(r, name, 12, INK, bold=True)
        if i < len(chain) - 1:
            arrow = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x + w, y + h / 2, x + w + gap, y + h / 2)
            arrow.line.color.rgb = ACCENT
            arrow.line.width = Pt(1.5)
        x += w + gap
    body_text(s, "Plus Purchase Order, Inventory Snapshot, and Landed Cost — 9 semantic-view TABLES "
                 "total, each backed by a real GOLD dynamic table.",
              Inches(0.7), Inches(3.15), Inches(11.6), Inches(0.4), on_black=False, size=12)
    stats = [
        ("Semantic tables", "9", "supplier, part, plant, customer, shipment, orders, inventory, landed cost"),
        ("Relationships", "10", "every fact table joined back to its dimensions"),
        ("Canonical metrics", "5", "OTD, customer fill, supplier fill, DOI, landed cost/unit"),
        ("Dimensions", "5", "tier, region, category, segment, date hierarchy"),
    ]
    stat_grid(s, stats, Inches(0.7), Inches(4.0), Inches(5.85), Inches(1.35), cols=2, on_black=False)
    footer(s, 6, on_black=False)


def slide_07_metrics():
    # source: sql/04_semantic_view/README.md metric table
    s = new_slide(BLACK)
    kicker(s, "Governance", Inches(0.7), Inches(0.5))
    headline(s, "Business meaning, not column names.", Inches(0.7), Inches(0.88), size=30)
    rows = [
        {"name": "On-Time Delivery Rate", "right": "64.875%",
         "desc": "Plant-dock receipt vs. planned. Cancelled / overdue-in-transit always count as late, never dropped."},
        {"name": "Customer Fill Rate", "right": "90.800%",
         "desc": "Order-binary: qty_shipped \u2265 qty_ordered."},
        {"name": "Supplier Fill Rate", "right": "86.294%",
         "desc": "Received units / ordered units \u2014 deliberately distinct from customer fill rate."},
        {"name": "Days of Inventory", "right": "48.60d",
         "desc": "On-hand qty / 30-day trailing ACTUAL demand \u2014 not forecast, not $-based."},
        {"name": "Landed Cost / Unit", "right": "$251.68",
         "desc": "Unit cost + freight + customs + overhead, computed at shipment grain."},
    ]
    list_rows(s, rows, Inches(0.7), Inches(1.75), Inches(12.0), row_h=Inches(0.92))
    footer(s, 7)


def slide_08_legacy_vs_governed():
    # source: sql/10_workspace_artifact/README.md, sql/00_source_schemas/README.md
    s = new_slide(CREAM)
    kicker(s, "The Proof", Inches(0.7), Inches(0.5), on_black=False)
    headline(s, "Stricter, not just different.", Inches(0.7), Inches(0.88), on_black=False, size=32)
    body_text(s, "The governed On-Time Delivery answer is lower than every legacy answer \u2014 the "
                 "governance decision closes loopholes each source system used to look better than "
                 "reality, it doesn't split the difference.",
              Inches(0.7), Inches(1.65), Inches(11.6), Inches(0.55), on_black=False, size=13)
    otd = [("ERP", 89.4, False), ("TMS", 91.3, False), ("Portal", 78.6, False), ("Governed", 64.875, True)]
    base_x = Inches(0.9)
    base_y = Inches(5.15)
    max_w = Inches(10.8)
    max_val = 91.3
    for i, (label, val, is_gov) in enumerate(otd):
        bw = Emu(int(max_w * (val / max_val)))
        by = base_y - Inches(0.85) * i
        bh = Inches(0.62)
        bar = rect(s, base_x, by, bw, bh, color=(ACCENT if is_gov else RGBColor(0x22, 0x22, 0x22)))
        tf = bar.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        r = p.add_run()
        set_run(r, f"  {label}", 12, WHITE, bold=True)
        _, tfv = textbox(s, base_x + bw + Inches(0.12), by, Inches(1.5), bh)
        pv = tfv.paragraphs[0]
        pv.alignment = PP_ALIGN.LEFT
        rv = pv.add_run()
        set_run(rv, f"{val}%", 16, ACCENT if is_gov else INK, bold=True)
    body_text(s, "Fill Rate: Supplier PO 86.3% / Warehouse pick 87.7%  \u2192  Governed: Customer 90.8% / Supplier 86.294% (two distinct canonical measures)\n"
                 "Days of Inventory: Planning 40.1d / Finance 506.6d  \u2192  Governed: 48.6d\n"
                 "Landed Cost/Unit: Procurement $276.40 / Logistics $488.29  \u2192  Governed: $251.68",
              Inches(0.7), Inches(6.05), Inches(11.8), Inches(0.9), on_black=False, size=10.5)
    footer(s, 8, on_black=False)


def slide_09_agent_router():
    # source: agents/agent_router.py class structure
    s = new_slide(BLACK)
    kicker(s, "Phase 5 \u2014 Multi-Agent Router", Inches(0.7), Inches(0.5))
    headline(s, "One router, four specialist agents.", Inches(0.7), Inches(0.88), size=30)
    body_text(s, "A 5-intent classifier (standard, at_risk, what_if, root_cause, document_qa) routes "
                 "every question to the right sub-agent, behind shared PreQueryValidator / "
                 "PostQueryEnricher guardrail hooks.",
              Inches(0.7), Inches(1.62), Inches(11.6), Inches(0.5), size=12.5)
    rows = [
        {"name": "CortexAnalystClient", "desc": "Governed Q&A against the Semantic View \u2014 the \"standard\" intent."},
        {"name": "SimulationAgent", "desc": "Hand-written, parameterized SQL for \"what-if\" supplier-delay scenarios."},
        {"name": "EvidenceTraceAgent", "desc": "Root-cause trace from a late shipment back to its supplier."},
        {"name": "DocumentQAAgent", "desc": "Cortex Search over supplier contract PDFs for the \"document_qa\" intent."},
    ]
    list_rows(s, rows, Inches(0.7), Inches(2.5), Inches(12.0), row_h=Inches(0.95), numbered=True)
    footer(s, 9)


def slide_10_guardrails():
    # source: docs/hackathon-review-human.md section 8
    s = new_slide(CREAM)
    kicker(s, "Governance Judging Criterion", Inches(0.7), Inches(0.5), on_black=False)
    headline(s, "Fails safely, never fabricates.", Inches(0.7), Inches(0.88), on_black=False, size=30)
    cards = [
        {"eyebrow": "01", "title": "Constrained SQL", "meta": [
            "Hand-written, parameterized queries",
            "for what_if and root_cause \u2014",
            "no LLM-freeform SQL for high-stakes intents.",
        ]},
        {"eyebrow": "02", "title": "Vocabulary lock", "meta": [
            "Synonyms + metric comments in the",
            "Semantic View constrain the LLM to",
            "one canonical measure per concept.",
        ]},
        {"eyebrow": "03", "title": "PreQueryValidator", "meta": [
            "Blocks empty/oversized input and a",
            "FORBIDDEN_TERMS list (drop table,",
            "delete from, grant, alter role...).",
        ]},
        {"eyebrow": "04", "title": "Confidence fallback", "meta": [
            "Below a 0.6 threshold, answers are",
            "prefixed \u201cI'm not confident...\u201d instead",
            "of presenting a guess as fact.",
        ]},
    ]
    card_grid(s, cards, Inches(0.7), Inches(2.15), Inches(2.9), 0, height=Inches(3.8), on_black=False)
    body_text(s, "Plus PostQueryEnricher (grounds claims in retrieved contract evidence) and "
                 "try/except fallbacks on every external call in the Streamlit app.",
              Inches(0.7), Inches(6.15), Inches(11.6), Inches(0.5), on_black=False, size=11.5)
    footer(s, 10, on_black=False)


def slide_11_cross_persona():
    # source: docs/hackathon-review-human.md 2.4; tests/test_golden_questions.py docstring
    s = new_slide(BLACK)
    kicker(s, "Challenge Requirement", Inches(0.7), Inches(0.5))
    headline(s, "Same question, different words,\nsame number.", Inches(0.7), Inches(0.88), size=30)
    personas = [
        ("Planning", "\u201cWhat's our on-time delivery rate?\u201d"),
        ("Procurement", "\u201cHow are we doing on schedule adherence?\u201d"),
        ("Logistics", "\u201cAre we hitting our delivery dates?\u201d"),
    ]
    x = Inches(0.7)
    w = Inches(3.8)
    for label, q in personas:
        badge_pill(s, label, x, Inches(2.5))
        body_text(s, q, x, Inches(3.0), w - Inches(0.3), Inches(0.8), size=12.5)
        x += w
    rect(s, Inches(0.7), Inches(4.15), Inches(11.6), Pt(1.25), color=LINE_ON_BLACK)
    _, tf = textbox(s, Inches(0.7), Inches(4.4), Inches(6), Inches(1.0))
    p = tf.paragraphs[0]
    r = p.add_run()
    set_run(r, "64.875%", 48, ACCENT, bold=True)
    body_text(s, "Same base_table + measure_name every time \u2014 verified by parsing the generated SQL, "
                 "not just comparing numbers.",
              Inches(0.7), Inches(5.35), Inches(7.0), Inches(0.7), size=12.5)
    body_text(s, "Honest caveat: the golden-question suite (tests/test_golden_questions.py) passes "
                 "2/5 live. The 3 REST-dependent tests hit a disclosed auth-transport bug (401 via "
                 "CortexAnalystClient) \u2014 not a semantic-view or metric-logic problem. The same "
                 "metrics are independently proven correct via direct SEMANTIC_VIEW() SQL and the "
                 "deployed app's SiS-native transport.",
              Inches(7.9), Inches(4.4), Inches(4.5), Inches(2.4), size=10.5)
    footer(s, 11)


def slide_12_app_placeholder():
    # source: app/streamlit_app.py module docstring; memory governed-answer-engine-app
    s = new_slide(CREAM)
    kicker(s, "Phase 7 \u2014 Streamlit in Snowflake, Container Runtime", Inches(0.7), Inches(0.5), on_black=False)
    headline(s, "Ungoverned vs. Governed, live.", Inches(0.7), Inches(0.88), on_black=False, size=30)
    box = rect(s, Inches(0.7), Inches(1.85), Inches(7.4), Inches(4.75), color=RGBColor(0xEC, 0xEC, 0xE6),
               line_color=GREY_ON_CREAM, line_w=1.25, round_=True)
    tf = box.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    set_run(r, "[ SCREENSHOT PLACEHOLDER ]", 16, GREY_ON_CREAM, bold=True)
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    set_run(r2, "Insert: Ungoverned / Governed toggle\n+ sidebar trace log", 12, GREY_ON_CREAM)
    cards = [
        "Dominant Ungoverned / Governed toggle \u2014 one click switches the transport.",
        "Persona chips per metric (e.g. Operations \u00b7 Logistics \u00b7 Procurement for OTD).",
        "Native left sidebar trace log: Understand \u2192 Scope \u2192 SQL \u2192 Answer, newest expanded.",
        "Ungoverned calls a real Cortex Complete call scoped to one department's system; "
        "Governed always routes through the Semantic View.",
    ]
    y = Inches(1.95)
    for c in cards:
        body_text(s, "\u2014  " + c, Inches(8.35), y, Inches(4.1), Inches(0.9), on_black=False, size=11.5)
        y += Inches(1.05)
    footer(s, 12, on_black=False)


def slide_13_document_intelligence():
    # source: sql/04_semantic_view/README.md "Document intelligence"
    s = new_slide(BLACK)
    kicker(s, "Unstructured Data", Inches(0.7), Inches(0.55))
    headline(s, "Contracts become queryable evidence.", Inches(0.7), Inches(0.95), size=30)
    stages = ["PDF contract", "AI_PARSE_DOCUMENT", "Cortex Search", "DocumentQAAgent"]
    x = Inches(0.7)
    w = Inches(2.6)
    y = Inches(2.35)
    for i, st_ in enumerate(stages):
        box = rect(s, x, y, w, Inches(0.85), line_color=WHITE, line_w=1.25, round_=True)
        tf = box.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        set_run(r, st_, 12.5, WHITE, bold=True)
        if i < len(stages) - 1:
            arrow = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x + w, y + Inches(0.425), x + w + Inches(0.35), y + Inches(0.425))
            arrow.line.color.rgb = ACCENT
            arrow.line.width = Pt(1.5)
        x += w + Inches(0.35)
    body_text(s, "11 synthetic supplier contracts, deterministic-per-supplier payment terms "
                 "(Net 30/45/60) + a late-delivery penalty clause \u2014 except SUP-0015, a deliberate "
                 "negative-case test with no penalty clause.",
              Inches(0.7), Inches(3.55), Inches(11.6), Inches(0.6), size=12.5)
    rect(s, Inches(0.7), Inches(4.35), Inches(11.6), Pt(1), color=LINE_ON_BLACK)
    body_text(s, "VALIDATED QUERY", Inches(0.7), Inches(4.6), Inches(3), Inches(0.3), size=10.5, bold=True,
              color=ACCENT)
    body_text(s, "\u201cDoes our contract with Supplier 002 have an SLA penalty for late delivery?\u201d",
              Inches(0.7), Inches(4.95), Inches(11.0), Inches(0.5), size=15, bold=True, color=WHITE)
    body_text(s, "\u2192 Top hit: SUP-0002_contract.pdf (cosine similarity 0.60, reranker 1.09) \u2014 "
                 "\u201c2% of shipment value per day late, capped at 15%.\u201d",
              Inches(0.7), Inches(5.55), Inches(11.0), Inches(0.6), size=13)
    footer(s, 13)


def slide_14_platform_rigor():
    # source: sql/07_rbac/README.md, sql/08_marketplace_enrichment/README.md, sql/10_workspace_artifact/README.md
    s = new_slide(CREAM)
    kicker(s, "Governance & Trust", Inches(0.7), Inches(0.5), on_black=False)
    headline(s, "Least privilege, real external data,\nreal cost discipline.", Inches(0.7), Inches(0.88),
             on_black=False, size=28)
    cards = [
        {"eyebrow": "RBAC", "title": "Least-privilege split", "meta": [
            "SUPPLY_CHAIN_ANALYST_RO (read-only)",
            "+ TASK_EXECUTOR (operational).",
            "Negative test: CREATE TABLE denied",
            "with \u201cInsufficient privileges.\u201d",
        ]},
        {"eyebrow": "MARKETPLACE", "title": "Weather enrichment", "meta": [
            "Pelmorex Frostbyte (free listing)",
            "joined to shipment risk by region.",
            "Honest finding: sample too small",
            "for a real weather signal \u2014 disclosed.",
        ]},
        {"eyebrow": "WORKSPACE", "title": "Legacy queries artifact", "meta": [
            "Every legacy divergence query for",
            "all 4 metrics, published as a",
            "Snowsight Workspace (not just .sql)",
            "\u2014 click-into, not just readable.",
        ]},
    ]
    card_grid(s, cards, Inches(0.7), Inches(2.5), Inches(3.87), 0, height=Inches(3.7), on_black=False)
    footer(s, 14, on_black=False)


def slide_15_coco_lifecycle():
    # source: .snowflake/cortex/plans + .cortex/plans file list; git log; docs/token-and-cost-tracking.md
    s = new_slide(BLACK)
    kicker(s, "How This Was Built", Inches(0.7), Inches(0.5))
    headline(s, "CoCo end-to-end: plan \u2192 build \u2192 run \u2192 validate.", Inches(0.7), Inches(0.88), size=28,
             width=Inches(12))
    rows = [
        {"name": "Planning", "desc": "8 dated CoCo planning-session artifacts, 2026-09-12 \u2192 2026-09-23 "
                                       "(.snowflake/cortex/plans/, .cortex/plans/) \u2014 ontology, pipeline, "
                                       "app UX, and gap-closing plans, each with a timestamped frontmatter."},
        {"name": "Development", "desc": "29 commits across 5 SQL phases + agents/agent_router.py + the "
                                          "Streamlit app \u2014 every phase folder has a README explaining why, "
                                          "not just what."},
        {"name": "Execution", "desc": "28 Dynamic Tables (TARGET_LAG-scheduled) + Cortex Search, run live; "
                                        "pause/resume ops scripts; real 30-day cost: 8.79 warehouse credits, "
                                        "1.14 Cortex Analyst+Search credits."},
        {"name": "Testing & validation", "desc": "reflect_semantic_model run pre-deploy; manual cross-check "
                                                   "against raw fact table (exact match); golden-question "
                                                   "suite \u2014 2/5 passing, disclosed not hidden."},
    ]
    list_rows(s, rows, Inches(0.7), Inches(1.85), Inches(12.0), row_h=Inches(1.15))
    footer(s, 15)


def slide_16_roadmap():
    # source: docs/pending-gaps.md, docs/hackathon-review-human.md sections 5-6
    s = new_slide(CREAM)
    kicker(s, "Roadmap", Inches(0.7), Inches(0.5), on_black=False)
    headline(s, "Built, and what's honestly still ahead.", Inches(0.7), Inches(0.88), on_black=False, size=30)
    col_w = Inches(5.85)
    left_x = Inches(0.7)
    right_x = Inches(6.85)
    top = Inches(2.15)
    badge_pill(s, "Done", left_x, top, on_black=False, accent=True)
    badge_pill(s, "Deferred by decision", right_x, top, on_black=False)
    done = [
        "Custom tools + function calling (4 tool schemas)",
        "Multi-agent orchestration with shared guardrail hooks",
        "Layered hallucination-mitigation guardrails",
        "RBAC least-privilege split, negative-tested",
        "Marketplace enrichment + Workspace artifact",
    ]
    deferred = [
        "Reusable CoCo skill packaging (skills/) \u2014 P3 stretch",
        "MCP connectors \u2014 blocked by no External Access "
        "Integration on this trial account",
        "AUTOMATION schema, Snowflake Tasks, Slack/email alerts",
        "Rewiring the app to connect as the read-only role "
        "(roles exist, grant-complete; wiring not done)",
    ]
    y = top + Inches(0.55)
    for item in done:
        body_text(s, "\u2713  " + item, left_x, y, col_w, Inches(0.6), on_black=False, size=12)
        y += Inches(0.62)
    y = top + Inches(0.55)
    for item in deferred:
        body_text(s, "\u2013  " + item, right_x, y, col_w, Inches(0.75), on_black=False, size=12)
        y += Inches(0.78)
    footer(s, 16, on_black=False)


def slide_17_close():
    # source: judging focus (challenge brief) + docs/hackathon-review-human.md summary
    s = new_slide(BLACK)
    kicker(s, "Judging Focus", Inches(0.7), Inches(0.5))
    headline(s, "Real-world relevance. Technical execution.\nSolution completeness.", Inches(0.7),
             Inches(0.9), size=26, width=Inches(12))
    cols = [
        ("Real-World Relevance", "Genuine multi-system fragmentation, readable in table comments \u2014 "
         "not staged for the demo."),
        ("Technical Execution", "Full medallion pipeline + native Semantic View + multi-agent router + "
         "deployed Streamlit app, all in-repo and commented."),
        ("Solution Completeness", "Ontology \u2192 governance \u2192 app, end to end, with every gap "
         "disclosed rather than hidden."),
    ]
    x = Inches(0.7)
    w = Inches(3.87)
    for title, desc in cols:
        rect(s, x, Inches(2.6), Inches(1.2), Pt(3), color=ACCENT)
        body_text(s, title.upper(), x, Inches(2.85), w - Inches(0.3), Inches(0.4), size=12, bold=True,
                   color=WHITE)
        body_text(s, desc, x, Inches(3.3), w - Inches(0.3), Inches(1.6), size=12)
        x += w
    rect(s, Inches(0.7), Inches(5.35), Inches(11.6), Pt(1), color=LINE_ON_BLACK)
    _, tf = textbox(s, Inches(0.7), Inches(5.6), Inches(11.6), Inches(0.9))
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    set_run(r, "Ask it three ways. Get one answer.", 26, ACCENT, bold=True)
    footer(s, 17)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    slide_01_cover()
    slide_02_problem()
    slide_03_approach()
    slide_04_fragmentation()
    slide_05_entity_resolution()
    slide_06_ontology()
    slide_07_metrics()
    slide_08_legacy_vs_governed()
    slide_09_agent_router()
    slide_10_guardrails()
    slide_11_cross_persona()
    slide_12_app_placeholder()
    slide_13_document_intelligence()
    slide_14_platform_rigor()
    slide_15_coco_lifecycle()
    slide_16_roadmap()
    slide_17_close()

    out_path = __file__.rsplit("\\", 1)[0] + "\\hackathon-deck.pptx"
    prs.save(out_path)
    print(f"Saved {len(prs.slides.__iter__.__self__._sldIdLst)} slides -> {out_path}")


if __name__ == "__main__":
    build()
