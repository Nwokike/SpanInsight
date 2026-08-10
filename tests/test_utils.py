"""Tests for core.utils module."""

from core.utils import figure_to_png_bytes, parse_version, sanitize_numpy


class TestSanitizeNumpy:
    def test_replaces_nan_with_none(self):
        assert sanitize_numpy(float("nan")) is None

    def test_replaces_inf_with_none(self):
        assert sanitize_numpy(float("inf")) is None
        assert sanitize_numpy(float("-inf")) is None

    def test_preserves_normal_float(self):
        assert sanitize_numpy(3.14) == 3.14

    def test_preserves_int(self):
        assert sanitize_numpy(42) == 42

    def test_preserves_string(self):
        assert sanitize_numpy("hello") == "hello"

    def test_handles_nested_list(self):
        data = [1.0, float("nan"), [2.0, float("inf")]]
        result = sanitize_numpy(data)
        assert result == [1.0, None, [2.0, None]]

    def test_handles_nested_dict(self):
        data = {"a": 1.0, "b": float("nan"), "c": {"d": float("inf")}}
        result = sanitize_numpy(data)
        assert result == {"a": 1.0, "b": None, "c": {"d": None}}

    def test_handles_empty_structures(self):
        assert sanitize_numpy([]) == []
        assert sanitize_numpy({}) == {}

    def test_preserves_none(self):
        assert sanitize_numpy(None) is None

    def test_preserves_bool(self):
        assert sanitize_numpy(True) is True
        assert sanitize_numpy(False) is False


class TestParseVersion:
    def test_basic_semver(self):
        assert parse_version("1.2.3") == (1, 2, 3)

    def test_comparison(self):
        assert parse_version("2.0.0") > parse_version("1.9.9")
        assert parse_version("1.2.3") > parse_version("1.0.1")

    def test_invalid_returns_zero(self):
        assert parse_version("invalid") == (0, 0, 0)
        assert parse_version("") == (0, 0, 0)

    def test_none_returns_zero(self):
        assert parse_version(None) == (0, 0, 0)

    def test_whitespace_stripped(self):
        assert parse_version("  1.2.3  ") == (1, 2, 1)


class TestFigureToPngBytes:
    def test_returns_png_bytes(self):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        result = figure_to_png_bytes(fig)
        assert isinstance(result, bytes)
        assert len(result) > 0
        # PNG magic bytes
        assert result[:4] == b"\x89PNG"

    def test_closes_figure(self):
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([1, 2])
        num_before = len(plt.get_fignums())
        figure_to_png_bytes(fig)
        num_after = len(plt.get_fignums())
        assert num_after < num_before
