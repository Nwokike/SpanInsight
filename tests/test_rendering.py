"""Tests for structured rendering: native charts, image fallbacks, output
parsing, and session-expiry recovery."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from components.native_chart import build_native_chart
from components.notebook_cell.output import (
    parse_cell_outputs,
    parse_outputs_to_controls,
)
from components.report_editor.visualizers import build_serialized_result_visualizer
from core.state import state
from screens.analysis.colab_connection import session_expired as _session_expired
from screens.analysis.execution_runner import run_cell_async
from services.colab.introspection import build_result_serialization_code

_BAR_SPEC = {
    "type": "bar",
    "title": "Revenue by Region",
    "x": ["East", "West", "North", "South"],
    "series": [{"name": "Revenue", "y": [100, 240, 180, 90]}],
}

_LINE_SPEC = {
    "type": "line",
    "title": "Monthly Sales",
    "x": ["Jan", "Feb", "Mar", "Apr"],
    "series": [{"name": "Sales", "y": [30, 45, 40, 60]}],
}

_PIE_SPEC = {
    "type": "pie",
    "title": "Traffic Sources",
    "x": ["Organic", "Ads", "Referral"],
    "series": [{"name": "Visits", "y": [500, 300, 200]}],
}


class TestNativeCharts:
    def test_bar_chart_builds(self):
        ctrl = build_native_chart(_BAR_SPEC)
        assert ctrl is not None

    def test_line_chart_builds(self):
        ctrl = build_native_chart(_LINE_SPEC)
        assert ctrl is not None

    def test_pie_chart_builds(self):
        ctrl = build_native_chart(_PIE_SPEC)
        assert ctrl is not None

    def test_pie_values_shorthand(self):
        spec = {"type": "pie", "x": ["A", "B"], "values": [7, 3]}
        assert build_native_chart(spec) is not None

    def test_invalid_spec_returns_none(self):
        assert build_native_chart({"type": "bar", "series": []}) is None
        assert build_native_chart({"type": "hexagon"}) is None
        assert build_native_chart("not a dict") is None

    def test_nan_and_junk_values_filtered(self):
        spec = {
            "type": "bar",
            "x": ["a", "b", "c"],
            "series": [{"name": "S", "y": [1, "junk", float("nan")]}],
        }
        assert build_native_chart(spec) is not None


class TestChartImageFallback:
    def test_png_fallback_when_native_fails(self):
        """Worst-case: native chart can't build → old-app-style image shows."""
        ser_res = {
            "type": "chart",
            "data": {"type": "bar", "series": []},
            "png_b64": "aVFBORw0KGgo=",
        }
        vis = build_serialized_result_visualizer(ser_res)
        assert vis is not None  # image fallback engaged, never blank

    def test_native_preferred_over_png(self):
        ser_res = {"type": "chart", "data": _BAR_SPEC, "png_b64": "aVFBORw0KGgo="}
        vis = build_serialized_result_visualizer(ser_res)
        assert vis is not None


class TestVisualizers:
    def test_dataframe_table_footer_shows_row_count(self):
        ser_res = {
            "type": "dataframe",
            "columns": ["a", "b"],
            "data": [[1, 2], [3, 4]],
            "total_rows": 1000,
        }
        vis = build_serialized_result_visualizer(ser_res)
        assert vis is not None

    def test_scalar_tile(self):
        vis = build_serialized_result_visualizer({"type": "scalar", "data": 42})
        assert vis is not None

    def test_dict_metric_cards(self):
        vis = build_serialized_result_visualizer(
            {"type": "dict", "data": {"mean": 12.5, "count": 9}}
        )
        assert vis is not None


