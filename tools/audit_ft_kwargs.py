"""Audit every ft.X(...) constructor call in src/ against the installed flet package.

For each call, collect keyword names and compare against the class's dataclass
fields / __init__ signature. Report any keyword the class does not accept.
Also flags calls where positional arg count exceeds the class's positional capacity
is not attempted (kwargs are the known failure mode).
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

import flet as ft


def valid_kwargs(cls) -> set[str] | None:
    """Return the set of accepted keyword names, or None if undeterminable."""
    names: set[str] = set()
    # dataclass fields
    if dataclasses.is_dataclass(cls):
        names |= {f.name for f in dataclasses.fields(cls)}
    # __init__ signature (walk MRO)
    try:
        sig = inspect.signature(cls.__init__)
        for pname, p in sig.parameters.items():
            if pname in ("self", "args", "kwargs"):
                continue
            if p.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                names.add(pname)
        if any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        ):
            return None  # accepts **kwargs -> cannot validate
    except (TypeError, ValueError):
        pass
    return names or None


def main() -> int:
    problems: list[str] = []
    checked = 0
    for py in sorted(SRC.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(), filename=str(py))
        except SyntaxError as e:
            problems.append(f"{py}: SYNTAX ERROR {e}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
            ):
                continue
            if func.value.id != "ft":
                continue
            cls = getattr(ft, func.attr, None)
            if cls is None:
                # A constructor-shaped name that does not exist in the
                # installed flet — this is exactly how runtime crashes like
                # "module flet has no attribute 'ActionChip'" happen.
                if func.attr[:1].isupper():
                    problems.append(
                        f"{py.relative_to(SRC.parent)}:{node.lineno}: "
                        f"ft.{func.attr} — DOES NOT EXIST in installed flet"
                    )
                continue
            if not isinstance(cls, type):
                continue  # enum access (ft.Icons.X handled as Attribute of Attribute) or func
            kw = valid_kwargs(cls)
            if kw is None:
                continue
            for k in node.keywords:
                if k.arg is None:
                    continue  # **kwargs spread
                checked += 1
                if k.arg not in kw:
                    problems.append(
                        f"{py.relative_to(SRC.parent)}:{node.lineno}: "
                        f"ft.{func.attr}(... {k.arg}=...) — not a valid field"
                    )
    print(f"Checked {checked} keyword args across {len(list(SRC.rglob('*.py')))} files")
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for p in problems:
            print(" ", p)
        return 1
    print("No invalid ft.* kwargs found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
