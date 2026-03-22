from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_PASCAL_CASE_RE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_CAMEL_CASE_RE = re.compile(r"^[a-z][A-Za-z0-9]*$")
_SHOULD_WHEN_RE = re.compile(r"^Should[A-Z][A-Za-z0-9]*_When[A-Z][A-Za-z0-9]*$")
_TEST_ATTR_RE = re.compile(r"^\s*\[(?:Fact|Theory)(?:\s*\(.*\))?\]\s*$")
_CLASS_RE = re.compile(
    r"\b(?:public|internal)\s+(?:sealed\s+|abstract\s+|static\s+|partial\s+)*class\s+([A-Za-z_][A-Za-z0-9_]*)\b"
)
_METHOD_RE = re.compile(
    r"\b(?:public|private|internal|protected)\s+(?:static\s+)?(?:async\s+)?(?:void|Task(?:<[^>]+>)?|bool|byte|sbyte|short|ushort|int|uint|long|ulong|float|double|decimal|string|char|object|[A-Z][A-Za-z0-9_<>,.?]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)
_LOCAL_RE = re.compile(
    r"^\s*(?:var|bool|byte|sbyte|short|ushort|int|uint|long|ulong|float|double|decimal|string|char|object|Task(?:<[^>]+>)?|[A-Z][A-Za-z0-9_<>,.?]+)\s+([A-Za-z_][A-Za-z0-9_]*)\s*="
)


def is_pascal_case(name: str) -> bool:
    return bool(_PASCAL_CASE_RE.match(str(name or "").strip()))


def is_camel_case(name: str) -> bool:
    return bool(_CAMEL_CASE_RE.match(str(name or "").strip()))


def is_should_when(name: str) -> bool:
    return bool(_SHOULD_WHEN_RE.match(str(name or "").strip()))


def _line_number_for_match(content: str, pattern: re.Pattern[str]) -> tuple[int, re.Match[str] | None]:
    for index, line in enumerate(content.replace("\r\n", "\n").split("\n"), start=1):
        match = pattern.search(line)
        if match:
            return index, match
    return 1, None


def validate_csharp_test_file(*, ref: str, content: str) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    normalized_ref = str(ref or "").strip().replace("\\", "/")
    file_name = Path(normalized_ref).name
    stem = Path(normalized_ref).stem
    lines = content.replace("\r\n", "\n").split("\n")

    if not file_name.endswith("Tests.cs") or not is_pascal_case(stem):
        violations.append(
            {
                "line": 1,
                "rule": "file_name",
                "message": f"file name must be PascalCase and end with Tests.cs: {file_name}",
            }
        )

    class_line, class_match = _line_number_for_match(content, _CLASS_RE)
    if class_match is None:
        violations.append({"line": 1, "rule": "class_name", "message": "class name not found in generated C# test file"})
    else:
        class_name = class_match.group(1)
        if not is_pascal_case(class_name):
            violations.append({"line": class_line, "rule": "class_name", "message": f"class name must be PascalCase: {class_name}"})
        if stem and class_name != stem:
            violations.append(
                {
                    "line": class_line,
                    "rule": "class_name_match",
                    "message": f"class name must match file stem: {class_name} != {stem}",
                }
            )

    found_test_method = False
    for index, line in enumerate(lines, start=1):
        method_match = _METHOD_RE.search(line.strip())
        if not method_match:
            continue
        method_name = method_match.group(1)
        prior_window = lines[max(0, index - 6) : index - 1]
        is_test_method = any(_TEST_ATTR_RE.match(item.strip()) for item in prior_window)
        if is_test_method:
            found_test_method = True
            if not is_should_when(method_name):
                violations.append(
                    {
                        "line": index,
                        "rule": "test_method_name",
                        "message": f"test method must use ShouldX_WhenY naming: {method_name}",
                    }
                )
        elif not is_pascal_case(method_name):
            violations.append(
                {
                    "line": index,
                    "rule": "helper_method_name",
                    "message": f"helper method must use PascalCase: {method_name}",
                }
            )

    if not found_test_method:
        violations.append(
            {
                "line": 1,
                "rule": "missing_test_method",
                "message": "at least one [Fact]/[Theory] test method is required",
            }
        )

    for index, line in enumerate(lines, start=1):
        local_match = _LOCAL_RE.match(line)
        if not local_match:
            continue
        local_name = local_match.group(1)
        if local_name == "_":
            continue
        if not is_camel_case(local_name):
            violations.append(
                {
                    "line": index,
                    "rule": "local_variable_name",
                    "message": f"local variable must use camelCase: {local_name}",
                }
            )

    return violations