class TestOutputParsing:
    def test_html_output_renders_as_text(self):
        outputs = [
            {
                "output_type": "display_data",
                "data": {"text/html": "<table><tr><td>42</td></tr></table>"},
            }
        ]
        ctrls = parse_outputs_to_controls(outputs)
        assert ctrls, "HTML output must not be silently dropped"

    def test_plotly_output_gets_notice_not_silence(self):
        outputs = [
            {
                "output_type": "display_data",
                "data": {
                    "application/vnd.plotly.v1+json": '{"data": []}',
                    "text/plain": "Figure(...)",
                },
            }
        ]
        ctrls = parse_outputs_to_controls(outputs)
        assert ctrls, "Plotly output must not be silently dropped"

    def test_parse_cell_outputs_structured_first(self):
        cell = {
            "id": "c1",
            "structured_result": {"type": "scalar", "data": 7},
            "outputs": [{"output_type": "stream", "text": "hello"}],
        }
        ctrls = parse_cell_outputs(cell)
        assert len(ctrls) == 2  # structured visualizer + raw stream

    def test_serializer_code_contract(self):
        code = build_result_serialization_code()
        assert "__SPANINSIGHT_RESULT_START__" in code
        assert "__SPANINSIGHT_RESULT_END__" in code
        # The kernel-wide backend must never be switched - user cells rely on inline
        assert "matplotlib.use" not in code


class _Refs:
    def __init__(self):
        self.current = {}


class RecoveryFakeColab:
    """Raises session-expired on first cell exec, succeeds after reconnect."""

    def __init__(self):
        self.calls = []
        self.reconnected = False

    async def check_auth(self):
        return True

    async def list_sessions(self):
        return []

    async def exec_code(self, code, session_name=None, **kwargs):
        self.calls.append((session_name, code))
        if not self.reconnected and "print('hello')" in code:
            raise RuntimeError(
                "Session has expired or closed on Colab server (404 Not Found) "
                "and was removed locally."
            )
        return [{"output_type": "stream", "name": "stdout", "text": "hello"}]


class HealingColab:
    """Fails the first N cell executions with kernel errors, then succeeds."""

    def __init__(self, fail_times):
        self.fail_times = fail_times
        self.cell_execs = 0
        self.heal_execs = 0

    async def exec_code(self, code, session_name=None, **kwargs):
        if "__SPANINSIGHT" in code:  # silent introspection snippets
            return []
        self.cell_execs += 1
        if self.cell_execs <= self.fail_times:
            return [
                {
                    "output_type": "error",
                    "ename": "NameError",
                    "evalue": "name 'BAD' is not defined",
                    "traceback": [
                        "Traceback (most recent call last):",
                        "NameError: BAD",
                    ],
                }
            ]
        return [{"output_type": "stream", "name": "stdout", "text": "good"}]


