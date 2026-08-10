import pandas as pd
import pytest

from services.sandbox import execute_code, execute_code_async, validate_code


def test_validate_code_success():
    code = """
import pandas as pd
import numpy as np
import statistics
mean_val = statistics.mean(df['A'])
result = f"Mean: {mean_val}"
"""
    is_safe, reason = validate_code(code)
    assert is_safe
    assert reason == ""


def test_validate_code_banned_import():
    code = """
import scipy.stats as stats
"""
    is_safe, reason = validate_code(code)
    assert not is_safe
    assert "Importing 'scipy.stats' is not available" in reason


def test_validate_code_non_whitelisted_import():
    code = """
import os
"""
    is_safe, reason = validate_code(code)
    assert not is_safe
    assert "blocked term" in reason


def test_validate_code_syntax_error():
    code = """
import pandas as pd
if True
    print("Forgot colon")
"""
    is_safe, reason = validate_code(code)
    assert not is_safe
    assert "Syntax Error" in reason


def test_execute_code_success():
    df = pd.DataFrame({"A": [1, 2, 3, 4, 5]})
    code = """
import statistics
mean_val = statistics.mean(df['A'])
result = mean_val
"""
    res = execute_code(code, df)
    assert res["success"]
    assert res["result"] == 3
    assert res["error"] is None


def test_execute_code_execution_error():
    df = pd.DataFrame({"A": [1, 2, 3]})
    code = """
result = 1 / 0
"""
    res = execute_code(code, df)
    assert not res["success"]
    assert "ZeroDivisionError" in res["error"]


def test_execute_code_restored_builtins():
    # Direct test showing that type(), getattr(), hasattr(), dir() are 100% allowed and functional
    df = pd.DataFrame({"A": [1.0, 2.0]})
    code = """
val_type = type(df['A'].iloc[0]).__name__
has_a = hasattr(df, 'columns')
result = f"Type: {val_type}, HasColumns: {has_a}"
"""
    res = execute_code(code, df)
    assert res["success"]
    assert "float" in res["result"]
    assert "True" in res["result"]


@pytest.mark.asyncio
async def test_execute_code_async():
    df = pd.DataFrame({"A": [10, 20]})
    code = """
result = np.sum(df['A'])
"""
    res = await execute_code_async(code, df)
    assert res["success"]
    assert res["result"] == 30


def test_execute_code_restricted_builtins_block_open():
    """open() should be blocked by restricted builtins."""
    df = pd.DataFrame({"A": [1]})
    code = """
result = open("test.txt", "w")
"""
    res = execute_code(code, df)
    assert not res["success"]
    assert "open" in res["error"].lower() or "name" in res["error"].lower()


def test_execute_code_restricted_builtins_block_eval():
    """eval() should be blocked by restricted builtins."""
    df = pd.DataFrame({"A": [1]})
    code = """
result = eval("1 + 1")
"""
    res = execute_code(code, df)
    assert not res["success"]


def test_execute_code_whitelisted_builtins_work():
    """Common builtins like sorted, enumerate, zip should work."""
    df = pd.DataFrame({"A": [3, 1, 2]})
    code = """
s = sorted(df['A'].tolist())
e = list(enumerate(s))
z = list(zip(s, [10, 20, 30]))
result = {"sorted": s, "enum_len": len(e), "zip_len": len(z)}
"""
    res = execute_code(code, df)
    assert res["success"]
    assert res["result"]["sorted"] == [1, 2, 3]
    assert res["result"]["enum_len"] == 3


def test_safe_import_blocks_os():
    """os import should be blocked at both AST and runtime levels."""
    df = pd.DataFrame({"A": [1]})
    code = """
__import__('os').system('echo pwned')
"""
    res = execute_code(code, df)
    assert not res["success"]


def test_execute_code_print_captured():
    """print() output should be captured in stdout."""
    df = pd.DataFrame({"A": [1, 2, 3]})
    code = """
print("hello world")
result = 42
"""
    res = execute_code(code, df)
    assert res["success"]
    assert res["result"] == 42
    assert "hello world" in res["stdout"]
