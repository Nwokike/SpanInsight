"""Parse Colab execution outputs into Flet controls for display."""

from __future__ import annotations

import base64
import json
import logging
from html.parser import HTMLParser as _HTMLParser

import flet as ft

from components.ansi_parser import parse_ansi_to_flet_text
from core import theme, tokens

logger = logging.getLogger("NotebookOutput")

_PLOTLY_MIME = "application/vnd.plotly.v1+json"


def _image_container(b64_img: str) -> ft.Container:
    # flet 0.86.5: Image.src accepts a base64 string directly (no src_base64 kw)
    return ft.Container(
        content=ft.Image(
            src=b64_img,
            fit=ft.BoxFit.CONTAIN,
        ),
        margin=ft.Margin(
            tokens.SPACE_NONE, tokens.SPACE_XS, tokens.SPACE_NONE, tokens.SPACE_XS
        ),
        border_radius=tokens.RADIUS_SM,
    )


def _html_to_text(html: str) -> str:
    """Convert kernel HTML output (e.g. styled DataFrame reprs) to readable text."""
    try:
        import html2text

        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.body_width = 0
        return converter.handle(html).strip()
    except Exception:
        # Last resort: strip tags crudely so content is never silently dropped
        import re

        text = re.sub(r"<[^>]+>", " ", html)
        return text.strip()


