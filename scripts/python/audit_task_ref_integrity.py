#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit reference integrity across the Taskmaster triplet:
  - .taskmaster/tasks/tasks.json            (master view)
  - .taskmaster/tasks/tasks_back.json       (backbone/governance view)
  - .taskmaster/tasks/tasks_gameplay.json   (gameplay view)

This script is deterministic (no LLM usage) and focuses on:
  1) ADR refs: file exists + Status is Accepted.
  2) Arch refs: CHxx values are within the known range (CH01..CH12).
  3) Overlay refs: referenced files exist; overlay is consistent with overlay_refs.
  4) Duplicate fields consistency in task views:
        adr_refs    vs adrRefs
        chapter_refs vs archRefs
        overlay_refs vs overlay
  5) contractRefs: every event type must exist as an EventType constant in Game.Core/Contracts/**.cs
  6) tasks.json (master) vs views: for each master task id, compare adr/arch/overlay with the
     exported view task (tasks_back is expected to exist for every taskmaster_id).

Outputs:
  - logs/ci/<YYYY-MM-DD>/task-refs-audit/task_ref_integrity.json

Exit code:
  - 0 if no P0 issues are found.
  - 1 if any P0 issue exists (missing files, non-Accepted ADRs, unknown contractRefs, missing required mappings).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


ADR_STATUS_RE = re.compile(r"^\s*-?\s*Status\s*:\s*(.+?)\s*$", flags=re.IGNORECASE | re.MULTILINE)
EVENTTYPE_RE = re.compile(r'public\s+const\s+string\s+EventType\s*=\s*"([^"]+)"\s*;', flags=re.MULTILINE)
CH_RE = re.compile(r"^CH(\d{2})$")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def normalize_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for v in value:
            s = str(v).strip()
            if s:
                out.append(s)
        return out
    s = str(value).strip()
    return [s] if s else []


def as_set(values: Iterable[str]) -> set[str]:
    return {v.strip() for v in values if str(v).strip()}


def collect_adr_statuses(root: Path) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for p in (root / "docs" / "adr").glob("ADR-*.md"):
        m = re.match(r"ADR-(\d{4})", p.stem)
        if not m:
            continue
        adr_id = f"ADR-{m.group(1)}"
        text = p.read_text(encoding="utf-8", errors="ignore")
        sm = ADR_STATUS_RE.search(text)
        status = sm.group(1).strip() if sm else "Unknown"
        statuses[adr_id] = {"path": str(p.relative_to(root)).replace("\\", "/"), "status": status}
    return statuses


def collect_event_types(root: Path) -> set[str]:
    contracts_root = root / "Game.Core" / "Contracts"
    if not contracts_root.exists():
        return set()
    types: set[str] = set()
    for cs in contracts_root.rglob("*.cs"):
        text = cs.read_text(encoding="utf-8", errors="ignore")
        for evt in EVENTTYPE_RE.findall(text):
            if evt.strip():
                types.add(evt.strip())
    return types


def ch_is_valid(ch: str) -> bool:
    m = CH_RE.match(ch)
    if not m:
        return False
    n = int(m.group(1))
    return 1 <= n <= 12


@dataclass(frozen=True)
class Finding:
    severity: str  # P0/P1/P2
    where: str
    task_id: str | None
    field: str
    message: str


def find_task_by_taskmaster_id(view: list[dict[str, Any]], taskmaster_id: int) -> dict[str, Any] | None:
    for t in view:
        if not isinstance(t, dict):
            continue
        if t.get("taskmaster_id") == taskmaster_id:
            return t
    return None


def audit_view_task(
    *,
    root: Path,
    view_name: str,
    task: dict[str, Any],
    adr_statuses: dict[str, dict[str, Any]],
    event_types: set[str],
) -> list[Finding]:
    tid = str(task.get("id", "")).strip() or None
    findings: list[Finding] = []

    # Duplicate fields consistency: adr_refs vs adrRefs
    adr_refs = normalize_str_list(task.get("adr_refs"))
    adrRefs = normalize_str_list(task.get("adrRefs"))
    if as_set(adr_refs) != as_set(adrRefs):
        findings.append(
            Finding(
                "P1",
                view_name,
                tid,
                "adr_refs/adrRefs",
                f"Mismatch between adr_refs={adr_refs} and adrRefs={adrRefs}. Keep them identical to avoid drift.",
            )
        )

    # Duplicate fields consistency: chapter_refs vs archRefs
    chapter_refs = normalize_str_list(task.get("chapter_refs"))
    archRefs = normalize_str_list(task.get("archRefs"))
    if as_set(chapter_refs) != as_set(archRefs):
        findings.append(
            Finding(
                "P1",
                view_name,
                tid,
                "chapter_refs/archRefs",
                f"Mismatch between chapter_refs={chapter_refs} and archRefs={archRefs}. Keep them identical to avoid drift.",
            )
        )

    # ADR existence + status accepted
    for adr in sorted(as_set(adr_refs) | as_set(adrRefs)):
        meta = adr_statuses.get(adr)
        if not meta:
            findings.append(Finding("P0", view_name, tid, "adr_refs", f"Missing ADR file for {adr}."))
            continue
        status = str(meta.get("status", "Unknown"))
        if status.lower() != "accepted":
            findings.append(
                Finding("P0", view_name, tid, "adr_refs", f"{adr} status is not Accepted (status={status}).")
            )

    # CH validity (we cannot validate base index file here; ensure CH01..CH12 only)
    for ch in sorted(as_set(chapter_refs) | as_set(archRefs)):
        if not ch_is_valid(ch):
            findings.append(Finding("P1", view_name, tid, "chapter_refs", f"Invalid chapter ref: {ch}"))

    # Overlay existence + consistency
    overlay_refs = normalize_str_list(task.get("overlay_refs"))
    overlay = str(task.get("overlay") or "").strip()
    if overlay:
        overlay_path = root / overlay
        if not overlay_path.exists():
            findings.append(Finding("P0", view_name, tid, "overlay", f"Overlay file not found: {overlay}"))
        if overlay_refs and overlay not in overlay_refs:
            findings.append(
                Finding(
                    "P2",
                    view_name,
                    tid,
                    "overlay/overlay_refs",
                    f"overlay is not included in overlay_refs (overlay={overlay}). This is usually expected.",
                )
            )

    for p in overlay_refs:
        full = root / p
        if not full.exists():
            findings.append(Finding("P0", view_name, tid, "overlay_refs", f"Overlay ref file not found: {p}"))

    # contractRefs validity
    contract_refs = normalize_str_list(task.get("contractRefs"))
    for evt in sorted(as_set(contract_refs)):
        if evt not in event_types:
            findings.append(
                Finding(
                    "P0",
                    view_name,
                    tid,
                    "contractRefs",
                    f"Unknown contract event type (not found in Game.Core/Contracts EventType constants): {evt}",
                )
            )

    return findings


def audit_master_task(
    *,
    root: Path,
    master_task: dict[str, Any],
    back_task: dict[str, Any] | None,
    gameplay_task: dict[str, Any] | None,
) -> list[Finding]:
    tid = str(master_task.get("id", "")).strip() or None
    findings: list[Finding] = []

    adrRefs = normalize_str_list(master_task.get("adrRefs"))
    archRefs = normalize_str_list(master_task.get("archRefs"))
    overlay = str(master_task.get("overlay") or "").strip()

    if overlay:
        if not (root / overlay).exists():
            findings.append(Finding("P0", "tasks.json", tid, "overlay", f"Overlay file not found: {overlay}"))

    # Mapping: tasks_back should exist for every master task id in this repo.
    if back_task is None:
        findings.append(Finding("P0", "tasks.json", tid, "mapping", "Missing tasks_back entry for this taskmaster id."))
        return findings

    # Compare master refs against view duplicates (adrRefs/archRefs/overlay)
    back_adr = normalize_str_list(back_task.get("adrRefs")) or normalize_str_list(back_task.get("adr_refs"))
    if as_set(adrRefs) != as_set(back_adr):
        findings.append(
            Finding(
                "P1",
                "tasks.json",
                tid,
                "adrRefs",
                f"tasks.json adrRefs differs from tasks_back adr refs (tasks.json={adrRefs}, tasks_back={back_adr}).",
            )
        )

    back_ch = normalize_str_list(back_task.get("archRefs")) or normalize_str_list(back_task.get("chapter_refs"))
    if as_set(archRefs) != as_set(back_ch):
        findings.append(
            Finding(
                "P1",
                "tasks.json",
                tid,
                "archRefs",
                f"tasks.json archRefs differs from tasks_back chapter refs (tasks.json={archRefs}, tasks_back={back_ch}).",
            )
        )

    back_overlay = str(back_task.get("overlay") or "").strip()
    if overlay and back_overlay and overlay != back_overlay:
        findings.append(
            Finding(
                "P1",
                "tasks.json",
                tid,
                "overlay",
                f"tasks.json overlay differs from tasks_back overlay (tasks.json={overlay}, tasks_back={back_overlay}).",
            )
        )

    # Gameplay mapping is optional by governance rule; warn only if master looks gameplay-ish but missing.
    if gameplay_task is None:
        # Heuristic: if title contains UI or gameplay keywords, suggest it should exist in gameplay view.
        title = str(master_task.get("title") or "")
        if any(k in title for k in ["UI", "玩法", "对战", "回合", "AI", "战斗"]):
            findings.append(
                Finding(
                    "P2",
                    "tasks.json",
                    tid,
                    "mapping",
                    "No tasks_gameplay entry found; verify this is intended (allowed by policy, but may reduce gameplay traceability).",
                )
            )

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit Taskmaster triplet references integrity.")
    ap.add_argument("--out", default=None, help="Output json path (default: logs/ci/<date>/task-refs-audit/task_ref_integrity.json)")
    args = ap.parse_args()

    root = repo_root()
    d = date.today().strftime("%Y-%m-%d")
    out_path = Path(args.out) if args.out else (root / "logs" / "ci" / d / "task-refs-audit" / "task_ref_integrity.json")

    tasks_json = load_json(root / ".taskmaster" / "tasks" / "tasks.json")
    master_tasks = (tasks_json.get("master") or {}).get("tasks") or []
    if not isinstance(master_tasks, list):
        raise SystemExit("tasks.json: master.tasks is not a list")

    tasks_back = load_json(root / ".taskmaster" / "tasks" / "tasks_back.json")
    tasks_gameplay = load_json(root / ".taskmaster" / "tasks" / "tasks_gameplay.json")
    if not isinstance(tasks_back, list) or not isinstance(tasks_gameplay, list):
        raise SystemExit("tasks_back.json/tasks_gameplay.json must be JSON arrays")

    adr_statuses = collect_adr_statuses(root)
    event_types = collect_event_types(root)

    findings: list[Finding] = []

    # Audit view tasks (self-contained)
    for view_name, view in [("tasks_back.json", tasks_back), ("tasks_gameplay.json", tasks_gameplay)]:
        for t in view:
            if not isinstance(t, dict):
                continue
            findings.extend(audit_view_task(root=root, view_name=view_name, task=t, adr_statuses=adr_statuses, event_types=event_types))

    # Audit master tasks vs views
    for m in master_tasks:
        if not isinstance(m, dict):
            continue
        tid = m.get("id")
        if tid is None:
            continue
        try:
            tm_id = int(str(tid))
        except ValueError:
            continue
        back_entry = find_task_by_taskmaster_id(tasks_back, tm_id)
        gameplay_entry = find_task_by_taskmaster_id(tasks_gameplay, tm_id)
        findings.extend(audit_master_task(root=root, master_task=m, back_task=back_entry, gameplay_task=gameplay_entry))

    # Summarize
    by_sev: dict[str, list[dict[str, Any]]] = {"P0": [], "P1": [], "P2": []}
    for f in findings:
        by_sev.setdefault(f.severity, [])
        by_sev[f.severity].append(
            {
                "where": f.where,
                "task_id": f.task_id,
                "field": f.field,
                "message": f.message,
            }
        )

    report = {
        "date": d,
        "summary": {
            "P0": len(by_sev.get("P0", [])),
            "P1": len(by_sev.get("P1", [])),
            "P2": len(by_sev.get("P2", [])),
        },
        "findings": by_sev,
        "stats": {
            "master_tasks": len(master_tasks),
            "tasks_back": len(tasks_back),
            "tasks_gameplay": len(tasks_gameplay),
            "adr_files": len(adr_statuses),
            "contract_event_types": len(event_types),
        },
    }

    write_json(out_path, report)

    # Print a concise summary for CI-style consumption
    p0 = report["summary"]["P0"]
    p1 = report["summary"]["P1"]
    p2 = report["summary"]["P2"]
    print(f"TASK_REF_INTEGRITY summary P0={p0} P1={p1} P2={p2} out={out_path}")

    return 1 if p0 else 0


if __name__ == "__main__":
    raise SystemExit(main())

