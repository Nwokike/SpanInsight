"""Silent kernel introspection - schema extraction code executed on Colab.

The code generated here runs INSIDE the Colab kernel and must be defensive by
design: it never assumes a variable named ``df`` exists (zip/sqlite/image
loads produce other variables), always prints its START/END markers, and
reports failures inside the JSON payload so the app can show the real reason
instead of failing silently.
"""

from __future__ import annotations

from services.colab.output_utils import extract_error_text, parse_marker_json

SCHEMA_MARKER = "SPANINSIGHT_SCHEMA"
RESULT_MARKER = "SPANINSIGHT_RESULT"

_SCHEMA_CODE_TEMPLATE = """
import json, math
def _si_clean(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, dict):
        return {str(k): _si_clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_si_clean(x) for x in v]
    return v

_schema = {"kind": "none", "error": None}
try:
    _cand = None
    for _name in ("df", "result", "data"):
        _v = globals().get(_name)
        if _v is not None and hasattr(_v, "columns") and hasattr(_v, "dtypes"):
            _cand = _v
            _schema["kind"] = "dataframe"
            break
    if _cand is not None:
        _schema["shape"] = [int(_cand.shape[0]), int(_cand.shape[1])]
        _schema["columns"] = [str(c) for c in _cand.columns]
        _schema["dtypes"] = {str(k): str(v) for k, v in _cand.dtypes.items()}
        _schema["nulls"] = {str(k): int(v) for k, v in _cand.isnull().sum().items()}
        _head_recs = _cand.head(5).to_dict(orient="records")
        _schema["head"] = _si_clean(_head_recs)
        try:
            _raw_summary = _cand.describe(include="all").to_dict()
        except Exception:
            _raw_summary = _cand.describe().to_dict()
        _schema["summary"] = _si_clean(_raw_summary)
    else:
        _arr = globals().get("data")
        if _arr is not None and hasattr(_arr, "shape"):
            _schema["kind"] = "array"
            _schema["shape"] = [int(x) for x in _arr.shape]
            _schema["dtype"] = str(getattr(_arr, "dtype", ""))
        elif _arr is not None and hasattr(_arr, "files"):
            _schema["kind"] = "npz"
            _schema["keys"] = [str(k) for k in _arr.files]
            _schema["error"] = "Archive loaded. Analyze a member array for schema."
        else:
            _schema["error"] = (
                "No tabular dataset (df) found in the session after loading this file."
            )
except Exception as _ex:
    _schema = {"kind": "none", "error": type(_ex).__name__ + ": " + str(_ex)}
print('__SPANINSIGHT_SCHEMA_START__')
print(json.dumps(_schema, default=str))
print('__SPANINSIGHT_SCHEMA_END__')
"""


def build_schema_extraction_code() -> str:
    """Python source executed silently on Colab to extract the active dataset schema."""
    return _SCHEMA_CODE_TEMPLATE


def parse_schema_from_outputs(outputs) -> tuple[dict | None, str | None]:
    """Parse schema execution outputs into (schema_dict, error_message).

    - (schema, None): schema extracted successfully
    - (None, message): extraction failed or payload malformed
    - (None, None): markers never printed (execution died before printing)
    """
    schema, parse_error = parse_marker_json(outputs, SCHEMA_MARKER)
    if parse_error:
        return None, parse_error
    if schema is None:
        kernel_error = extract_error_text(outputs)
        if kernel_error:
            return None, f"Schema execution failed on Colab: {kernel_error}"
        # The hardened schema code always prints its markers - no markers and
        # no error means the execution itself died (timeout / kernel crash).
        return (
            None,
            "Schema extraction produced no result - the Colab kernel may have timed out or crashed.",
        )

    remote_error = schema.get("error")
    if remote_error:
        return None, str(remote_error)
    if schema.get("kind") != "dataframe":
        return None, schema.get("error") or "Loaded file is not a tabular dataset."
    if not schema.get("columns"):
        return None, "Dataset loaded but has no columns."
    return schema, None