class _TableExtractor(_HTMLParser):
    """Pull plain-text cell grids out of <table> markup (stdlib only)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._depth = 0
        self._rows: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                self._rows = []
        elif self._depth and tag == "tr":
            self._row = []
        elif self._depth and tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "table" and self._depth:
            self._depth -= 1
            if self._depth == 0 and self._rows is not None:
                self.tables.append(self._rows)
                self._rows = None
        elif self._depth and tag == "tr" and self._row is not None:
            if self._rows is not None and self._row:
                self._rows.append(self._row)
            self._row = None
        elif self._depth and tag in ("td", "th") and self._cell is not None:
            if self._row is not None:
                self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


_MAX_MD_TABLES = 4
_MAX_MD_ROWS = 60


def _markdown_from_html_tables(html: str) -> str | None:
    """Render HTML <table>s (styled DataFrames) as native markdown tables.

    Returns markdown text or None when the html holds no usable table, so the
    caller can fall back to plain-text conversion.
    """
    try:
        parser = _TableExtractor()
        parser.feed(html)
        parts = []
        for rows in parser.tables[:_MAX_MD_TABLES]:
            rows = [r for r in rows[:_MAX_MD_ROWS] if r]
            if len(rows) < 2:
                continue  # need a header plus at least one body row
            ncols = max(len(r) for r in rows)

            def _fmt(r: list[str], _ncols: int = ncols) -> str:
                return (
                    "| "
                    + " | ".join(r[c] if c < len(r) else "" for c in range(_ncols))
                    + " |"
                )

            lines = [_fmt(rows[0]), "|" + "|".join([" --- "] * ncols) + "|"]
            lines.extend(_fmt(r) for r in rows[1:])
            parts.append("\n".join(lines))
        return "\n\n".join(parts) or None
    except Exception:
        return None


def parse_outputs_to_controls(outputs: list) -> list[ft.Control]:
    """Convert raw Colab output dicts into renderable Flet controls."""
    output_controls = []
    for out in outputs:
        if len(output_controls) >= 1000:
            break
        otype = out.get("output_type") or out.get("type", "")
        if otype == "stream":
            is_err = out.get("name") == "stderr"
            text = out.get("text", "")
            output_controls.append(
                parse_ansi_to_flet_text(
                    raw_text=text, default_size=tokens.FONT_SM, is_error=is_err
                )
            )
        elif otype == "error":
            traceback = "\n".join(out.get("traceback", []))
            output_controls.append(
                parse_ansi_to_flet_text(
                    raw_text=traceback,
                    default_size=tokens.FONT_SM,
                    is_error=True,
                )
            )
        elif otype in ["execute_result", "display_data"]:
            data = out.get("data", {})
            if "image/png" in data:
                try:
                    b64_img = data["image/png"]
                    b64_img = b64_img.replace("\n", "").replace("\r", "")
                    output_controls.append(_image_container(b64_img))
                except Exception as e:
                    output_controls.append(
                        ft.Text(f"Image Error: {e}", color=theme.ERROR)
                    )
            elif "image/svg+xml" in data:
                # Rare (matplotlib ships PNG alongside); best-effort render
                try:
                    svg = data["image/svg+xml"]
                    if isinstance(svg, (list, tuple)):
                        svg = "".join(str(s) for s in svg)
                    b64_svg = base64.b64encode(str(svg).encode("utf-8")).decode("utf-8")
                    output_controls.append(_image_container(b64_svg))
                except Exception as e:
                    logger.debug("SVG render failed (%s); trying text/plain", e)
                    if "text/plain" in data:
                        output_controls.append(
                            parse_ansi_to_flet_text(
                                raw_text=data["text/plain"],
                                default_size=tokens.FONT_SM,
                            )
                        )
            elif _PLOTLY_MIME in data:
                # Interactive Plotly figures can't render in-app - be honest,
                # and still show the textual repr instead of dropping everything.
                note = ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.INFO_OUTLINE_ROUNDED,
                                size=tokens.ICON_XS,
                                color=theme.WARNING,
                            ),
                            ft.Text(
                                "Interactive Plotly figure - shown as summary below.",
                                size=tokens.FONT_XS,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=tokens.SPACE_XS,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_NONE,
                        tokens.SPACE_XXS,
                        tokens.SPACE_NONE,
                        tokens.SPACE_NONE,
                    ),
                )
                output_controls.append(note)
                if "text/plain" in data:
                    output_controls.append(
                        parse_ansi_to_flet_text(
                            raw_text=data["text/plain"],
                            default_size=tokens.FONT_SM,
                        )
                    )
            elif "application/json" in data:
                payload = data["application/json"]
                try:
                    pretty = json.dumps(
                        payload, indent=2, ensure_ascii=False, default=str
                    )
                except Exception:
                    pretty = str(payload)
                if len(pretty) > 5000:
                    pretty = pretty[:5000] + "\n…"
                output_controls.append(
                    ft.Container(
                        content=parse_ansi_to_flet_text(
                            pretty, default_size=tokens.FONT_SM
                        ),
                        padding=tokens.SPACE_SM,
                        bgcolor=theme.TERMINAL_BG,
                        border_radius=tokens.RADIUS_SM,
                    )
                )
            elif "text/html" in data:
                html = data["text/html"]
                if isinstance(html, (list, tuple)):
                    html = "".join(str(h) for h in html)
                # Styled DataFrames ship as HTML tables - render them as real
                # tables via markdown; fall back to plain text otherwise.
                md_tables = _markdown_from_html_tables(str(html))
                if md_tables:
                    output_controls.append(
                        ft.Markdown(
                            value=md_tables,
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        )
                    )
                    continue
                readable = _html_to_text(str(html))
                if readable:
                    output_controls.append(
                        ft.Container(
                            content=parse_ansi_to_flet_text(
                                readable, default_size=tokens.FONT_SM
                            ),
                            padding=tokens.SPACE_SM,
                            bgcolor=ft.Colors.with_opacity(
                                tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE
                            ),
                            border_radius=tokens.RADIUS_SM,
                        )
                    )
            elif "text/plain" in data:
                output_controls.append(
                    parse_ansi_to_flet_text(
                        raw_text=data["text/plain"],
                        default_size=tokens.FONT_SM,
                    )
                )
    return output_controls


def parse_cell_outputs(cell: dict) -> list[ft.Control]:
    """Structured result visualizer first (native chart/table/metrics), then raw outputs."""
    controls: list[ft.Control] = []
    structured = cell.get("structured_result")
    if isinstance(structured, dict):
        try:
            from components.report_editor.visualizers import (
                build_serialized_result_visualizer,
            )

            vis = build_serialized_result_visualizer(structured)
            if vis is not None:
                controls.append(vis)
        except Exception as ex:
            logger.warning("Structured result render failed: %s", ex)
    controls.extend(parse_outputs_to_controls(cell.get("outputs", [])))
    return controls