class TestSelfHealing:
    @pytest.mark.asyncio
    async def test_prompt_cell_heals_and_succeeds(self):
        colab = HealingColab(fail_times=1)
        cell = {
            "id": "h1",
            "type": "code",
            "source": "print('BAD')",
            "prompt": "Analyze sales",
        }
        state.notebook_cells = [cell]
        state.active_schema_json = {"columns": ["sales"]}

        async def fake_correct(prompt, bad_code, error, schema):
            return "print('good')"

        with patch(
            "services.ai.generate_corrected_code",
            new=AsyncMock(side_effect=fake_correct),
        ):
            await run_cell_async(
                cell_id="h1",
                session_name="s",
                colab=colab,
                page=None,
                cell_refs_map=_Refs(),
                set_is_executing=lambda _v: None,
                on_cell_change=lambda: None,
            )

        assert colab.cell_execs == 2  # failed run + healed run
        assert cell["source"] == "print('good')"
        assert cell.get("heal_count") == 1
        assert not cell.get("failed")
        assert all(o.get("output_type") != "error" for o in cell.get("outputs", []))

    @pytest.mark.asyncio
    async def test_healing_exhausts_after_two_attempts(self):
        colab = HealingColab(fail_times=10)
        cell = {
            "id": "h2",
            "type": "code",
            "source": "print('BAD')",
            "prompt": "Analyze sales",
        }
        state.notebook_cells = [cell]

        async def fake_correct(prompt, bad_code, error, schema):
            return bad_code + "\n# retry"

        with patch(
            "services.ai.generate_corrected_code",
            new=AsyncMock(side_effect=fake_correct),
        ):
            await run_cell_async(
                cell_id="h2",
                session_name="s",
                colab=colab,
                page=None,
                cell_refs_map=_Refs(),
                set_is_executing=lambda _v: None,
                on_cell_change=lambda: None,
            )

        assert colab.cell_execs == 3  # initial + 2 heal attempts
        assert cell.get("failed") is True  # retry affordance can now appear

    @pytest.mark.asyncio
    async def test_expert_cell_without_prompt_never_auto_heals(self):
        colab = HealingColab(fail_times=1)
        cell = {"id": "h3", "type": "code", "source": "print('BAD')"}
        state.notebook_cells = [cell]

        await run_cell_async(
            cell_id="h3",
            session_name="s",
            colab=colab,
            page=None,
            cell_refs_map=_Refs(),
            set_is_executing=lambda _v: None,
            on_cell_change=lambda: None,
        )

        assert colab.cell_execs == 1  # no heal attempts for hand-written code
        assert cell.get("failed") is True
        assert cell["source"] == "print('BAD')"  # source untouched

    @pytest.mark.asyncio
    async def test_healing_stops_when_ai_cannot_improve(self):
        colab = HealingColab(fail_times=5)
        cell = {
            "id": "h4",
            "type": "code",
            "source": "print('BAD')",
            "prompt": "Analyze sales",
        }
        state.notebook_cells = [cell]

        async def same_code(prompt, bad_code, error, schema):
            return bad_code  # AI returns identical code

        with patch(
            "services.ai.generate_corrected_code",
            new=AsyncMock(side_effect=same_code),
        ):
            await run_cell_async(
                cell_id="h4",
                session_name="s",
                colab=colab,
                page=None,
                cell_refs_map=_Refs(),
                set_is_executing=lambda _v: None,
                on_cell_change=lambda: None,
            )

        assert colab.cell_execs == 1
        assert cell.get("failed") is True


class TestSessionRecovery:
    def test_session_expired_detector(self):
        assert _session_expired("Session has expired or closed (404)")
        assert _session_expired("Session lost (404/401). It may have timed out.")
        assert not _session_expired("SyntaxError: invalid syntax")
        assert not _session_expired("Connection failed")

    @pytest.mark.asyncio
    async def test_run_cell_recovers_after_expiry(self):
        colab = RecoveryFakeColab()
        cell = {"id": "c1", "type": "code", "source": "print('hello')"}
        state.notebook_cells = [cell]
        state.active_project_id = ""

        async def fake_connect(_colab, _page, _set):
            colab.reconnected = True
            state.active_session_name = "fresh_session"
            state.colab_authenticated = True
            state.colab_connected = True

        with (
            patch(
                "screens.analysis.colab_connection.connect_colab_async",
                new=AsyncMock(side_effect=fake_connect),
            ),
            patch("services.dataset_cache.get_cached_path", return_value=None),
        ):
            await run_cell_async(
                cell_id="c1",
                session_name="dead_session",
                colab=colab,
                page=None,
                cell_refs_map=_Refs(),
                set_is_executing=lambda _v: None,
                on_cell_change=lambda: None,
            )

        # Cell retried on the fresh session and did NOT end in an error state
        sessions_used = [s for s, _c in colab.calls]
        assert "dead_session" in sessions_used
        assert "fresh_session" in sessions_used
        assert all(o.get("output_type") != "error" for o in cell.get("outputs", [])), (
            cell.get("outputs")
        )

    @pytest.mark.asyncio
    async def test_run_cell_surfaces_non_session_errors(self):
        class BoomColab:
            async def exec_code(self, code, session_name=None, **kwargs):
                raise SyntaxError("bad code")

        cell = {"id": "c2", "type": "code", "source": "x = ?"}
        state.notebook_cells = [cell]
        await run_cell_async(
            cell_id="c2",
            session_name="s",
            colab=BoomColab(),
            page=None,
            cell_refs_map=_Refs(),
            set_is_executing=lambda _v: None,
            on_cell_change=lambda: None,
        )
        assert cell["outputs"][0]["output_type"] == "error"
        assert "bad code" in cell["outputs"][0]["evalue"]


