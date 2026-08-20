"""Audit every in-project function call in src/ for invalid keyword arguments.

Complements audit_ft_kwargs.py (which covers ft.* constructors). This one
builds a map of all function defs in src/ and checks every call-by-name for
kwargs the definition doesn't accept. Reports name-collision ambiguity rather
than guessing.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def collect_defs() -> dict[str, list[tuple[Path, set[str], bool]]]:
    """name -> list of (file, accepted_kwargs, has_var_keyword)."""
    defs: dict[str, list[tuple[Path, set[str], bool]]] = {}
    for py in sorted(SRC.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(), filename=str(py))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                names = {a.arg for a in args.args + args.kwonlyargs + args.posonlyargs}
                names.discard("self")
                names.discard("cls")
                has_vk = args.kwarg is not None
                defs.setdefault(node.name, []).append((py, names, has_vk))
    return defs


def main() -> int:
    defs = collect_defs()
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
            # direct name call: foo(...)
            if isinstance(func, ast.Name):
                name = func.id
            # attribute call where we can still match by method name: x.foo(...)
            elif isinstance(func, ast.Attribute):
                name = func.attr
            else:
                continue
            cands = defs.get(name)
            if not cands:
                continue
            # skip if any candidate accepts **kwargs (can't disprove)
            if any(has_vk for _, _, has_vk in cands):
                continue
            # union of accepted kwargs across same-named defs; if the sets
            # disagree we still flag kwargs accepted by NONE of them
            accepted_union = set().union(*(names for _, names, _ in cands))
            for k in node.keywords:
                if k.arg is None:
                    continue
                checked += 1
                if k.arg not in accepted_union:
                    locs = ", ".join(
                        str(p.relative_to(SRC.parent)) for p, _, _ in cands
                    )
                    problems.append(
                        f"{py.relative_to(SRC.parent)}:{node.lineno}: "
                        f"{name}(... {k.arg}=...) — not accepted by def(s) in: {locs}"
                    )
    print(f"Checked {checked} keyword args on in-project functions")
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for p in problems:
            print(" ", p)
        return 1
    print("No invalid in-project call kwargs found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
