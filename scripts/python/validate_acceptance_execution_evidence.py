#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REFS_RE = re.compile(r"\bRefs\s*:\s*(.+)$", flags=re.IGNORECASE)
CS_FACT_RE = re.compile(r"^\s*\[\s*(Fact|Theory)\s*\]\s*$")
CS_METHOD_RE = re.compile(r"^\s*public\s+(?:async\s+)?(?:Task(?:<[^>]+>)?|void)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
CS_CLASS_RE = re.compile(r"^\s*public\s+(?:sealed\s+|static\s+|partial\s+)*class\s+([A-Za-z_][A-Za-z0-9_]*)\b")
GD_TEST_FUNC_RE = re.compile(r"^\s*func\s+(test_[A-Za-z0-9_]+)\s*\(", flags=re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _split_refs_blob(blob: str) -> list[str]:
    normalized = str(blob or "").replace("`", " ").replace(",", " ").replace(";", " ")
    out: list[str] = []
    for token in normalized.split():
        p = token.strip().replace("\\", "/")
        if not p:
            continue
        out.append(p)
    return out


def parse_refs_from_line(line: str) -> list[str]:
    m = REFS_RE.search(str(line or "").strip())
    if not m:
        return []
    return _split_refs_blob(m.group(1) or "")


def resolve_current_task_id(tasks_json: dict[str, Any]) -> str:
    tasks = (tasks_json.get("master") or {}).get("tasks") or []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        if str(t.get("status")) == "in-progress":
            return str(t.get("id"))
    raise ValueError("No task with status=in-progress found in tasks.json")


def find_view_task(view: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
    try:
        tid_int = int(str(task_id))
    except ValueError:
        return None
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") == tid_int:
            return t
    return None


def load_sc_test_summary(root: Path, date: str) -> dict[str, Any]:
    p = root / "logs" / "ci" / date / "sc-test" / "summary.json"
    return load_json(p) if p.exists() else {}


def get_step(summary: dict[str, Any], name: str) -> dict[str, Any] | None:
    for s in summary.get("steps") or []:
        if isinstance(s, dict) and s.get("name") == name:
            return s
    return None


def find_latest_trx(unit_dir: Path) -> Path | None:
    if not unit_dir.exists():
        return None
    candidates = list(unit_dir.glob("*.trx"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_trx_test_names(trx_path: Path) -> set[str]:
    names: set[str] = set()
    root = ET.parse(trx_path).getroot()
    for elem in root.iter():
        if elem.tag.endswith("UnitTestResult"):
            tn = elem.attrib.get("testName")
            if tn:
                names.add(tn)
    return names


def find_latest_gdunit_results_xml(report_dir: Path) -> Path | None:
    if not report_dir.exists():
        return None
    xmls = list(report_dir.rglob("results.xml"))
    if not xmls:
        return None
    return max(xmls, key=lambda p: p.stat().st_mtime)


def parse_junit_testcase_names(results_xml: Path) -> set[str]:
    names: set[str] = set()
    root = ET.parse(results_xml).getroot()
    for elem in root.iter():
        if elem.tag == "testcase":
            n = elem.attrib.get("name")
            if n:
                names.add(n)
    return names


@dataclass(frozen=True)
class BoundTest:
    kind: str  # cs|gd
    ref: str
    anchor: str
    class_name: str | None
    method_or_func: str


def bind_anchor_to_test(*, root: Path, ref: str, anchor: str) -> BoundTest | None:
    p = root / ref
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    indices = [i for i, line in enumerate(text) if anchor in line]
    if not indices:
        return None

    ext = p.suffix.lower()
    if ext == ".gd":
        # Prefer anchors bound close to a test function (refactor stage convention: within 5 lines).
        for idx in indices:
            for j in range(idx + 1, min(len(text), idx + 6)):
                m = GD_TEST_FUNC_RE.match(text[j])
                if m:
                    return BoundTest(kind="gd", ref=ref, anchor=anchor, class_name=None, method_or_func=m.group(1))
        # Fallback (older files): allow a wider search window.
        for idx in indices:
            for j in range(idx + 1, min(len(text), idx + 40)):
                m = GD_TEST_FUNC_RE.match(text[j])
                if m:
                    return BoundTest(kind="gd", ref=ref, anchor=anchor, class_name=None, method_or_func=m.group(1))
        return None

    if ext == ".cs":
        # Prefer anchors bound close to a [Fact]/[Theory] attribute to avoid binding file-header anchors.
        for idx in indices:
            fact_idx = None
            for j in range(idx + 1, min(len(text), idx + 6)):
                if CS_FACT_RE.match(text[j]):
                    fact_idx = j
                    break
            if fact_idx is None:
                continue

            method_line = None
            method_name = None
            for j in range(fact_idx + 1, min(len(text), fact_idx + 25)):
                m = CS_METHOD_RE.match(text[j])
                if m:
                    method_line = j
                    method_name = m.group(1)
                    break
            if method_line is None or method_name is None:
                continue

            class_name = None
            for j in range(method_line, -1, -1):
                m = CS_CLASS_RE.match(text[j])
                if m:
                    class_name = m.group(1)
                    break

            return BoundTest(kind="cs", ref=ref, anchor=anchor, class_name=class_name, method_or_func=method_name)

        # Fallback (older files): allow a wider search window.
        for idx in indices:
            class_name = None
            for j in range(idx, -1, -1):
                m = CS_CLASS_RE.match(text[j])
                if m:
                    class_name = m.group(1)
                    break

            fact_idx = None
            for j in range(idx + 1, min(len(text), idx + 60)):
                if CS_FACT_RE.match(text[j]):
                    fact_idx = j
                    break
            if fact_idx is None:
                continue

            for j in range(fact_idx + 1, min(len(text), fact_idx + 25)):
                m = CS_METHOD_RE.match(text[j])
                if m:
                    return BoundTest(kind="cs", ref=ref, anchor=anchor, class_name=class_name, method_or_func=m.group(1))
        return None

    return None


def is_test_executed(bound: BoundTest, *, trx_names: set[str], gdunit_names: set[str]) -> bool:
    if bound.kind == "gd":
        return bound.method_or_func in gdunit_names
    if bound.kind == "cs":
        if bound.class_name:
            suffix = f".{bound.class_name}.{bound.method_or_func}"
            return any(n.endswith(suffix) or (suffix in n) for n in trx_names)
        return any(f".{bound.method_or_func}" in n for n in trx_names)
    return False


def validate_view(
    *,
    root: Path,
    view_name: str,
    task_id: str,
    entry: dict[str, Any],
    trx_names: set[str],
    gdunit_names: set[str],
) -> dict[str, Any]:
    acceptance = entry.get("acceptance") or []
    if not isinstance(acceptance, list):
        return {"view": view_name, "status": "skipped", "reason": "acceptance_not_list", "items": []}

    items: list[dict[str, Any]] = []
    errors: list[str] = []

    for idx, raw in enumerate(acceptance):
        text = str(raw or "").strip()
        anchor = f"ACC:T{task_id}.{idx + 1}"
        refs = parse_refs_from_line(text)
        if not refs:
            items.append({"index": idx + 1, "status": "fail", "reason": "missing_refs", "anchor": anchor})
            errors.append(f"{view_name}: acceptance[{idx}] missing Refs:")
            continue

        # Find a bound test in any referenced file.
        bound: BoundTest | None = None
        for r in refs:
            bound = bind_anchor_to_test(root=root, ref=r, anchor=anchor)
            if bound is not None:
                break

        if bound is None:
            items.append({"index": idx + 1, "status": "fail", "reason": "cannot_bind_anchor_to_test", "anchor": anchor, "refs": refs})
            errors.append(f"{view_name}: acceptance[{idx}] cannot bind anchor to a concrete test: {anchor}")
            continue

        executed = is_test_executed(bound, trx_names=trx_names, gdunit_names=gdunit_names)
        items.append(
            {
                "index": idx + 1,
                "status": "ok" if executed else "fail",
                "anchor": anchor,
                "ref": bound.ref,
                "kind": bound.kind,
                "class": bound.class_name,
                "test": bound.method_or_func,
                "executed": executed,
            }
        )
        if not executed:
            errors.append(f"{view_name}: acceptance[{idx}] bound test not found in execution evidence: {anchor} -> {bound.ref}::{bound.method_or_func}")

    return {"view": view_name, "status": "ok" if not errors else "fail", "items": items, "errors": errors}


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate acceptance executed evidence for one task (TRX/JUnit).")
    ap.add_argument("--task-id", default=None, help="Task id (e.g. 11). Default: first status=in-progress in tasks.json.")
    ap.add_argument("--run-id", required=True, help="Expected sc-test run_id.")
    ap.add_argument("--out", required=True, help="Output JSON path.")
    ap.add_argument("--date", default="", help="Override date for logs lookup (YYYY-MM-DD). Default: today.")
    args = ap.parse_args()

    root = repo_root()
    tasks_json = load_json(root / ".taskmaster/tasks/tasks.json")
    task_id = str(args.task_id or "").strip() or resolve_current_task_id(tasks_json)
    date = args.date.strip() or dt.date.today().strftime("%Y-%m-%d")

    summary = load_sc_test_summary(root, date)
    summary_run_id = summary.get("run_id") if isinstance(summary, dict) else None
    run_id_file = root / "logs" / "ci" / date / "sc-test" / "run_id.txt"
    run_id_file_value = run_id_file.read_text(encoding="utf-8", errors="ignore").strip() if run_id_file.exists() else None

    meta: dict[str, Any] = {
        "date": date,
        "expected_run_id": args.run_id,
        "summary_run_id": summary_run_id,
        "run_id_file": str(run_id_file.relative_to(root)).replace("\\", "/"),
        "run_id_file_value": run_id_file_value,
        "sc_test_summary": f"logs/ci/{date}/sc-test/summary.json",
        "errors": [],
    }

    if str(summary_run_id or "") != args.run_id:
        meta["errors"].append("run_id_mismatch_in_summary")
    if str(run_id_file_value or "") != args.run_id:
        meta["errors"].append("run_id_mismatch_in_run_id_file")

    unit_step = get_step(summary, "unit") if isinstance(summary, dict) else None
    gd_step = get_step(summary, "gdunit-hard") if isinstance(summary, dict) else None

    unit_dir = Path(unit_step.get("artifacts_dir")) if isinstance(unit_step, dict) and unit_step.get("artifacts_dir") else (root / "logs" / "unit" / date)
    unit_run_id_file = unit_dir / "run_id.txt"
    unit_run_id_value = unit_run_id_file.read_text(encoding="utf-8", errors="ignore").strip() if unit_run_id_file.exists() else None
    trx = find_latest_trx(unit_dir)
    meta["unit_dir"] = str(unit_dir).replace("\\", "/")
    meta["unit_run_id_file"] = str(unit_run_id_file).replace("\\", "/")
    meta["unit_run_id_value"] = unit_run_id_value
    meta["trx"] = str(trx).replace("\\", "/") if trx else None

    gd_report_dir = None
    if isinstance(gd_step, dict) and gd_step.get("report_dir"):
        gd_report_dir = (root / str(gd_step.get("report_dir"))).resolve() if str(gd_step.get("report_dir")).startswith("logs") else Path(gd_step.get("report_dir"))
    else:
        gd_report_dir = root / "logs" / "e2e" / date / "sc-test" / "gdunit-hard"
    gd_run_id_file = Path(gd_report_dir) / "run_id.txt"
    gd_run_id_value = gd_run_id_file.read_text(encoding="utf-8", errors="ignore").strip() if gd_run_id_file.exists() else None
    gd_xml = find_latest_gdunit_results_xml(gd_report_dir)
    meta["gd_report_dir"] = str(gd_report_dir).replace("\\", "/")
    meta["gd_run_id_file"] = str(gd_run_id_file).replace("\\", "/")
    meta["gd_run_id_value"] = gd_run_id_value
    meta["gd_results_xml"] = str(gd_xml).replace("\\", "/") if gd_xml else None

    trx_names: set[str] = set()
    if trx and trx.exists():
        trx_names = parse_trx_test_names(trx)
    gd_names: set[str] = set()
    if gd_xml and gd_xml.exists():
        gd_names = parse_junit_testcase_names(gd_xml)

    meta["trx_test_count"] = len(trx_names)
    meta["gdunit_test_count"] = len(gd_names)

    if str(unit_run_id_value or "") != args.run_id:
        meta["errors"].append("unit_run_id_mismatch_or_missing")
    if isinstance(gd_step, dict):
        if str(gd_run_id_value or "") != args.run_id:
            meta["errors"].append("gdunit_run_id_mismatch_or_missing")

    back_view = load_json(root / ".taskmaster/tasks/tasks_back.json")
    gameplay_view = load_json(root / ".taskmaster/tasks/tasks_gameplay.json")
    if not isinstance(back_view, list) or not isinstance(gameplay_view, list):
        raise ValueError("Expected tasks_back.json/tasks_gameplay.json to be JSON arrays")

    back_entry = find_view_task(back_view, task_id)
    game_entry = find_view_task(gameplay_view, task_id)

    results: list[dict[str, Any]] = []
    if back_entry is not None:
        results.append(validate_view(root=root, view_name="back", task_id=task_id, entry=back_entry, trx_names=trx_names, gdunit_names=gd_names))
    if game_entry is not None:
        results.append(validate_view(root=root, view_name="gameplay", task_id=task_id, entry=game_entry, trx_names=trx_names, gdunit_names=gd_names))

    if not results:
        meta["errors"].append("task_not_found_in_back_or_gameplay")

    hard_errors: list[str] = []
    for r in results:
        if r.get("status") == "fail":
            hard_errors.extend(r.get("errors") or [])
    hard_errors.extend(meta["errors"])

    payload = {"status": "ok" if not hard_errors else "fail", "meta": meta, "results": results}
    write_json(Path(args.out), payload)
    return 0 if not hard_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
