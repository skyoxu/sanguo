#!/usr/bin/env python3
"""Generate task -> contractRefs -> contract files -> tests matrix.

Outputs:
- .taskmaster/docs/task-contract-test-matrix.json
- .taskmaster/docs/task-contract-test-matrix.md
- logs/ci/<YYYY-MM-DD>/task-contract-test-matrix/summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

EVENT_TYPES_MEMBER_RE = re.compile(r'\bpublic\s+const\s+string\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"([^"]+)"\s*;')
EVENT_TYPE_LITERAL_RE = re.compile(r'\bpublic\s+const\s+string\s+EventType\s*=\s*"([^"]+)"\s*;')
EVENT_TYPE_SYMBOL_RE = re.compile(r'\bpublic\s+const\s+string\s+EventType\s*=\s*EventTypes\.([A-Za-z_][A-Za-z0-9_]*)\s*;')
RECORD_NAME_RE = re.compile(r'\bpublic\s+sealed\s+record\s+([A-Za-z_][A-Za-z0-9_]*)')


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _load_view_tasks(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict) and isinstance(data.get("tasks"), list):
        return [x for x in data["tasks"] if isinstance(x, dict)]
    return []


def _load_event_types_map(event_types_path: Path) -> dict[str, str]:
    if not event_types_path.exists():
        return {}
    text = event_types_path.read_text(encoding="utf-8", errors="ignore")
    return {symbol: value for symbol, value in EVENT_TYPES_MEMBER_RE.findall(text)}


def _index_event_contracts(repo: Path, contracts_root: Path, event_types_map: dict[str, str]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    event_to_files: dict[str, list[str]] = {}
    event_to_classes: dict[str, list[str]] = {}

    for cs in sorted(contracts_root.rglob("*.cs")):
        text = cs.read_text(encoding="utf-8", errors="ignore")
        rel = _to_posix(cs.relative_to(repo))
        classes = RECORD_NAME_RE.findall(text)

        resolved_types: list[str] = []
        resolved_types.extend(EVENT_TYPE_LITERAL_RE.findall(text))
        for sym in EVENT_TYPE_SYMBOL_RE.findall(text):
            value = event_types_map.get(sym)
            if value:
                resolved_types.append(value)

        for event_type in resolved_types:
            event_to_files.setdefault(event_type, [])
            if rel not in event_to_files[event_type]:
                event_to_files[event_type].append(rel)

            event_to_classes.setdefault(event_type, [])
            for cls in classes:
                if cls not in event_to_classes[event_type]:
                    event_to_classes[event_type].append(cls)

    return event_to_files, event_to_classes


def _index_tests(repo: Path, test_root: Path) -> dict[str, str]:
    tests: dict[str, str] = {}
    for cs in sorted(test_root.rglob("*.cs")):
        tests[_to_posix(cs.relative_to(repo))] = cs.read_text(encoding="utf-8", errors="ignore")
    return tests


def _find_tests_for_event(event_type: str, classes: list[str], test_texts: dict[str, str]) -> list[str]:
    results: list[str] = []
    for path, text in test_texts.items():
        matched = False
        for cls in classes:
            if f"{cls}.EventType" in text or re.search(rf"\b{re.escape(cls)}\b", text):
                matched = True
                break
        if not matched and event_type in text:
            matched = True
        if matched:
            results.append(path)
    return sorted(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate task-contract-test matrix.")
    parser.add_argument(
        "--task-views",
        nargs="*",
        default=[".taskmaster/tasks/tasks_back.json", ".taskmaster/tasks/tasks_gameplay.json"],
        help="Task view files to scan.",
    )
    parser.add_argument(
        "--contracts-root",
        default="Game.Core/Contracts",
        help="Contracts root path.",
    )
    parser.add_argument(
        "--tests-root",
        default="Game.Core.Tests",
        help="Tests root path.",
    )
    parser.add_argument(
        "--out-json",
        default=".taskmaster/docs/task-contract-test-matrix.json",
        help="Output matrix JSON path.",
    )
    parser.add_argument(
        "--out-md",
        default=".taskmaster/docs/task-contract-test-matrix.md",
        help="Output matrix markdown path.",
    )
    args = parser.parse_args(argv)

    repo = Path.cwd().resolve()
    task_views = [repo / p for p in args.task_views]
    contracts_root = (repo / args.contracts_root).resolve()
    tests_root = (repo / args.tests_root).resolve()

    event_types_map = _load_event_types_map(contracts_root / "EventTypes.cs")
    event_to_files, event_to_classes = _index_event_contracts(repo, contracts_root, event_types_map)
    test_texts = _index_tests(repo, tests_root)

    matrix_tasks: list[dict[str, Any]] = []
    unresolved_refs: set[str] = set()
    refs_without_tests: set[str] = set()
    refs_total = 0
    tasks_with_refs = 0

    for view in task_views:
        if not view.exists():
            continue
        tasks = _load_view_tasks(view)
        view_name = _to_posix(view.relative_to(repo))
        for task in tasks:
            refs = task.get("contractRefs") or []
            refs = [r for r in refs if isinstance(r, str) and r.strip()]
            if refs:
                tasks_with_refs += 1
            items: list[dict[str, Any]] = []
            for ref in refs:
                refs_total += 1
                files = event_to_files.get(ref, [])
                classes = event_to_classes.get(ref, [])
                tests = _find_tests_for_event(ref, classes, test_texts) if files else []
                resolved = bool(files)
                if not resolved:
                    unresolved_refs.add(ref)
                if resolved and not tests:
                    refs_without_tests.add(ref)
                items.append(
                    {
                        "event_type": ref,
                        "resolved": resolved,
                        "contract_files": files,
                        "contract_classes": classes,
                        "tests": tests,
                    }
                )

            matrix_tasks.append(
                {
                    "view": view_name,
                    "task_id": task.get("id"),
                    "taskmaster_id": task.get("taskmaster_id"),
                    "title": task.get("title"),
                    "status": task.get("status"),
                    "layer": task.get("layer"),
                    "contract_refs_count": len(refs),
                    "contracts": items,
                }
            )

    summary = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "task_views": [_to_posix(p.relative_to(repo)) for p in task_views if p.exists()],
        "tasks_scanned": len(matrix_tasks),
        "tasks_with_contract_refs": tasks_with_refs,
        "contract_refs_total": refs_total,
        "unique_event_refs": len({c["event_type"] for t in matrix_tasks for c in t["contracts"]}),
        "unresolved_refs_count": len(unresolved_refs),
        "unresolved_refs": sorted(unresolved_refs),
        "resolved_refs_without_tests_count": len(refs_without_tests),
        "resolved_refs_without_tests": sorted(refs_without_tests),
        "event_contract_coverage": {
            "event_types_total": len(set(event_types_map.values())),
            "typed_event_contracts_total": len(event_to_files),
        },
    }

    matrix = {
        "summary": summary,
        "tasks": matrix_tasks,
    }

    out_json = (repo / args.out_json).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out_md = (repo / args.out_md).resolve()
    zh_title = "\u4efb\u52a1-\u5951\u7ea6-\u6d4b\u8bd5\u4e09\u5411\u77e9\u9635"
    zh_summary = "\u6458\u8981"
    zh_unresolved = "\u672a\u89e3\u6790\u4e8b\u4ef6"
    zh_no_tests = "\u5df2\u89e3\u6790\u4f46\u65e0\u6d4b\u8bd5\u5f15\u7528\u4e8b\u4ef6"
    zh_details = "\u4efb\u52a1\u660e\u7ec6"

    md_lines: list[str] = []
    md_lines.append(f"# {zh_title}")
    md_lines.append("")
    md_lines.append(f"## {zh_summary}")
    md_lines.append("")
    md_lines.append(f"- \u626b\u63cf\u4efb\u52a1\u6570\uff1a{summary['tasks_scanned']}")
    md_lines.append(f"- \u542b contractRefs \u7684\u4efb\u52a1\u6570\uff1a{summary['tasks_with_contract_refs']}")
    md_lines.append(f"- contractRefs \u603b\u6570\uff1a{summary['contract_refs_total']}")
    md_lines.append(f"- \u552f\u4e00\u4e8b\u4ef6\u5f15\u7528\u6570\uff1a{summary['unique_event_refs']}")
    md_lines.append(f"- \u672a\u89e3\u6790\u4e8b\u4ef6\u6570\uff1a{summary['unresolved_refs_count']}")
    md_lines.append(f"- \u5df2\u89e3\u6790\u4f46\u65e0\u6d4b\u8bd5\u5f15\u7528\u7684\u4e8b\u4ef6\u6570\uff1a{summary['resolved_refs_without_tests_count']}")
    md_lines.append(f"- EventTypes \u5e38\u91cf\u6570\uff1a{summary['event_contract_coverage']['event_types_total']}")
    md_lines.append(f"- \u5f3a\u7c7b\u578b\u4e8b\u4ef6\u5951\u7ea6\u6570\uff1a{summary['event_contract_coverage']['typed_event_contracts_total']}")
    md_lines.append("")

    if summary["unresolved_refs"]:
        md_lines.append(f"## {zh_unresolved}")
        md_lines.append("")
        for event_type in summary["unresolved_refs"]:
            md_lines.append(f"- `{event_type}`")
        md_lines.append("")

    if summary["resolved_refs_without_tests"]:
        md_lines.append(f"## {zh_no_tests}")
        md_lines.append("")
        for event_type in summary["resolved_refs_without_tests"]:
            md_lines.append(f"- `{event_type}`")
        md_lines.append("")

    md_lines.append(f"## {zh_details}")
    md_lines.append("")
    for task in matrix_tasks:
        if task["contract_refs_count"] == 0:
            continue
        md_lines.append(f"### {task['task_id']} ({task['view']})")
        md_lines.append("")
        md_lines.append(f"- \u6807\u9898\uff1a{task['title']}")
        md_lines.append(f"- \u72b6\u6001\uff1a{task['status']}")
        md_lines.append(f"- layer\uff1a{task['layer']}")
        md_lines.append(f"- taskmaster_id\uff1a{task['taskmaster_id']}")
        for item in task["contracts"]:
            md_lines.append(f"- \u4e8b\u4ef6\uff1a`{item['event_type']}`")
            if item["resolved"]:
                md_lines.append(f"  - \u5951\u7ea6\u6587\u4ef6\uff1a{', '.join(f'`{p}`' for p in item['contract_files'])}")
                if item["tests"]:
                    md_lines.append(f"  - \u5173\u8054\u6d4b\u8bd5\uff1a{', '.join(f'`{p}`' for p in item['tests'])}")
                else:
                    md_lines.append("  - \u5173\u8054\u6d4b\u8bd5\uff1a\u65e0")
            else:
                md_lines.append("  - \u5951\u7ea6\u6587\u4ef6\uff1a\u672a\u89e3\u6790")
                md_lines.append("  - \u5173\u8054\u6d4b\u8bd5\uff1a\u672a\u89e3\u6790")
        md_lines.append("")

    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    ci_out = repo / "logs" / "ci" / _today() / "task-contract-test-matrix" / "summary.json"
    ci_out.parent.mkdir(parents=True, exist_ok=True)
    ci_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = "ok" if summary["unresolved_refs_count"] == 0 else "fail"
    print(
        f"TASK_CONTRACT_TEST_MATRIX status={status} tasks={summary['tasks_scanned']} "
        f"refs={summary['contract_refs_total']} unresolved={summary['unresolved_refs_count']} "
        f"no_tests={summary['resolved_refs_without_tests_count']} out={_to_posix(out_json.relative_to(repo))}"
    )

    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
