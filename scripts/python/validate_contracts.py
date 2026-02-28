#!/usr/bin/env python
"""Validate contract references and contract hard rules for Game.Core/Contracts.

Hard checks:
- Overlay contract backlink must exist (each contract file is referenced by overlay 08 docs).
- EventType naming must follow ADR-0004 prefixes:
  - core.<entity>.<action>...
  - ui.menu.<action>...
  - screen.<name>.<action>...
- XML comments:
  - Every public contract type must have <summary>.
  - Files with EventType constant must also have <remarks>.
- BCL-only boundary: contracts must not depend on Godot APIs/namespaces.
- Namespace must start with Game.Core.Contracts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


CONTRACTS_PREFIX = "Game.Core/Contracts/"
CONTRACTS_ROOT = Path("Game.Core") / "Contracts"
OVERLAYS_ROOT = Path("docs") / "architecture" / "overlays"

EVENT_TYPE_PATTERN = re.compile(
    r"^(?:"
    r"core\.[a-z0-9_]+(?:\.[a-z0-9_]+)+"
    r"|ui\.menu\.[a-z0-9_]+(?:\.[a-z0-9_]+)*"
    r"|screen\.[a-z0-9_]+(?:\.[a-z0-9_]+)+"
    r")$"
)
NAMESPACE_PATTERN = re.compile(r"^\s*namespace\s+([A-Za-z_][A-Za-z0-9_\.]*)\s*(?:;|\{)", re.MULTILINE)
USING_PATTERN = re.compile(r"^\s*using\s+([A-Za-z_][A-Za-z0-9_\.]*)\s*;", re.MULTILINE)
PUBLIC_TYPE_LINE_PATTERN = re.compile(
    r"^\s*public\s+(?:sealed\s+|abstract\s+|static\s+|partial\s+)?(?:record|class|interface|enum|struct)\s+[A-Za-z_][A-Za-z0-9_]*"
)
EVENTTYPE_CONST_PATTERN = re.compile(r"public\s+const\s+string\s+EventType\s*=\s*([^;]+);")
EVENT_TYPES_CONST_PATTERN = re.compile(r"public\s+const\s+string\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\"([^\"]+)\";")


def _to_posix(p: Path) -> str:
    return p.as_posix()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def find_overlay_docs(root: Path) -> List[Path]:
    overlays_root = root / OVERLAYS_ROOT
    if not overlays_root.exists():
        return []
    docs: List[Path] = []
    for prd_dir in overlays_root.iterdir():
        if not prd_dir.is_dir():
            continue
        chapter_dir = prd_dir / "08"
        if not chapter_dir.exists():
            continue
        docs.extend(chapter_dir.glob("*.md"))
    return docs


def extract_contract_paths(md_path: Path) -> List[str]:
    text = _read_text(md_path)
    pattern = re.compile(r"`(" + re.escape(CONTRACTS_PREFIX) + r"[^`]+?\.cs)`")
    seen: set[str] = set()
    out: List[str] = []
    for match in pattern.findall(text):
        norm = str(match).replace("\\", "/")
        if norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def find_all_contract_files(root: Path) -> List[str]:
    contracts_root = root / CONTRACTS_ROOT
    if not contracts_root.exists():
        return []
    files = [_to_posix(p.relative_to(root)) for p in contracts_root.rglob("*.cs") if p.is_file()]
    files.sort()
    return files


def _is_required_overlay_contract_doc(rel_doc: str) -> bool:
    name = Path(rel_doc).name
    return name.startswith("08-Contracts-") or name.startswith("08-Feature-Slice-")


def _line_number_of(text: str, needle: str) -> int:
    idx = text.find(needle)
    if idx < 0:
        return 1
    return text[:idx].count("\n") + 1


def _extract_event_types_map(root: Path) -> tuple[Dict[str, str], List[Dict[str, Any]]]:
    issues: List[Dict[str, Any]] = []
    mapping: Dict[str, str] = {}
    event_types_path = root / CONTRACTS_ROOT / "EventTypes.cs"
    if not event_types_path.exists():
        issues.append(
            {
                "file": _to_posix(event_types_path.relative_to(root)),
                "line": 1,
                "code": "event_types_file_missing",
                "message": "EventTypes.cs is missing.",
            }
        )
        return mapping, issues

    text = _read_text(event_types_path)
    for m in EVENT_TYPES_CONST_PATTERN.finditer(text):
        name = m.group(1)
        value = m.group(2)
        mapping[name] = value
        if not EVENT_TYPE_PATTERN.match(value):
            issues.append(
                {
                    "file": _to_posix(event_types_path.relative_to(root)),
                    "line": _line_number_of(text, m.group(0)),
                    "code": "event_type_value_invalid",
                    "message": f"EventTypes.{name} value '{value}' does not match ADR-0004 naming pattern.",
                }
            )
    if not mapping:
        issues.append(
            {
                "file": _to_posix(event_types_path.relative_to(root)),
                "line": 1,
                "code": "event_types_empty",
                "message": "No public const string entries found in EventTypes.cs.",
            }
        )
    return mapping, issues


def _validate_namespace(rel_path: str, text: str) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    m = NAMESPACE_PATTERN.search(text)
    if not m:
        issues.append(
            {
                "file": rel_path,
                "line": 1,
                "code": "namespace_missing",
                "message": "Missing namespace declaration.",
            }
        )
        return issues

    ns = m.group(1)
    if not ns.startswith("Game.Core.Contracts"):
        issues.append(
            {
                "file": rel_path,
                "line": _line_number_of(text, m.group(0)),
                "code": "namespace_invalid",
                "message": f"Namespace '{ns}' must start with 'Game.Core.Contracts'.",
            }
        )
    return issues


def _validate_bcl_only(rel_path: str, text: str) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    if re.search(r"^\s*using\s+Godot(?:\.|;)", text, flags=re.MULTILINE) or re.search(r"\bGodot\.", text):
        issues.append(
            {
                "file": rel_path,
                "line": 1,
                "code": "godot_dependency_forbidden",
                "message": "Contracts must not depend on Godot API.",
            }
        )

    for m in USING_PATTERN.finditer(text):
        ns = m.group(1)
        if ns.startswith("System") or ns.startswith("Game.Core.Contracts"):
            continue
        issues.append(
            {
                "file": rel_path,
                "line": _line_number_of(text, m.group(0)),
                "code": "using_non_bcl_forbidden",
                "message": f"Using '{ns}' is outside BCL/contracts boundary.",
            }
        )
    return issues


def _validate_xml_comments(rel_path: str, text: str, require_remarks: bool) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if not PUBLIC_TYPE_LINE_PATTERN.match(line.strip()):
            continue
        start = max(0, idx - 12)
        header = "\n".join(lines[start:idx])
        if "<summary>" not in header:
            issues.append(
                {
                    "file": rel_path,
                    "line": idx + 1,
                    "code": "xml_summary_missing",
                    "message": "Public contract type is missing XML <summary>.",
                }
            )
        if require_remarks and "<remarks>" not in header:
            issues.append(
                {
                    "file": rel_path,
                    "line": idx + 1,
                    "code": "xml_remarks_missing",
                    "message": "Event contract type is missing XML <remarks>.",
                }
            )
        break
    return issues


def _validate_eventtype_constants(rel_path: str, text: str, event_types_map: Dict[str, str]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    matches = list(EVENTTYPE_CONST_PATTERN.finditer(text))
    if rel_path.startswith("Game.Core/Contracts/Events/") and not matches:
        issues.append(
            {
                "file": rel_path,
                "line": 1,
                "code": "eventtype_const_missing",
                "message": "Event contract must define 'public const string EventType'.",
            }
        )
        return issues

    for m in matches:
        rhs = str(m.group(1)).strip()
        line_no = _line_number_of(text, m.group(0))
        literal = re.fullmatch(r"\"([^\"]+)\"", rhs)
        if literal:
            value = literal.group(1)
            if not EVENT_TYPE_PATTERN.match(value):
                issues.append(
                    {
                        "file": rel_path,
                        "line": line_no,
                        "code": "eventtype_literal_invalid",
                        "message": f"EventType literal '{value}' does not match ADR-0004 naming pattern.",
                    }
                )
            continue

        ref = re.fullmatch(r"EventTypes\.([A-Za-z_][A-Za-z0-9_]*)", rhs)
        if ref:
            key = ref.group(1)
            if key not in event_types_map:
                issues.append(
                    {
                        "file": rel_path,
                        "line": line_no,
                        "code": "eventtype_ref_missing",
                        "message": f"EventType reference EventTypes.{key} not found in EventTypes.cs.",
                    }
                )
                continue
            value = event_types_map[key]
            if not EVENT_TYPE_PATTERN.match(value):
                issues.append(
                    {
                        "file": rel_path,
                        "line": line_no,
                        "code": "eventtype_ref_value_invalid",
                        "message": f"EventTypes.{key} value '{value}' does not match ADR-0004 naming pattern.",
                    }
                )
            continue

        issues.append(
            {
                "file": rel_path,
                "line": line_no,
                "code": "eventtype_rhs_invalid",
                "message": "EventType must be a string literal or EventTypes.<Name>.",
            }
        )
    return issues


def _validate_contract_file(rel_path: str, text: str, event_types_map: Dict[str, str]) -> Dict[str, List[Dict[str, Any]]]:
    has_eventtype_const = "public const string EventType" in text
    return {
        "namespace_issues": _validate_namespace(rel_path, text),
        "bcl_only_issues": _validate_bcl_only(rel_path, text),
        "xml_comment_issues": _validate_xml_comments(rel_path, text, require_remarks=has_eventtype_const),
        "eventtype_issues": _validate_eventtype_constants(rel_path, text, event_types_map),
    }


def build_report(root: Path) -> Dict[str, object]:
    overlay_docs = find_overlay_docs(root)

    doc_contracts: Dict[str, List[str]] = {}
    for md in overlay_docs:
        rel_doc = _to_posix(md.relative_to(root))
        doc_contracts[rel_doc] = extract_contract_paths(md)

    referenced_contracts: List[str] = []
    for contracts in doc_contracts.values():
        for c in contracts:
            if c not in referenced_contracts:
                referenced_contracts.append(c)

    all_contracts = find_all_contract_files(root)
    missing_contract_files: List[Dict[str, str]] = []
    for doc, contracts in doc_contracts.items():
        for contract_path in contracts:
            contract_rel = contract_path.replace("\\", "/")
            if not (root / contract_rel).exists():
                missing_contract_files.append({"doc": doc, "contract": contract_rel})

    docs_without_contracts = [doc for doc, contracts in doc_contracts.items() if not contracts]
    required_docs_without_contracts = [doc for doc in docs_without_contracts if _is_required_overlay_contract_doc(doc)]
    contracts_without_docs = [c for c in all_contracts if c not in referenced_contracts]

    event_types_map, event_types_file_issues = _extract_event_types_map(root)

    namespace_issues: List[Dict[str, Any]] = []
    bcl_only_issues: List[Dict[str, Any]] = []
    xml_comment_issues: List[Dict[str, Any]] = []
    eventtype_issues: List[Dict[str, Any]] = list(event_types_file_issues)

    for rel in all_contracts:
        text = _read_text(root / rel)
        result = _validate_contract_file(rel, text, event_types_map)
        namespace_issues.extend(result["namespace_issues"])
        bcl_only_issues.extend(result["bcl_only_issues"])
        xml_comment_issues.extend(result["xml_comment_issues"])
        eventtype_issues.extend(result["eventtype_issues"])

    overlay_backlink_missing = contracts_without_docs
    hard_fail = any(
        [
            missing_contract_files,
            required_docs_without_contracts,
            overlay_backlink_missing,
            eventtype_issues,
            xml_comment_issues,
            bcl_only_issues,
            namespace_issues,
        ]
    )

    return {
        "ok": not hard_fail,
        "overlay_docs_count": len(overlay_docs),
        "referenced_contracts_count": len(referenced_contracts),
        "all_contracts_count": len(all_contracts),
        "event_types_count": len(event_types_map),
        "missing_contract_files": missing_contract_files,
        "docs_without_contracts": docs_without_contracts,
        "required_docs_without_contracts": required_docs_without_contracts,
        "contracts_without_docs": contracts_without_docs,
        "overlay_backlink_missing": overlay_backlink_missing,
        "eventtype_issues": eventtype_issues,
        "xml_comment_issues": xml_comment_issues,
        "bcl_only_issues": bcl_only_issues,
        "namespace_issues": namespace_issues,
    }


def write_report(root: Path, report: Dict[str, object]) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = root / "logs" / "ci" / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "contracts-validate.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Contracts + overlay backlinks with hard checks.")
    parser.add_argument("--root", default=".", help="Project root directory (default: current directory)")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    report = build_report(root)
    out_path = write_report(root, report)

    print(f"Contracts validation report written to: {out_path}")
    if not report.get("ok", False):
        print("Contracts validation detected hard issues; see JSON report for details.")
        return 1
    print("Contracts validation passed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

