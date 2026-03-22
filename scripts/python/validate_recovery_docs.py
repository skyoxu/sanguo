#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

EXECUTION_PLAN_FIELDS = [
    "Title",
    "Status",
    "Branch",
    "Git Head",
    "Goal",
    "Scope",
    "Current step",
    "Last completed step",
    "Stop-loss",
    "Next action",
    "Recovery command",
    "Open questions",
    "Exit criteria",
    "Related ADRs",
    "Related decision logs",
    "Related task id(s)",
    "Related run id",
    "Related latest.json",
    "Related pipeline artifacts",
]

DECISION_LOG_FIELDS = [
    "Title",
    "Date",
    "Status",
    "Supersedes",
    "Superseded by",
    "Branch",
    "Git Head",
    "Why now",
    "Context",
    "Decision",
    "Consequences",
    "Recovery impact",
    "Validation",
    "Related ADRs",
    "Related execution plans",
    "Related task id(s)",
    "Related run id",
    "Related latest.json",
    "Related pipeline artifacts",
]

FIELD_LINE_RE = re.compile(r"^- ([^:]+):\s*(.*)$")
BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")
HEX_RE = re.compile(r"^[0-9a-f]{7,40}$")


def parse_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = FIELD_LINE_RE.match(raw_line.strip())
        if not match:
            continue
        fields[match.group(1).strip()] = match.group(2).strip()
    return fields


def is_template(path: Path) -> bool:
    return path.name.upper() == "TEMPLATE.MD"


def is_readme(path: Path) -> bool:
    return path.name.upper() == "README.MD"


def check_required_fields(path: Path, fields: dict[str, str], required: list[str], *, allow_blank: bool) -> list[str]:
    errors: list[str] = []
    for key in required:
        if key not in fields:
            errors.append(f"{path}: missing field '{key}'")
            continue
        value = fields[key]
        if not allow_blank and not value:
            errors.append(f"{path}: field '{key}' must not be blank")
    return errors


def check_na_reason(path: Path, fields: dict[str, str], keys: list[str]) -> list[str]:
    errors: list[str] = []
    for key in keys:
        value = str(fields.get(key, "")).strip()
        lower = value.lower()
        if lower == "n/a":
            errors.append(f"{path}: field '{key}' must explain why it is n/a")
    return errors


def check_git_head(path: Path, value: str) -> list[str]:
    value = str(value).strip()
    if not value:
        return [f"{path}: field 'Git Head' must not be blank"]
    if value.lower().startswith("n/a"):
        return []
    if HEX_RE.fullmatch(value):
        return []
    return [f"{path}: field 'Git Head' must be a git hash or an explained n/a"]


def extract_repo_paths(value: str) -> list[str]:
    items = [match.group(1).strip() for match in BACKTICK_PATH_RE.finditer(value)]
    if items:
        return [item for item in items if item]
    text = str(value).strip()
    if not text or text.lower().startswith("n/a"):
        return []
    if any(sep in text for sep in [",", ";"]):
        return []
    if " " in text and not text.endswith(".md") and not text.endswith(".json"):
        return []
    return [text]


def is_runtime_artifact_reference(key: str, rel: str) -> bool:
    normalized = rel.replace("\\", "/").lstrip("./")
    if key not in {"Related latest.json", "Related pipeline artifacts"}:
        return False
    return normalized.startswith("logs/")


def check_repo_paths(path: Path, fields: dict[str, str], keys: list[str]) -> list[str]:
    errors: list[str] = []
    for key in keys:
        value = str(fields.get(key, "")).strip()
        if not value or value.lower().startswith("n/a"):
            continue
        for rel in extract_repo_paths(value):
            rel_path = Path(rel)
            if rel_path.is_absolute():
                continue
            candidate = REPO_ROOT / rel_path
            if "*" in rel or "?" in rel:
                continue
            if is_runtime_artifact_reference(key, rel):
                continue
            if not candidate.exists():
                errors.append(f"{path}: field '{key}' points to missing path '{rel}'")
    return errors


def validate_doc(path: Path, required: list[str]) -> list[str]:
    fields = parse_fields(path)
    allow_blank = is_template(path)
    errors = check_required_fields(path, fields, required, allow_blank=allow_blank)
    if is_readme(path):
        return errors
    if allow_blank:
        return errors
    errors.extend(check_na_reason(path, fields, ["Related task id(s)", "Related run id", "Related latest.json"]))
    errors.extend(check_git_head(path, fields.get("Git Head", "")))
    errors.extend(
        check_repo_paths(
            path,
            fields,
            [
                "Related decision logs",
                "Related execution plans",
                "Related latest.json",
                "Related pipeline artifacts",
            ],
        )
    )
    return errors


def validate_directory(dir_name: str, required: list[str]) -> list[str]:
    dir_path = REPO_ROOT / dir_name
    errors: list[str] = []
    for path in sorted(dir_path.glob("*.md")):
        if is_readme(path):
            continue
        errors.extend(validate_doc(path, required))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate recovery-oriented markdown in execution-plans/ and decision-logs/.")
    parser.add_argument("--dir", choices=["execution-plans", "decision-logs", "all"], default="all", help="Validate one directory or both.")
    args = parser.parse_args()

    errors: list[str] = []
    if args.dir in {"execution-plans", "all"}:
        errors.extend(validate_directory("execution-plans", EXECUTION_PLAN_FIELDS))
    if args.dir in {"decision-logs", "all"}:
        errors.extend(validate_directory("decision-logs", DECISION_LOG_FIELDS))

    if errors:
        for item in errors:
            print(f"ERROR: {item}")
        return 1

    print("OK: recovery docs validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
