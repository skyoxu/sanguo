#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup non-portable / non-testable acceptance items by migrating them to test_strategy.

Why:
  Acceptance should remain focused on observable, testable behavior.
  Non-portable items like absolute local paths or "Local demo references" create
  brittle acceptance semantics and should not block semantic alignment.

Policy (deterministic):
  - If an acceptance line contains:
      * absolute Windows path (e.g. C:\...)
      * "Local demo references"
    then:
      1) migrate the line to test_strategy (dedupe against existing test_strategy)
      2) blank the acceptance slot to preserve index stability (ACC:T<id>.<n>)
  - When migrating, if the content is highly duplicate of an existing test_strategy item,
    we do NOT add a new item (we still blank the acceptance slot).

This script does NOT modify Refs: tokens and does NOT generate tests.

Outputs:
  logs/ci/<YYYY-MM-DD>/sc-acceptance-migrate/ (report.json, report.md)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ABS_PATH_RE = re.compile(r"\b[A-Za-z]:\\")
LOCAL_DEMO_RE = re.compile(r"\bLocal demo references\b", re.IGNORECASE)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_md_utf8_bom(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("\ufeff" + text + "\n").encode("utf-8"))


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def ci_dir(name: str) -> Path:
    return repo_root() / "logs" / "ci" / today_str() / name


def ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    s = str(value).strip()
    return [s] if s else []


def normalize_for_dedupe(text: str) -> str:
    s = str(text or "").strip()
    # Drop Refs: tail for semantic dedupe.
    s = re.sub(r"\bRefs\s*:\s*.+$", "", s, flags=re.IGNORECASE).strip()
    s = s.replace("`", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower()


def is_highly_duplicate(candidate: str, existing: str, *, threshold: float) -> bool:
    a = normalize_for_dedupe(candidate)
    b = normalize_for_dedupe(existing)
    if not a or not b:
        return False
    if a == b:
        return True
    # Containment is a strong signal.
    if a in b or b in a:
        return True
    return SequenceMatcher(a=a, b=b).ratio() >= threshold


@dataclass(frozen=True)
class MigrationItem:
    task_id: int
    view: str
    index_1_based: int
    reason: str
    acceptance_text: str
    action: str  # migrated|dedupe_skip|skipped


def classify_reason(line: str) -> str | None:
    s = str(line or "")
    if LOCAL_DEMO_RE.search(s):
        return "local-demo-references"
    if ABS_PATH_RE.search(s):
        return "absolute-path"
    return None


def migrate_view(*, view: list[dict[str, Any]], view_name: str, threshold: float) -> tuple[int, list[MigrationItem]]:
    changed = 0
    items: list[MigrationItem] = []
    for entry in view:
        if not isinstance(entry, dict):
            continue
        tid = entry.get("taskmaster_id")
        if not isinstance(tid, int):
            continue
        acceptance = entry.get("acceptance") or []
        if not isinstance(acceptance, list):
            continue
        test_strategy = ensure_list(entry.get("test_strategy"))

        for idx, raw in enumerate(list(acceptance)):
            text = str(raw or "").strip()
            if not text:
                continue
            reason = classify_reason(text)
            if not reason:
                continue

            # Blank acceptance slot to preserve index stability.
            acceptance[idx] = ""
            changed += 1

            # Dedupe against existing test_strategy.
            duplicate = any(is_highly_duplicate(text, existing, threshold=threshold) for existing in test_strategy)
            if duplicate:
                items.append(
                    MigrationItem(
                        task_id=tid,
                        view=view_name,
                        index_1_based=idx + 1,
                        reason=reason,
                        acceptance_text=text,
                        action="dedupe_skip",
                    )
                )
                continue

            # Append migrated text with a stable tag.
            migrated = f"[MIGRATED_FROM_ACCEPTANCE:{reason}] {text}"
            test_strategy.append(migrated)
            items.append(
                MigrationItem(
                    task_id=tid,
                    view=view_name,
                    index_1_based=idx + 1,
                    reason=reason,
                    acceptance_text=text,
                    action="migrated",
                )
            )

        entry["acceptance"] = acceptance
        entry["test_strategy"] = test_strategy

    return changed, items


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate non-portable acceptance lines to test_strategy (with dedupe).")
    ap.add_argument("--apply", action="store_true", help="Write changes to tasks_back/tasks_gameplay.")
    ap.add_argument("--dedupe-threshold", type=float, default=0.9, help="Similarity threshold (default: 0.9).")
    args = ap.parse_args()

    root = repo_root()
    back_path = root / ".taskmaster" / "tasks" / "tasks_back.json"
    gameplay_path = root / ".taskmaster" / "tasks" / "tasks_gameplay.json"

    back = read_json(back_path)
    gameplay = read_json(gameplay_path)
    if not isinstance(back, list) or not isinstance(gameplay, list):
        print("SC_ACCEPTANCE_MIGRATE status=fail reason=views_not_arrays")
        return 2

    back_changed, back_items = migrate_view(view=back, view_name="back", threshold=float(args.dedupe_threshold))
    gameplay_changed, gameplay_items = migrate_view(view=gameplay, view_name="gameplay", threshold=float(args.dedupe_threshold))

    out_dir = ci_dir("sc-acceptance-migrate")
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "date": today_str(),
        "apply": bool(args.apply),
        "dedupe_threshold": float(args.dedupe_threshold),
        "changed": {"back": back_changed, "gameplay": gameplay_changed, "total": back_changed + gameplay_changed},
        "migrations": [i.__dict__ for i in (back_items + gameplay_items)],
        "counts_by_reason": {},
        "counts_by_action": {},
    }
    for it in report["migrations"]:
        report["counts_by_reason"][it["reason"]] = report["counts_by_reason"].get(it["reason"], 0) + 1
        report["counts_by_action"][it["action"]] = report["counts_by_action"].get(it["action"], 0) + 1

    write_json(out_dir / "report.json", report)

    md: list[str] = []
    md.append(f"# Acceptance migrate report ({today_str()})")
    md.append("")
    md.append(f"- apply: {bool(args.apply)}")
    md.append(f"- dedupe_threshold: {float(args.dedupe_threshold)}")
    md.append(f"- changed.total: {report['changed']['total']} (back={back_changed}, gameplay={gameplay_changed})")
    md.append("")
    md.append("## Counts")
    md.append(f"- by_reason: {json.dumps(report['counts_by_reason'], ensure_ascii=False)}")
    md.append(f"- by_action: {json.dumps(report['counts_by_action'], ensure_ascii=False)}")
    md.append("")
    md.append("## Sample (first 60)")
    for it in report["migrations"][:60]:
        md.append(f"- T{it['task_id']} [{it['view']}] acceptance[{it['index_1_based']}]: {it['reason']} action={it['action']}")
        md.append(f"  - {it['acceptance_text']}")

    write_md_utf8_bom(out_dir / "report.md", "\n".join(md))

    if args.apply:
        back_path.write_text(json.dumps(back, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        gameplay_path.write_text(json.dumps(gameplay, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    status = "ok"
    print(f"SC_ACCEPTANCE_MIGRATE status={status} apply={bool(args.apply)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
