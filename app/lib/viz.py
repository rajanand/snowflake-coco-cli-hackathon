"""Altair chart builders.

Every spec is handed the active token dict so charts and page can never drift
apart on a theme switch, and all chart furniture (background, fonts, axis
colour) is derived from those tokens rather than Altair's defaults.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

FONT = "Geist"
MONO = "Geist Mono"


def _base(chart, c: dict, height: int):
    """Apply shared theming: transparent ground, Geist, hairline axes."""
    return (
        chart.properties(height=height, background="transparent")
        .configure_view(strokeWidth=0, fill=None)
        .configure_axis(
            labelFont=FONT, titleFont=FONT,
            labelColor=c["muted"], titleColor=c["muted"],
            labelFontSize=11, titleFontSize=11,
            domainColor=c["hairline"], tickColor=c["hairline"],
            gridColor=c["grid"], gridDash=[2, 3],
        )
        .configure_legend(
            labelFont=FONT, titleFont=FONT,
            labelColor=c["text_dim"], titleColor=c["muted"],
            labelFontSize=11, titleFontSize=10,
        )
        .configure_text(font=FONT)
    )


# ---------------------------------------------------------------------------
# The answer number line
# ---------------------------------------------------------------------------

def answer_number_line(
    c: dict,
    legacy: list[dict],
    governed: float | None,
    domain: list[float],
    unit: str = "%",
    sample: dict | None = None,
    beat: int = 3,
    fmt_precision: int = 1,
) -> alt.LayerChart:
    """One axis that carries the whole argument.

    Reading order is deliberate. The shaded band is the range the *loud*
    systems argued over. Hollow rings are their individual claims - hollow and
    low-contrast because they are noise. If a sampled source exists it is drawn
    as an interval, never a point, because a 70%-coverage sample does not
    deserve the visual authority of a single number. The governed answer is the
    only filled, accented mark on the chart.

    ``beat`` gates the reveal so the presenter controls the pace:
        1 = claims + band, 2 = + divergence callout, 3 = + governed answer.
    """
    layers = []

    vals = [l["value"] for l in legacy if l.get("value") is not None]
    lo_band, hi_band = (min(vals), max(vals)) if vals else (0, 0)
    spread = hi_band - lo_band

    # Y positions. The axis is hidden; these only establish vertical rhythm.
    Y_CLAIM, Y_SAMPLE = 0.66, 0.28
    y_scale = alt.Scale(domain=[0, 1])
    y_enc = alt.Y("y:Q", scale=y_scale, axis=None)
    x_scale = alt.Scale(domain=domain, nice=False, clamp=True)

    def x(field="x:Q", title=None):
        return alt.X(field, scale=x_scale,
                     axis=alt.Axis(title=title, grid=True, tickCount=6,
                                   format=",.0f", labelPadding=6))

    # --- 1. the range the loud systems argued over -------------------------
    if beat >= 1 and vals:
        band = pd.DataFrame([{"x": lo_band, "x2": hi_band, "y": 0.02, "y2": 0.92}])
        layers.append(
            alt.Chart(band).mark_rect(
                fill=c["noise"], fillOpacity=0.11,
                stroke=c["noise"], strokeOpacity=0.30, strokeWidth=1, strokeDash=[3, 3],
            ).encode(
                x=x("x:Q", f"Reported value ({unit.strip() or 'value'})"),
                x2="x2:Q",
                y=alt.Y("y:Q", scale=y_scale, axis=None),
                y2="y2:Q",
            )
        )

    # --- 2. individual legacy claims: hollow, recessive -------------------
    if beat >= 1 and legacy:
        ldf = pd.DataFrame([
            {
                "x": l["value"], "y": Y_CLAIM,
                "label": l["system"], "team": l["team"],
                "definition": l["definition"], "flaw": l["flaw"],
                "shown": f"{l['value']:.{fmt_precision}f}{unit}",
            }
            for l in legacy if l.get("value") is not None
        ])

        # Stems tie each ring to the axis so the reading is unambiguous.
        layers.append(
            alt.Chart(ldf).mark_rule(
                color=c["noise"], strokeWidth=1, strokeOpacity=0.45
            ).encode(x=x(), y=alt.datum(0.02), y2=alt.datum(Y_CLAIM))
        )
        layers.append(
            alt.Chart(ldf).mark_point(
                filled=False, size=165, strokeWidth=1.7, opacity=1,
            ).encode(
                x=x(), y=y_enc,
                stroke=alt.value(c["noise"]),
                tooltip=[
                    alt.Tooltip("team:N", title="Team"),
                    alt.Tooltip("label:N", title="System"),
                    alt.Tooltip("shown:N", title="Their answer"),
                    alt.Tooltip("definition:N", title="Their definition"),
                    alt.Tooltip("flaw:N", title="Why it is wrong"),
                ],
            )
        )
        # System name above, its number below - keeps the ring uncluttered.
        layers.append(
            alt.Chart(ldf).mark_text(
                dy=-16, font=FONT, fontSize=11, fontWeight=500, color=c["muted"]
            ).encode(x=x(), y=y_enc, text="label:N")
        )
        layers.append(
            alt.Chart(ldf).mark_text(
                dy=15, font=MONO, fontSize=11, color=c["noise"]
            ).encode(x=x(), y=y_enc, text="shown:N")
        )

    # --- 3. divergence callout: used once, in warn ------------------------
    if beat >= 2 and spread > 0:
        mid = pd.DataFrame([{
            "x": (lo_band + hi_band) / 2, "y": 0.97,
            "t": f"{spread:.{fmt_precision}f} {unit.strip() or 'unit'} of disagreement",
        }])
        layers.append(
            alt.Chart(mid).mark_text(
                font=FONT, fontSize=11.5, fontWeight=600, color=c["warn"],
            ).encode(x=x(), y=alt.Y("y:Q", scale=y_scale, axis=None), text="t:N")
        )

    # --- 4. sampled source as an interval, not a point -------------------
    if beat >= 1 and sample:
        sdf = pd.DataFrame([{
            "x": sample["lo"], "x2": sample["hi"], "y": Y_SAMPLE,
            "point": sample["point"], "n": sample["n"],
            "coverage": sample["coverage"],
            "ci": f"{sample['lo']:.1f}–{sample['hi']:.1f}{unit}",
        }])
        layers.append(
            alt.Chart(sdf).mark_rule(
                color=c["noise"], strokeWidth=5, strokeOpacity=0.42, strokeCap="round"
            ).encode(
                x=x(), x2="x2:Q", y=y_enc,
                tooltip=[
                    alt.Tooltip("ci:N", title="95% CI"),
                    alt.Tooltip("point:Q", title="Sample value", format=".3f"),
                    alt.Tooltip("n:Q", title="Shipments sampled"),
                    alt.Tooltip("coverage:Q", title="Coverage %"),
                ],
            )
        )
        layers.append(
            alt.Chart(sdf).mark_tick(
                color=c["noise"], thickness=1.7, size=15, opacity=0.95
            ).encode(x=alt.X("point:Q", scale=x_scale, axis=None), y=y_enc)
        )
        layers.append(
            alt.Chart(sdf).mark_text(
                dy=17, font=FONT, fontSize=10.5, color=c["muted"],
            ).encode(
                x=alt.X("point:Q", scale=x_scale, axis=None), y=y_enc,
                text=alt.value(
                    f"IoT sensors · {sample['coverage']:.0f}% coverage · 95% CI"
                ),
            )
        )

    # --- 5. the governed answer: the only filled, accented mark ---------
    if beat >= 3 and governed is not None:
        gdf = pd.DataFrame([{
            "x": governed, "y": Y_CLAIM,
            "shown": f"{governed:.{fmt_precision}f}{unit}",
        }])
        layers.append(
            alt.Chart(gdf).mark_rule(
                color=c["accent"], strokeWidth=2.4
            ).encode(x=x(), y=alt.datum(0.0), y2=alt.datum(0.94))
        )
        layers.append(
            alt.Chart(gdf).mark_point(
                filled=True, size=260, opacity=1
            ).encode(
                x=x(), y=y_enc,
                color=alt.value(c["accent"]),
                tooltip=[alt.Tooltip("shown:N", title="Governed answer")],
            )
        )
        layers.append(
            alt.Chart(gdf).mark_text(
                dy=-30, font=FONT, fontSize=10.5, fontWeight=600,
                color=c["accent"],
            ).encode(x=x(), y=y_enc, text=alt.value("GOVERNED"))
        )
        layers.append(
            alt.Chart(gdf).mark_text(
                dy=19, font=MONO, fontSize=12.5, fontWeight=600, color=c["accent"]
            ).encode(x=x(), y=y_enc, text="shown:N")
        )

    if not layers:
        layers.append(alt.Chart(pd.DataFrame([{"x": domain[0], "y": 0}])).mark_point(
            opacity=0).encode(x=x(), y=y_enc))

    return _base(alt.layer(*layers).resolve_scale(x="shared"), c, height=232)


# ---------------------------------------------------------------------------
# Drilldown
# ---------------------------------------------------------------------------

def drilldown_bars(c: dict, df: pd.DataFrame, dim_col: str, metric_col: str,
                   unit: str = "%") -> alt.Chart:
    """Horizontal bars for a dimension slice of a governed metric.

    Horizontal because dimension labels are words, not dates, and a single
    accent hue with opacity encoding keeps it from becoming a colour chart.
    """
    d = df.copy()
    d[metric_col] = pd.to_numeric(d[metric_col], errors="coerce")
    d = d.dropna(subset=[metric_col])

    bars = alt.Chart(d).mark_bar(
        height=16, cornerRadiusEnd=3, color=c["accent"], opacity=0.85
    ).encode(
        y=alt.Y(f"{dim_col}:N", sort="-x", title=None,
                axis=alt.Axis(labelFont=FONT, labelFontSize=11.5,
                              labelColor=c["text_dim"], labelPadding=8,
                              domainOpacity=0, tickOpacity=0)),
        x=alt.X(f"{metric_col}:Q", title=None,
                axis=alt.Axis(grid=True, tickCount=5, format=",.0f")),
        tooltip=[alt.Tooltip(f"{dim_col}:N", title="Segment"),
                 alt.Tooltip(f"{metric_col}:Q", title="Governed value", format=".3f")],
    )

    labels = alt.Chart(d).mark_text(
        align="left", dx=6, font=MONO, fontSize=11, color=c["text_dim"]
    ).encode(
        y=alt.Y(f"{dim_col}:N", sort="-x", title=None),
        x=alt.X(f"{metric_col}:Q"),
        text=alt.Text(f"{metric_col}:Q", format=".1f"),
    )

    h = max(120, 34 * max(len(d), 1))
    return _base(alt.layer(bars, labels), c, height=h)
