from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from _csharp_test_conventions import validate_csharp_test_file  # noqa: E402


_GD_FUNC_RE = re.compile(r"^\s*func\s+(test_[a-z0-9_]+)\s*\(")


def _validate_csharp(ref: str, content: str) -> list[str]:
    return [str(item.get("message") or "") for item in validate_csharp_test_file(ref=ref, content=content)]


def _validate_gdscript(ref: str, content: str) -> list[str]:
    errors: list[str] = []
    file_name = Path(ref).name
    if not re.match(r"^test_[a-z0-9_]+\.gd$", file_name):
        errors.append(f"GDScript test file must use test_<behavior>.gd naming: {file_name}")

    found_test_func = False
    for line in content.replace("\r\n", "\n").split("\n"):
        func_match = _GD_FUNC_RE.match(line)
        if not func_match:
            continue
        found_test_func = True
    if not found_test_func:
        errors.append("generated GDScript test file must contain at least one func test_<behavior>(...)")
    return errors


def validate_generated_test_content(*, ref: str, content: str) -> tuple[bool, list[str]]:
    normalized_ref = str(ref or "").strip().replace("\\", "/")
    ext = Path(normalized_ref).suffix.lower()
    if ext == ".cs":
        errors = _validate_csharp(normalized_ref, content)
    elif ext == ".gd":
        errors = _validate_gdscript(normalized_ref, content)
    else:
        errors = [f"unsupported generated test extension: {ext or '<missing>'}"]
    return not errors, errors
