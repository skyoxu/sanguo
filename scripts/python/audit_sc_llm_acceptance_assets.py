#!/usr/bin/env python
"""
Audit script dependencies and referenced assets (scripts/docs) for selected tooling scripts.

Scope:
- Target scripts:
  1) scripts/sc/acceptance_check.py
  2) scripts/sc/llm_review.py
  3) scripts/sc/llm_generate_tests_from_acceptance_refs.py
  4) scripts/python/migrate_task_optional_hints_to_views.py
  5) scripts/sc/llm_align_acceptance_semantics.py
  6) scripts/sc/llm_check_subtasks_coverage.py
  7) scripts/sc/llm_semantic_gate_all.py
  8) scripts/sc/llm_fill_acceptance_refs.py

Checks:
- File exists
- Python import dependencies (internal modules only) exist
- Referenced repo-relative paths (docs/*.md, scripts/*.py) exist
- Write a JSON report under logs/ci/<YYYY-MM-DD>/audit-sc-llm-acceptance-assets.json

Notes:
- Standard library only.
- UTF-8 read/write.
- Console output is ASCII-only to avoid Windows codepage issues.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


TARGET_SCRIPTS = [
    "scripts/sc/acceptance_check.py",
    "scripts/sc/llm_review.py",
    "scripts/sc/llm_generate_tests_from_acceptance_refs.py",
    "scripts/python/migrate_task_optional_hints_to_views.py",
    "scripts/sc/llm_align_acceptance_semantics.py",
    "scripts/sc/llm_check_subtasks_coverage.py",
    "scripts/sc/llm_semantic_gate_all.py",
    "scripts/sc/llm_fill_acceptance_refs.py",
]


RE_PATH_TOKEN = re.compile(
    r"(?P<path>(?:docs|scripts)/[A-Za-z0-9_./\\-]+?\.(?:md|py))"
)
RE_BACKTICK_PATH = re.compile(
    r"`(?P<path>(?:docs|scripts)/[A-Za-z0-9_./\\-]+?\.(?:md|py))`"
)


def _date_dir(root: Path) -> Path:
    return root / "logs" / "ci" / datetime.now().strftime("%Y-%m-%d")


def _read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _norm_rel(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _path_exists(root: Path, rel_path: str) -> bool:
    return (root / Path(rel_path)).exists()


def _is_placeholder_path(path: str) -> bool:
    # Allow templated placeholders in docs like logs/ci/<date>/... or <id>
    return "<" in path and ">" in path


def _iter_referenced_paths(text: str) -> set[str]:
    hits: set[str] = set()
    for m in RE_PATH_TOKEN.finditer(text):
        hits.add(_norm_rel(m.group("path")))
    for m in RE_BACKTICK_PATH.finditer(text):
        hits.add(_norm_rel(m.group("path")))
    return hits


@dataclass(frozen=True)
class ImportRef:
    module: str
    name: str | None  # for from-import
    lineno: int


def _parse_imports(text: str, filename: str) -> tuple[list[ImportRef], str | None]:
    try:
        tree = ast.parse(text, filename=filename)
    except SyntaxError as ex:
        return [], f"SyntaxError:{ex.msg}@{ex.lineno}"

    refs: list[ImportRef] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                refs.append(ImportRef(module=alias.name, name=None, lineno=getattr(node, "lineno", 0)))
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            # Relative imports: represent as ".foo" etc.
            mod = ("." * int(node.level or 0)) + node.module
            for alias in node.names:
                refs.append(ImportRef(module=mod, name=alias.name, lineno=getattr(node, "lineno", 0)))
    return refs, None


def _module_to_candidate_paths(script_path: str, module: str) -> list[str]:
    """
    Resolve internal module references to possible file paths.
    - For absolute internal modules like 'scripts.sc._risk_summary' -> scripts/sc/_risk_summary.py
    - For relative imports like '. _step_result' within scripts/sc/* -> scripts/sc/_step_result.py
    """
    candidates: list[str] = []
    script_rel = _norm_rel(script_path)

    if module.startswith("."):
        # Relative to script directory
        base_dir = "/".join(script_rel.split("/")[:-1])
        mod = module.lstrip(".")
        if not mod:
            return candidates
        candidates.append(f"{base_dir}/{mod.replace('.', '/')}.py")
        candidates.append(f"{base_dir}/{mod.replace('.', '/')}/__init__.py")
        return candidates

    # Absolute import
    candidates.append(f"{module.replace('.', '/')}.py")
    candidates.append(f"{module.replace('.', '/')}/__init__.py")
    return candidates


def _is_internal_module(module: str) -> bool:
    # Treat scripts.* as internal. Also treat relative imports as internal.
    return module.startswith("scripts.") or module.startswith(".")


def audit(root: Path) -> dict[str, object]:
    results: list[dict[str, object]] = []
    ok = True

    for rel in TARGET_SCRIPTS:
        item: dict[str, object] = {"path": rel, "exists": False, "issues": [], "imports": [], "refs": []}
        script_path = root / Path(rel)
        if not script_path.exists():
            item["issues"].append({"type": "missing_script"})
            ok = False
            results.append(item)
            continue

        item["exists"] = True
        text = _read_utf8(script_path)

        # 1) Parse imports and validate internal import targets exist.
        import_refs, parse_err = _parse_imports(text, rel)
        if parse_err:
            item["issues"].append({"type": "parse_error", "detail": parse_err})
            ok = False
        missing_internal_imports: list[dict[str, object]] = []
        for ir in import_refs:
            item["imports"].append({"module": ir.module, "name": ir.name, "lineno": ir.lineno})
            if not _is_internal_module(ir.module):
                continue
            candidates = _module_to_candidate_paths(rel, ir.module)
            if not candidates:
                continue
            found = any(_path_exists(root, c) for c in candidates)
            if not found:
                missing_internal_imports.append(
                    {"module": ir.module, "lineno": ir.lineno, "candidates": candidates}
                )
        if missing_internal_imports:
            item["issues"].append({"type": "missing_internal_imports", "items": missing_internal_imports})
            ok = False

        # 2) Find referenced repo-relative docs/scripts paths in the file and validate they exist.
        referenced_paths = sorted(_iter_referenced_paths(text))
        missing_refs: list[str] = []
        for p in referenced_paths:
            item["refs"].append(p)
            if _is_placeholder_path(p):
                continue
            if not _path_exists(root, p):
                missing_refs.append(p)
        if missing_refs:
            item["issues"].append({"type": "missing_referenced_paths", "items": missing_refs})
            ok = False

        results.append(item)

    return {"ok": ok, "targets": TARGET_SCRIPTS, "results": results}


def main(argv: list[str] | None = None) -> int:
    root = Path(".").resolve()
    report = audit(root)

    out_dir = _date_dir(root)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "audit-sc-llm-acceptance-assets.json"
    _write_utf8(out_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    status = "OK" if report.get("ok") else "FAIL"
    print(f"audit_sc_llm_acceptance_assets: {status}")
    print(f"report={out_path.as_posix()}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