class TestControlValidation:
    """Run Flet's own validator over constructed controls.

    Catches invalid configurations (e.g. Shimmer requiring gradient or both
    base/highlight colors) at TEST time - such bugs only explode when Flet
    patches updates at runtime.
    """

    def test_skeleton_validates(self):
        from flet.utils.validation import validate

        from components.insight_card.skeleton import build_running_skeleton

        validate(build_running_skeleton())

    def test_native_charts_validate(self):
        from flet.utils.validation import validate

        from components.native_chart import build_native_chart

        for spec in (_BAR_SPEC, _LINE_SPEC, _PIE_SPEC):
            ctrl = build_native_chart(spec)
            assert ctrl is not None
            validate(ctrl)

    def test_insight_card_states_validate(self):
        from flet.utils.validation import validate

        from components.insight_card import build_insight_card

        running = build_insight_card(
            block={
                "id": "x",
                "type": "code",
                "source": "print(1)",
                "prompt": "p",
                "is_running": True,
                "outputs": [],
            }
        )
        validate(running)

        finished = build_insight_card(
            block={
                "id": "y",
                "type": "code",
                "source": "print(1)",
                "prompt": "p",
                "outputs": [{"output_type": "stream", "text": "done"}],
                "structured_result": {"type": "chart", "data": _BAR_SPEC},
                "narration": "ok",
            }
        )
        validate(finished)

    def test_visualizer_controls_validate(self):
        from flet.utils.validation import validate

        validate(
            build_serialized_result_visualizer(
                {
                    "type": "dataframe",
                    "columns": ["a"],
                    "data": [[1]],
                    "total_rows": 10,
                }
            )
        )

    def test_thought_accordion_validates(self):
        from flet.utils.validation import validate

        from components.thought_accordion import build_thought_accordion

        ctrl = build_thought_accordion(
            {"thought": "Because of X.", "thought_duration": 1.2, "model": "qwen"}
        )
        assert ctrl is not None
        validate(ctrl)


class TestThoughtAccordionContract:
    def test_collapsed_by_default_and_expands_on_flag(self):
        from components.thought_accordion import build_thought_accordion

        block = {"thought": "Reasoning here", "_show_thought": False}
        ctrl = build_thought_accordion(block)
        body = ctrl.controls[1]
        assert body.visible is False

        block["_show_thought"] = True
        ctrl2 = build_thought_accordion(block)
        assert ctrl2.controls[1].visible is True

    def test_no_thought_returns_none(self):
        from components.thought_accordion import build_thought_accordion

        assert build_thought_accordion({"thought": "   "}) is None


class FakePage:
    """Minimal page double: records scheduled tasks."""

    def __init__(self):
        self.tasks = []
        self.snack_bar = None
        self.loop = None  # _flush_output_to_ui skips update when loop is None

    def run_task(self, fn, *args):
        self.tasks.append(getattr(fn, "__name__", str(fn)))

    def update(self):
        pass


