"""Native interactive charts built on flet_charts 0.86.5.

Renders chart-spec results produced by AI analyses (``result = {"chart": ...}``)
as real, touch-friendly Flet charts - animated, with hover tooltips - instead
of static PNGs. All constructors verified against the installed package.
"""

from __future__ import annotations

import logging
import math

import flet as ft
import flet_charts as fch

from core import theme, tokens

logger = logging.getLogger("NativeChart")

# Distinct series palette tuned for light & dark surfaces
# Distinct series palette tuned for light & dark surfaces
_PALETTE = [
    theme.PRIMARY,
    theme.ACCENT,
    *theme.CHART_PALETTE,
]

_LABEL_CAP = 14  # max x-axis labels rendered before thinning


def _num(v) -> float | None:
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except TypeError, ValueError:
        return None


def _thinned_labels(x_labels: list) -> list[tuple[int, str]]:
    """Return (index, label) pairs, thinned to at most _LABEL_CAP entries."""
    items = [(i, str(lbl)) for i, lbl in enumerate(x_labels)]
    if len(items) <= _LABEL_CAP:
        return items
    step = len(items) / _LABEL_CAP
    return [items[min(int(i * step), len(items) - 1)] for i in range(_LABEL_CAP)]


def _axis_text(value: str, size: int = tokens.FONT_SM_XS) -> ft.Text:
    return ft.Text(
        value,
        size=size,
        color=ft.Colors.ON_SURFACE_VARIANT,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )


def build_native_chart(spec: dict) -> ft.Control | None:
    """Build an interactive chart from a chart spec.

    Spec shape (produced by AI code or the result serializer):
        {"type": "bar"|"line"|"pie", "title": str, "x": [labels],
         "series": [{"name": str, "y": [numbers]}],
         "y_label": str (bar/line only), "values": [numbers] (pie shorthand)}
    """
    if not isinstance(spec, dict):
        return None
    chart_type = str(spec.get("type", "")).lower().strip()
    title = str(spec.get("title", "")).strip()
    x_labels = [str(x) for x in (spec.get("x") or [])]
    raw_series = spec.get("series") or []
    if not raw_series and spec.get("values"):
        raw_series = [{"name": spec.get("series_name", "Value"), "y": spec["values"]}]

    series: list[tuple[str, list[float | None]]] = []
    for s in raw_series:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name", "Series"))
        ys = [_num(v) for v in (s.get("y") or s.get("data") or [])]
        series.append((name, ys))
    if not series:
        return None

    try:
        if chart_type == "pie":
            chart = _build_pie(spec, series)
        elif chart_type == "line":
            chart = _build_line(spec, series, x_labels)
        elif chart_type == "bar":
            chart = _build_bar(spec, series)
        else:
            return None
    except Exception as ex:
        logger.warning("Native chart build failed: %s", ex)
        return None

    header_controls = []
    if title:
        header_controls.append(
            ft.Text(
                title,
                size=tokens.FONT_SM,
                weight=ft.FontWeight.W_700,
                color=ft.Colors.ON_SURFACE,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )

    if chart_type == "pie":
        values = [v for v in series[0][1] if v is not None]
        legend_names = x_labels[: len(values)] or [name for name, _ in series]
    else:
        legend_names = [name for name, _ in series]
    legend = _build_legend(legend_names) if len(legend_names) > 1 else []

    return ft.Container(
        content=ft.Column(
            header_controls + [ft.Container(content=chart, height=220)] + legend,
            spacing=tokens.SPACE_XS,
        ),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_MD,
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE),
        border=ft.Border.all(
            tokens.DIVIDER_THICKNESS,
            ft.Colors.with_opacity(tokens.OPACITY_MUTED, ft.Colors.ON_SURFACE),
        ),
    )


def _build_pie(
    spec: dict, series: list[tuple[str, list[float | None]]]
) -> fch.PieChart:
    values = [v for v in series[0][1] if v is not None]
    total = sum(values) or 1.0

    sections = []
    for i, v in enumerate(values):
        pct = v / total * 100
        sections.append(
            fch.PieChartSection(
                value=v,
                title=f"{pct:.0f}%",
                title_style=ft.TextStyle(
                    size=tokens.FONT_SM,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                ),
                color=_PALETTE[i % len(_PALETTE)],
                radius=tokens.PIE_CHART_RADIUS,
            )
        )

    return fch.PieChart(
        sections=sections,
        center_space_radius=tokens.PIE_CHART_CENTER_RADIUS,
        sections_space=tokens.SPACE_XXS,
        expand=True,
        animation=ft.Animation(
            tokens.OUTPUT_THROTTLE_MS, ft.AnimationCurve.EASE_OUT_CUBIC
        ),
    )


