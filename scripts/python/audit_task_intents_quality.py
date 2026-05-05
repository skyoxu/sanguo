#!/usr/bin/env python3
"""Audit normalized task intents for generic quality risks."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_INTENTS = "logs/ci/task-generation/task-intents.normalized.json"
DEFAULT_OUT = "logs/ci/task-generation/task-intents.quality.json"
NOISY_TITLE_RE = re.compile(r"\b(adr[- ]refs|test[- ]refs|tasks\.json|taskmaster|\.cs|\.gd|\.md)\b", re.IGNORECASE)
GENERIC_TITLE_RE = re.compile(r"^(Implement|Validate|Document|Create|Build|Set up|Add test coverage for) (requirement|slice|testing)$", re.IGNORECASE)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def title_key(title: str) -> str:
    words = re.findall(r"[A-Za-z]+|\d+", title.lower())
    if "part" in words:
        idx = words.index("part")
        if idx + 1 < len(words) and words[idx + 1].isdigit():
            return " ".join(words[:2] + words[idx : idx + 2] + words[idx + 2 : idx + 6])
    return " ".join(words[:8])


def audit(intents: dict[str, Any], max_anchors_per_intent: int) -> dict[str, Any]:
    rows = []
    titles = [str(intent.get("title", "")) for intent in intents.get("intents", [])]
    title_counts = Counter(title_key(title) for title in titles)
    for intent in intents.get("intents", []):
        iid = str(intent.get("id", ""))
        title = str(intent.get("title", ""))
        covered = int(intent.get("covered_anchor_count") or 0)
        issues = []
        if covered > max_anchors_per_intent:
            issues.append("too_many_anchors")
        if NOISY_TITLE_RE.search(title):
            issues.append("metadata_noise_in_title")
        if GENERIC_TITLE_RE.search(title):
            issues.append("generic_title")
        if title_counts[title_key(title)] > 1:
            issues.append("near_duplicate_title_prefix")
        if not intent.get("requirement_ids") or not intent.get("source_refs"):
            issues.append("missing_traceability")
        if issues:
            rows.append(
                {
                    "id": iid,
                    "title": title,
                    "covered_anchor_count": covered,
                    "topic": intent.get("topic"),
                    "layer": intent.get("layer"),
                    "owner": intent.get("owner"),
                    "issues": issues,
                }
            )
    issue_counts: Counter[str] = Counter(issue for row in rows for issue in row["issues"])
    return {
        "schema": "task-generation.task-intents-quality.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "intent_count": len(intents.get("intents", [])),
        "issue_count": len(rows),
        "issue_counts": dict(sorted(issue_counts.items())),
        "status": "ok" if not rows else "review",
        "issues": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit normalized task intent quality.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--intents", default=DEFAULT_INTENTS)
    parser.add_argument("--max-anchors-per-intent", type=int, default=8)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    result = audit(load_json(root / args.intents), args.max_anchors_per_intent)
    out = root / args.out
    write_json(out, result)
    print(f"task_intents_quality={out} status={result['status']} issues={result['issue_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