_RESULT_CODE_TEMPLATE = """
import json, math
def _si_clean(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, dict):
        return {str(k): _si_clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_si_clean(x) for x in v]
    return v
_out = None
try:
    _r = globals().get("result")
    if _r is None:
        # Models often display the final table instead of assigning `result`;
        # IPython keeps the last displayed expression in `_`.
        _r = globals().get("_")
    if isinstance(_r, dict) and "chart" in _r:
        _spec = _r["chart"]
        _png = None
        try:
            # NOTE: never switch the kernel-wide backend - user cells rely on
            # the inline backend. savefig() to a buffer works under any backend.
            import matplotlib.pyplot as _plt
            import base64 as _b64
            import io as _io
            _fig, _ax = _plt.subplots(figsize=(8, 4.5), dpi=110)
            _t = str(_spec.get("type", "bar")).lower()
            _xs = [str(x) for x in (_spec.get("x") or [])]
            _sers = _spec.get("series") or []
            if _t == "pie":
                _vals = [float(v) for v in ((_sers[0].get("y") if _sers else None) or _spec.get("values") or []) if isinstance(v, (int, float))]
                _ax.pie(_vals, labels=_xs[:len(_vals)] or None, autopct="%1.0f%%")
            else:
                for _s in _sers:
                    _ys = [float(v) if isinstance(v, (int, float)) else 0.0 for v in (_s.get("y") or [])]
                    if _t == "line":
                        _ax.plot(range(len(_ys)), _ys, marker="o", label=str(_s.get("name", "")))
                    else:
                        _ax.bar(range(len(_ys)), _ys, label=str(_s.get("name", "")))
                if _xs:
                    _step = max(1, len(_xs) // 12)
                    _ax.set_xticks(range(0, len(_xs), _step))
                    _ax.set_xticklabels(_xs[::_step], rotation=30, ha="right")
                _ax.legend()
            _ax.set_title(str(_spec.get("title", "")))
            _buf = _io.BytesIO()
            _fig.tight_layout()
            _fig.savefig(_buf, format="png", bbox_inches="tight")
            _plt.close(_fig)
            _png = _b64.b64encode(_buf.getvalue()).decode("utf-8")
        except Exception:
            _png = None
        _out = {"type": "chart", "data": _si_clean(_spec), "png_b64": _png}
    elif _r is not None and hasattr(_r, "columns") and hasattr(_r, "head"):
        _rows = []
        for _rec in _r.head(20).to_dict(orient="records"):
            _rows.append([_si_clean(_rec.get(c)) for c in _r.columns])
        _out = {"type": "dataframe", "columns": [str(c) for c in _r.columns],
                "data": _rows, "total_rows": int(len(_r))}
    elif _r is not None and hasattr(_r, "index") and not hasattr(_r, "columns"):
        _out = {"type": "series", "name": str(getattr(_r, "name", "") or "Value"),
                "index": [str(i) for i in list(_r.index)[:20]],
                "data": [_si_clean(x) for x in list(_r.values)[:20]],
                "total_rows": int(len(_r))}
    elif _r is not None and hasattr(_r, "shape") and hasattr(_r, "ravel"):
        _out = {"type": "ndarray", "data": [_si_clean(x) for x in list(_r.ravel())[:50]],
                "shape": [int(x) for x in _r.shape]}
    elif isinstance(_r, dict):
        _out = {"type": "dict", "data": _si_clean(_r)}
    elif isinstance(_r, (list, tuple)):
        _out = {"type": "list", "data": _si_clean(list(_r))}
    elif isinstance(_r, (int, float, str, bool)):
        _out = {"type": "scalar", "data": _si_clean(_r)}
except Exception as _ex:
    _out = {"type": "error", "error": type(_ex).__name__ + ": " + str(_ex)}
if _out is not None:
    print('__SPANINSIGHT_RESULT_START__')
    print(json.dumps(_out, default=str))
    print('__SPANINSIGHT_RESULT_END__')
"""


def build_result_serialization_code() -> str:
    """Python source executed silently after a cell to serialize ``result``."""
    return _RESULT_CODE_TEMPLATE


def parse_result_from_outputs(outputs) -> dict | None:
    """Parse the result payload from serializer outputs; None when absent/unusable."""
    payload, parse_error = parse_marker_json(outputs, RESULT_MARKER)
    if parse_error or payload is None:
        return None
    if payload.get("type") == "error":
        return None
    return payload