def _build_line(
    spec: dict,
    series: list[tuple[str, list[float | None]]],
    x_labels: list[str],
) -> fch.LineChart:
    max_len = max((len(ys) for _, ys in series), default=0)
    if not x_labels:
        x_labels = [str(i + 1) for i in range(max_len)]

    data_series = []
    for i, (name, ys) in enumerate(series):
        points = [
            fch.LineChartDataPoint(x=j, y=y) for j, y in enumerate(ys) if y is not None
        ]
        if not points:
            continue
        data_series.append(
            fch.LineChartData(
                points=points,
                curved=True,
                color=_PALETTE[i % len(_PALETTE)],
                stroke_width=2.5,
                rounded_stroke_cap=True,
            )
        )

    bottom_labels = [
        fch.ChartAxisLabel(value=i, label=_axis_text(lbl))
        for i, lbl in _thinned_labels(x_labels[:max_len])
    ]

    return fch.LineChart(
        data_series=data_series,
        interactive=True,
        expand=True,
        min_y=0,
        horizontal_grid_lines=fch.ChartGridLines(
            interval=None,
            color=ft.Colors.with_opacity(tokens.OPACITY_MUTED, ft.Colors.ON_SURFACE),
        ),
        left_axis=fch.ChartAxis(
            title=ft.Text(
                str(spec.get("y_label", "")),
                size=tokens.FONT_XS,
                color=ft.Colors.ON_SURFACE_VARIANT,
                weight=ft.FontWeight.W_600,
            )
            if spec.get("y_label")
            else None,
        ),
        bottom_axis=fch.ChartAxis(labels=bottom_labels),
        animation=ft.Animation(
            tokens.OUTPUT_THROTTLE_MS, ft.AnimationCurve.EASE_OUT_CUBIC
        ),
    )


def _build_bar(
    spec: dict, series: list[tuple[str, list[float | None]]]
) -> fch.BarChart:
    x_labels = [str(x) for x in (spec.get("x") or [])]
    groups = []
    n_points = max(len(ys) for _, ys in series)
    for j in range(n_points):
        rods = []
        for i, (_, ys) in enumerate(series):
            v = ys[j] if j < len(ys) else None
            if v is None:
                continue
            rods.append(
                fch.BarChartRod(
                    from_y=0,
                    to_y=v,
                    width=max(6, 26 - 4 * (len(series) - 1)),
                    color=_PALETTE[i % len(_PALETTE)],
                    tooltip=f"{v:,.2f}",
                    show_tooltip=True,
                    border_radius=tokens.RADIUS_XS,
                )
            )
        if rods:
            groups.append(fch.BarChartGroup(x=j, rods=rods))

    bottom_labels = (
        [
            fch.ChartAxisLabel(value=i, label=_axis_text(lbl))
            for i, lbl in _thinned_labels(x_labels[:n_points])
        ]
        if x_labels
        else []
    )

    return fch.BarChart(
        groups=groups,
        interactive=True,
        expand=True,
        horizontal_grid_lines=fch.ChartGridLines(
            color=ft.Colors.with_opacity(tokens.OPACITY_MUTED, ft.Colors.ON_SURFACE),
        ),
        left_axis=fch.ChartAxis(
            title=ft.Text(
                str(spec.get("y_label", "")),
                size=tokens.FONT_XS,
                color=ft.Colors.ON_SURFACE_VARIANT,
                weight=ft.FontWeight.W_600,
            )
            if spec.get("y_label")
            else None
        ),
        bottom_axis=fch.ChartAxis(labels=bottom_labels) if bottom_labels else None,
        animation=ft.Animation(
            tokens.OUTPUT_THROTTLE_MS, ft.AnimationCurve.EASE_OUT_CUBIC
        ),
    )


def _build_legend(names: list[str]) -> list[ft.Control]:
    dots = []
    for i, name in enumerate(names):
        dots.append(
            ft.Row(
                [
                    ft.Container(
                        width=tokens.DOT_INDICATOR_WIDTH_INACTIVE,
                        height=tokens.DOT_INDICATOR_HEIGHT,
                        border_radius=tokens.RADIUS_XS,
                        bgcolor=_PALETTE[i % len(_PALETTE)],
                    ),
                    ft.Text(
                        name,
                        size=tokens.FONT_XS,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=tokens.SPACE_XS,
                tight=True,
            )
        )
    return [ft.Row(dots, wrap=True, spacing=tokens.SPACE_SM)] if dots else []