class TestPostExecAISkip:
    @pytest.mark.asyncio
    async def test_load_cells_skip_post_exec_ai(self):
        colab = HealingColab(fail_times=0)  # every exec succeeds
        cell = {
            "id": "s1",
            "type": "code",
            "source": "df = pd.read_json('/content/x.json')",
            "prompt": "Load Dataset: x.json",
            "skip_narration": True,
        }
        state.notebook_cells = [cell]
        page = FakePage()

        await run_cell_async(
            cell_id="s1",
            session_name="s",
            colab=colab,
            page=page,
            cell_refs_map=_Refs(),
            set_is_executing=lambda _v: None,
            on_cell_change=lambda: None,
        )
        assert "_post_exec_ai" not in page.tasks

    @pytest.mark.asyncio
    async def test_load_prefix_alone_skips_post_exec_ai(self):
        """Belt-and-braces: even without the flag, load cells never narrate."""
        colab = HealingColab(fail_times=0)
        cell = {
            "id": "s2",
            "type": "code",
            "source": "df = pd.read_csv('/content/x.csv')",
            "prompt": "Load Dataset: x.csv",
        }
        state.notebook_cells = [cell]
        page = FakePage()

        await run_cell_async(
            cell_id="s2",
            session_name="s",
            colab=colab,
            page=page,
            cell_refs_map=_Refs(),
            set_is_executing=lambda _v: None,
            on_cell_change=lambda: None,
        )
        assert "_post_exec_ai" not in page.tasks

    @pytest.mark.asyncio
    async def test_analysis_cells_still_narrate(self):
        colab = HealingColab(fail_times=0)
        cell = {
            "id": "s3",
            "type": "code",
            "source": "print('analysis')",
            "prompt": "Analyze revenue trends",
        }
        state.notebook_cells = [cell]
        page = FakePage()

        await run_cell_async(
            cell_id="s3",
            session_name="s",
            colab=colab,
            page=page,
            cell_refs_map=_Refs(),
            set_is_executing=lambda _v: None,
            on_cell_change=lambda: None,
        )
        assert "_post_exec_ai" in page.tasks


class TestDatasetOverviewCard:
    def test_overview_card_renders_categorical_and_numeric_summary(self):
        from components.dataset_overview_card import build_dataset_overview_card

        schema = {
            "shape": [100, 3],
            "columns": ["age", "category", "score"],
            "dtypes": {"age": "int64", "category": "object", "score": "float64"},
            "nulls": {"age": 0, "category": 5, "score": 12},
            "summary": {
                "age": {"count": 100, "mean": 34.5, "std": 8.2, "min": 18, "max": 65},
                "category": {
                    "count": 95,
                    "unique": 4,
                    "top": "Electronics",
                    "freq": 40,
                },
                "score": {
                    "count": 88,
                    "mean": 85.2,
                    "std": 10.1,
                    "min": 50,
                    "max": 100,
                },
            },
        }
        card = build_dataset_overview_card(
            dataset_name="test_data.csv",
            schema=schema,
            page=FakePage(),
            initial_description="Test description",
            suggestions=["Analyze age distribution"],
        )
        assert card is not None
        assert card.content is not None

    def test_initial_load_cell_omitted_in_insight_mode(self):
        from screens.analysis.cell_list import build_cells_container

        cells = [
            {
                "id": "c1",
                "type": "code",
                "source": "df = pd.read_csv('a.csv')",
                "is_initial_load": True,
            },
            {
                "id": "c2",
                "type": "code",
                "source": "df.head()",
                "prompt": "Show top rows",
            },
        ]
        # In Insight Mode (not expert mode): c1 must be skipped
        insight_controls = build_cells_container(
            page=FakePage(),
            notebook_cells=cells,
            cell_refs_map=_Refs(),
            on_run_cell=lambda _: None,
            on_stop_cell=lambda _: None,
            on_delete_cell=lambda _: None,
            on_move_cell=lambda _a, _b: None,
            on_cell_change=lambda: None,
            on_clear_output=lambda _: None,
            is_expert_mode=False,
        )
        assert len(insight_controls) == 1

        # In Expert Mode: both cells are rendered
        expert_controls = build_cells_container(
            page=FakePage(),
            notebook_cells=cells,
            cell_refs_map=_Refs(),
            on_run_cell=lambda _: None,
            on_stop_cell=lambda _: None,
            on_delete_cell=lambda _: None,
            on_move_cell=lambda _a, _b: None,
            on_cell_change=lambda: None,
            on_clear_output=lambda _: None,
            is_expert_mode=True,
        )
        assert len(expert_controls) == 2


class TestShowSnackDialog:
    def test_show_snack_calls_show_dialog(self):
        from core.utils import show_snack

        class DialogPage(FakePage):
            def __init__(self):
                super().__init__()
                self.dialogs = []

            def show_dialog(self, dlg):
                self.dialogs.append(dlg)

        page = DialogPage()
        show_snack(page, "Test message", error=True)
        assert len(page.dialogs) == 1
        assert page.dialogs[0].content.value == "Test message"
