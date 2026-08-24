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


# Kernel-side serializer for the cell ``result`` variable.
#
# Every supported type converts to a TYPED payload the app renders natively:
#   DataFrame -> {"type":"dataframe"}   Series -> {"type":"series"}
#   ndarray   -> {"type":"ndarray"}     Figure/PIL -> {"type":"chart","png_b64"}
#   scalars (incl. numpy/datetime)  -> {"type":"scalar"}
# Nested occurrences (a DataFrame inside a dict/list) get the SAME treatment -
# they are never left for json.dumps(default=str) to stringify into giant repr
# blobs. Unknown objects degrade to a TRUNCATED string, never an unbounded one.
# All caps bound the payload size; every branch is exception-guarded so a bad
# object can never break the user's cell.
_RESULT_CODE_TEMPLATE = """
import json, math
import base64 as _si_b64
import io as _si_io

_SI_STR_LIMIT = 200
_SI_LIST_CAP = 100
_SI_NP_CAP = 50
_SI_ROW_CAP = 20
_SI_MAX_DEPTH = 4


def _si_trunc(_v):
    _s = str(_v)
    return _s if len(_s) <= _SI_STR_LIMIT else _s[:_SI_STR_LIMIT] + "\\u2026"


def _si_png_payload(_png_bytes):
    return {
        "type": "chart",
        "png_b64": _si_b64.b64encode(_png_bytes).decode("utf-8"),
    }


def _si_fig_png(_obj):
    try:
        _fig = _obj.get_figure() if hasattr(_obj, "get_figure") else _obj
        _buf = _si_io.BytesIO()
        _fig.savefig(_buf, format="png", bbox_inches="tight")
        return _si_png_payload(_buf.getvalue())
    except Exception:
        return None


def _si_pil_png(_obj):
    try:
        _buf = _si_io.BytesIO()
        _obj.save(_buf, format="PNG")
        return _si_png_payload(_buf.getvalue())
    except Exception:
        return None


def _si_df(_df):
    try:
        _cols = []
        for _c in _df.columns:
            if isinstance(_c, tuple):
                _cols.append(" \\u00b7 ".join(str(_x) for _x in _c))
            else:
                _cols.append(str(_c))
        _ncols = len(_df.columns)
        _rows = []
        for _, _r in _df.head(_SI_ROW_CAP).iterrows():
            _rows.append([_si_clean(_r.iloc[_i], 1) for _i in range(_ncols)])
        return {
            "type": "dataframe",
            "columns": _cols,
            "data": _rows,
            "total_rows": int(len(_df)),
        }
    except Exception:
        return None


def _si_series(_s):
    try:
        return {
            "type": "series",
            "name": str(getattr(_s, "name", "") or "Value"),
            "index": [str(_i) for _i in list(_s.index)[:_SI_ROW_CAP]],
            "data": [_si_clean(_x, 1) for _x in list(_s.values)[:_SI_ROW_CAP]],
            "total_rows": int(len(_s)),
        }
    except Exception:
        return None


def _si_clean(v, depth=0):
    # numpy FIRST: np.int64 subclasses int and np.float64 subclasses float,
    # so the plain-python checks below would otherwise miss them.
    try:
        import numpy as _np

        if isinstance(v, _np.generic):
            return _si_clean(v.item(), depth + 1)
        if isinstance(v, _np.ndarray):
            return {
                "type": "ndarray",
                "shape": [int(x) for x in v.shape],
                "data": [_si_clean(x, depth + 1) for x in v.ravel()[:_SI_NP_CAP]],
            }
    except Exception:
        pass
    if v is None or isinstance(v, bool) or isinstance(v, str):
        return v
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else v
    if depth > _SI_MAX_DEPTH:
        return _si_trunc(v)
    try:
        import pandas as _pd

        if isinstance(v, _pd.DataFrame):
            return _si_df(v)
        if isinstance(v, _pd.Series):
            return _si_series(v)
        if isinstance(v, _pd.Index):
            return _si_series(_pd.Series(v))
    except Exception:
        pass
    _tn = type(v).__name__
    if _tn == "Styler":
        try:
            return _si_clean(v.data, depth + 1)
        except Exception:
            return _si_trunc(v)
    if hasattr(v, "savefig") and hasattr(v, "canvas"):
        _p = _si_fig_png(v)
        return _p if _p is not None else _si_trunc(v)
    if _tn == "Image" and hasattr(v, "save"):
        _p = _si_pil_png(v)
        return _p if _p is not None else _si_trunc(v)
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return _si_trunc(v)
    if isinstance(v, dict):
        return {
            str(k): _si_clean(x, depth + 1)
            for k, x in list(v.items())[:_SI_LIST_CAP]
        }
    if isinstance(v, (list, tuple, set, frozenset)):
        return [_si_clean(x, depth + 1) for x in list(v)[:_SI_LIST_CAP]]
    if isinstance(v, (bytes, bytearray)):
        return "<%d bytes>" % len(v)
    return _si_trunc(v)


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
            _buf = _si_io.BytesIO()
            _fig.tight_layout()
            _fig.savefig(_buf, format="png", bbox_inches="tight")
            _plt.close(_fig)
            _png = _si_b64.b64encode(_buf.getvalue()).decode("utf-8")
        except Exception:
            _png = None
        _out = {"type": "chart", "data": _si_clean(_spec), "png_b64": _png}
    elif isinstance(_r, dict):
        _out = {"type": "dict", "data": _si_clean(_r)}
    elif isinstance(_r, (list, tuple)):
        _out = {
            "type": "list",
            "data": _si_clean(list(_r)),
            "total_rows": len(_r),
        }
    elif _r is not None:
        # DataFrame / Series / ndarray / Figure / PIL / datetime / unknown all
        # flow through _si_clean, which returns a TYPED payload when it
        # recognizes the object.
        _c = _si_clean(_r)
        if isinstance(_c, dict) and "type" in _c:
            _out = _c
        else:
            _out = {"type": "scalar", "data": _c}
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
