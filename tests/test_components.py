"""Tests for components: ANSI parser, output formatting, files formatting, and FAB menu."""

from __future__ import annotations

from components.ansi_parser import parse_ansi_to_flet_text
from screens.analysis.fab_menu import build_analysis_fab
from screens.files.components import fmt_size, is_data_file


class TestAnsiParser:
    def test_plain_text(self):
        txt = parse_ansi_to_flet_text("Hello World")
        assert txt.spans is not None
        assert any("Hello World" in (s.text or "") for s in txt.spans)

    def test_ansi_color_code(self):
        txt = parse_ansi_to_flet_text("\x1b[31mError text\x1b[0m")
        assert txt.spans is not None
        assert any("Error text" in (s.text or "") for s in txt.spans)


class TestFilesComponents:
    def test_fmt_size(self):
        assert fmt_size(500) == "500 B"
        assert fmt_size(2048) == "2.0 KB"
        assert fmt_size(5 * 1024 * 1024) == "5.0 MB"
        assert fmt_size(None) == ""

    def test_is_data_file(self):
        assert is_data_file("data.csv") is True
        assert is_data_file("records.xlsx") is True
        assert is_data_file("output.parquet") is True
        assert is_data_file("info.json") is True
        assert is_data_file("script.py") is False
        assert is_data_file("image.png") is False


class TestFabMenu:
    def test_build_fab_with_cells(self):
        fab = build_analysis_fab(
            has_session=True,
            has_cells=True,
            has_schema=True,
            autopilot_running=False,
            on_export=None,
            on_clear_all=None,
            on_autopilot=None,
            on_manage_files=None,
        )
        assert fab is not None
        assert fab.content is not None
        # Check popup items
        items = fab.content.items
        assert len(items) == 4
        assert items[0].content == "Export .ipynb"
        assert items[1].content == "Clear All Cells"
        assert items[2].content == "Run Autopilot"
        assert items[3].content == "Manage Files"

    def test_build_fab_empty(self):
        fab = build_analysis_fab(
            has_session=True,
            has_cells=False,
            has_schema=False,
            autopilot_running=False,
            on_export=None,
            on_clear_all=None,
            on_autopilot=None,
            on_manage_files=None,
        )
        assert fab is not None
        assert len(fab.content.items) == 1
        assert fab.content.items[0].content == "Manage Files"

    def test_build_fab_no_session(self):
        fab = build_analysis_fab(
            has_session=False,
            has_cells=False,
            has_schema=False,
            autopilot_running=False,
            on_export=None,
            on_clear_all=None,
            on_autopilot=None,
            on_manage_files=None,
        )
        assert fab is None


class TestFileItem:
    def test_file_item_no_selection_mode(self):
        from components.file_item import build_file_item

        item = build_file_item(
            file_info={"name": "data.csv", "type": "file", "size": 1024},
            selected=False,
            selection_mode=False,
        )
        assert item is not None
        # Row has 2 controls: icon + name/size column (no trailing checkbox)
        assert len(item.content.controls) == 2

    def test_file_item_with_selection_mode(self):
        from components.file_item import build_file_item

        item = build_file_item(
            file_info={"name": "data.csv", "type": "file", "size": 1024},
            selected=True,
            selection_mode=True,
        )
        assert item is not None
        # Row has 3 controls: icon + name/size column + trailing checkbox
        assert len(item.content.controls) == 3
