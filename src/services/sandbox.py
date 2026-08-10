"""Local code execution sandbox — runs analysis code safely against a DataFrame.

This module executes user/AI-generated Python code in an isolated namespace
with the user's DataFrame pre-loaded as `df`. Results include stdout,
modified DataFrames, and matplotlib figures.
"""

from __future__ import annotations

import asyncio
import io
import logging
import sys
import traceback
from typing import Any

logger = logging.getLogger(__name__)


def execute_code(code: str, df=None) -> dict[str, Any]:
    """Execute Python code in a sandboxed namespace.

    Args:
        code: Python source code to execute.
        df: Optional pandas DataFrame available as `df` in the code.

    Returns:
        Dict with keys:
        - stdout: captured print output
        - df: the (possibly modified) DataFrame
        - figures: list of matplotlib Figure objects
        - error: error message if execution failed, else None
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    namespace: dict[str, Any] = {"__builtins__": __builtins__}

    # Pre-load common data science imports
    try:
        import numpy as np
        import pandas as pd

        namespace["pd"] = pd
        namespace["np"] = np
    except ImportError:
        pass

    if df is not None:
        namespace["df"] = df.copy()

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured = io.StringIO()

    plt.close("all")

    result = {
        "stdout": "",
        "df": df,
        "figures": [],
        "error": None,
    }

    try:
        exec(code, namespace)  # noqa: S102

        result["stdout"] = captured.getvalue()

        # Check if df was modified
        if "df" in namespace:
            result["df"] = namespace["df"]

        # Collect any matplotlib figures
        figs = [plt.figure(i) for i in plt.get_fignums()]
        result["figures"] = figs

    except Exception:
        result["error"] = traceback.format_exc()
        result["stdout"] = captured.getvalue()
    finally:
        sys.stdout = old_stdout

    return result


async def execute_code_async(code: str, df=None) -> dict[str, Any]:
    """Async wrapper around execute_code — runs in a thread to avoid blocking."""
    return await asyncio.to_thread(execute_code, code, df)
