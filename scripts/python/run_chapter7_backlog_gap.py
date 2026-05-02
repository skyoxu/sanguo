#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


TASKS_JSON = Path(".taskmaster/tasks/tasks.json")
TASKS_BACK = Path(".taskmaster/tasks/tasks_back.json")
TASKS_GAMEPLAY = Path(".taskmaster/tasks/tasks_gameplay.json")


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _resolve_path(repo_root: Path, value: str | Path) -> Path:
    path = value if isinstance(value, Path) else Path(value)
    return path if path.is_absolute() else (repo_root / path)


def _contract_path(repo_root: Path, value: Path) -> str:
    resolved = _resolve_path(repo_root, value)
    return str(resolved.resolve()).replace("\\", "/")


def _normalize_rel(path: Path) -> str:
    return path.as_posix().lstrip("./")


def _tokenize(text: str) -> set[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "into",
        "from",
        "can",
        "are",
        "but",
        "all",
        "not",
        "you",
        "your",
        "their",
        "then",
        "than",
        "only",
        "through",
        "have",
        "has",
        "had",
        "will",
        "would",
        "should",
        "could",
        "must",
        "being",
        "player",
        "game",
        "system",
        "task",
        "implement",
        "create",
        "develop",
        "design",
        "build",
        "wire",
        "surfaces",
        "surface",
    }
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\\-]+", text.lower())
    return {word for word in words if len(word) > 2 and word not in stop}


def _load_tasks(repo_root: Path, tasks_json_path: Path) -> list[dict[str, Any]]:
    payload = _read_json(_resolve_path(repo_root, tasks_json_path))
    tasks = payload.get("master", {}).get("tasks", []) if isinstance(payload, dict) else []
    if not isinstance(tasks, list):
        raise ValueError("tasks.json master.tasks must be a list")
    return [item for item in tasks if isinstance(item, dict)]


def _task_text(task: dict[str, Any]) -> str:
    parts = [
        str(task.get("title") or ""),
        str(task.get("description") or ""),
        str(task.get("details") or ""),
    ]
    for subtask in task.get("subtasks") or []:
        if isinstance(subtask, dict):
            parts.extend(
                [
                    str(subtask.get("title") or ""),
                    str(subtask.get("description") or ""),
                    str(subtask.get("details") or ""),
                ]
            )
    return "\n".join(parts)


def _score(query_tokens: set[str], task_tokens: set[str], title_tokens: set[str]) -> float:
    if not query_tokens or not task_tokens:
        return 0.0
    shared = query_tokens & task_tokens
    if not shared:
        return 0.0
    jaccard = len(shared) / max(1, len(query_tokens | task_tokens))
    query_coverage = len(shared) / max(1, len(query_tokens))
    title_bonus = len(query_tokens & title_tokens) * 0.03
    return round((jaccard * 0.45) + (query_coverage * 0.55) + title_bonus, 4)


def _parse_epic_stories(epics_text: str) -> list[dict[str, str]]:
    stories: list[dict[str, str]] = []
    current_epic = ""
    for raw in epics_text.splitlines():
        line = raw.strip()
        if line.startswith("## Epic "):
            current_epic = line
            continue
        if line.startswith("- As a "):
            stories.append({"epic": current_epic, "story": line[2:].strip()})
    return stories


def _extract_duplicate_clusters(duplicate_audit_text: str) -> list[str]:
    clusters: list[str] = []
    capture = False
    for raw in duplicate_audit_text.splitlines():
        line = raw.strip()
        if line == "## High-overlap clusters":
            capture = True
            continue
        if capture and line.startswith("### "):
            clusters.append(line.removeprefix("### ").strip())
        elif capture and line.startswith("## "):
            break
    return clusters


def _extract_gap_signals(design_text: str) -> list[str]:
    signals: list[str] = []
    keywords = [
        "partial",
        "partially",
        "still",
        "not fully",
        "need ",
        "needs ",
        "remaining",
        "未",
        "仍",
        "待",
        "缺",
        "不完整",
        "未完全",
        "后续",
    ]
    strong_nouns = {
        "surface",
        "surfaces",
        "panel",
        "panels",
        "dialog",
        "flow",
        "flows",
        "screen",
        "screens",
        "report",
        "reports",
        "readout",
        "readouts",
        "onboarding",
        "tutorial",
        "achievement",
        "achievements",
        "difficulty",
        "reward",
        "rewards",
        "meta",
        "audit",
        "migration",
        "summary",
    }
    for raw in design_text.splitlines():
        line = raw.strip()
        if len(line) < 18 or len(line) > 260:
            continue
        if line.startswith("#") or line.startswith("|") or line.startswith("```"):
            continue
        lowered = line.lower()
        if not (any(keyword in lowered for keyword in keywords) or any(keyword in line for keyword in ["未", "仍", "待", "缺", "不完整", "未完全", "后续"])):
            continue
        token_hits = _tokenize(line)
        if not (token_hits & strong_nouns):
            continue
        if any(
            phrase in lowered
            for phrase in [
                "当前里程碑的价值",
                "玩法框架仍然",
                "建造决策既是",
                "内容段落类型",
                "如果未来扩展版本",
                "如果后续要补正式视觉",
                "核心信息传达仍应",
                "玩家认为高压来自系统",
                "可在后续版本评估",
                "主要短板在玩家面收口",
            ]
        ):
            continue
        if any(keyword in lowered for keyword in keywords) or any(keyword in line for keyword in ["未", "仍", "待", "缺", "不完整", "未完全", "后续"]):
            signals.append(line)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in signals:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _top_matches(text: str, scored_tasks: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    query_tokens = _tokenize(text)
    matches: list[dict[str, Any]] = []
    for task in scored_tasks:
        score = _score(query_tokens, task["tokens"], task["title_tokens"])
        if score <= 0:
            continue
        matches.append(
            {
                "task_id": task["task_id"],
                "title": task["title"],
                "status": task["status"],
                "score": score,
            }
        )
    matches.sort(key=lambda item: (-item["score"], item["task_id"]))
    return matches[:limit]


def _bucket_for_match(matches: list[dict[str, Any]], *, threshold: float = 0.06) -> str:
    if not matches:
        return "not-clearly-covered"
    top = matches[0]
    if float(top["score"]) < threshold:
        return "not-clearly-covered"
    task_id = int(top["task_id"])
    if 1 <= task_id <= 40:
        return "covered-by-t1-t40"
    if 41 <= task_id <= 46:
        return "covered-by-t41-t46"
    return "covered-by-existing-post-46"


def analyze(
    *,
    repo_root: Path,
    tasks_json_path: Path,
    tasks_back_path: Path,
    tasks_gameplay_path: Path,
    design_doc_path: Path,
    epics_doc_path: Path,
    duplicate_audit_path: Path,
    delivery_profile: str,
) -> dict[str, Any]:
    tasks = _load_tasks(repo_root, tasks_json_path)
    scored_tasks: list[dict[str, Any]] = []
    for task in tasks:
        task_id = int(task.get("id") or 0)
        title = str(task.get("title") or "")
        task_text = _task_text(task)
        scored_tasks.append(
            {
                "task_id": task_id,
                "title": title,
                "status": str(task.get("status") or ""),
                "tokens": _tokenize(task_text),
                "title_tokens": _tokenize(title),
            }
        )

    design_text = _read_text(_resolve_path(repo_root, design_doc_path))
    epics_text = _read_text(_resolve_path(repo_root, epics_doc_path))
    duplicate_text = _read_text(_resolve_path(repo_root, duplicate_audit_path))

    epic_stories = _parse_epic_stories(epics_text)
    story_mappings: list[dict[str, Any]] = []
    for item in epic_stories:
        query_text = f"{item['epic']} {item['story']}"
        matches = _top_matches(query_text, scored_tasks)
        story_mappings.append(
            {
                "epic": item["epic"],
                "story": item["story"],
                "bucket": _bucket_for_match(matches),
                "top_matches": matches,
            }
        )

    gap_signals = _extract_gap_signals(design_text)
    design_gap_mappings: list[dict[str, Any]] = []
    for signal in gap_signals:
        matches = _top_matches(signal, scored_tasks)
        bucket = _bucket_for_match(matches)
        design_gap_mappings.append(
            {
                "signal": signal,
                "bucket": bucket,
                "top_matches": matches,
            }
        )

    candidate_task_gaps = [
        item for item in design_gap_mappings
        if item["bucket"] == "not-clearly-covered"
    ]

    counts = {
        "covered_by_t1_t40": sum(1 for item in story_mappings if item["bucket"] == "covered-by-t1-t40"),
        "covered_by_t41_t46": sum(1 for item in story_mappings if item["bucket"] == "covered-by-t41-t46"),
        "not_clearly_covered": sum(1 for item in story_mappings if item["bucket"] == "not-clearly-covered"),
        "candidate_task_gaps": len(candidate_task_gaps),
    }

    should_create_tasks = len(candidate_task_gaps) > 0 or counts["not_clearly_covered"] > 0
    if should_create_tasks:
        why = "Some BMAD stories or design gap signals are not clearly covered by T1-T46 and may justify T47+ after review."
    else:
        why = "BMAD epic stories are already absorbed by T1-T46; current signals look like wiring/readout closure rather than new backlog ownership."

    return {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": "run-chapter7-backlog-gap",
        "status": "ok",
        "delivery_profile": delivery_profile,
        "input_contract": {
            "repo_root": str(repo_root.resolve()).replace("\\", "/"),
            "tasks_json_path": _contract_path(repo_root, tasks_json_path),
            "tasks_back_path": _contract_path(repo_root, tasks_back_path),
            "tasks_gameplay_path": _contract_path(repo_root, tasks_gameplay_path),
            "design_doc_path": _contract_path(repo_root, design_doc_path),
            "epics_doc_path": _contract_path(repo_root, epics_doc_path),
            "duplicate_audit_path": _contract_path(repo_root, duplicate_audit_path),
        },
        "story_count": len(epic_stories),
        "story_bucket_counts": counts,
        "duplicate_risk_clusters": _extract_duplicate_clusters(duplicate_text),
        "story_mappings": story_mappings,
        "design_gap_signal_count": len(gap_signals),
        "design_gap_mappings": design_gap_mappings,
        "candidate_task_gaps": candidate_task_gaps,
        "recommendation": {
            "should_create_tasks": should_create_tasks,
            "why": why,
            "next_action": "review-candidate-gaps" if should_create_tasks else "do-not-create-tasks-yet",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze BMAD design/epics against T1-T46 and route Chapter 7 backlog-gap decisions.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--delivery-profile", default="fast-ship")
    parser.add_argument("--tasks-json-path", default=str(TASKS_JSON))
    parser.add_argument("--tasks-back-path", default=str(TASKS_BACK))
    parser.add_argument("--tasks-gameplay-path", default=str(TASKS_GAMEPLAY))
    parser.add_argument("--design-doc-path", required=True)
    parser.add_argument("--epics-doc-path", required=True)
    parser.add_argument("--duplicate-audit-path", required=True)
    parser.add_argument("--out-json", default="")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if args.self_check:
        payload = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "action": "run-chapter7-backlog-gap",
            "status": "ok",
            "delivery_profile": args.delivery_profile,
            "input_contract": {
                "repo_root": str(repo_root.resolve()).replace("\\", "/"),
                "tasks_json_path": _contract_path(repo_root, Path(args.tasks_json_path)),
                "tasks_back_path": _contract_path(repo_root, Path(args.tasks_back_path)),
                "tasks_gameplay_path": _contract_path(repo_root, Path(args.tasks_gameplay_path)),
                "design_doc_path": _contract_path(repo_root, Path(args.design_doc_path)),
                "epics_doc_path": _contract_path(repo_root, Path(args.epics_doc_path)),
                "duplicate_audit_path": _contract_path(repo_root, Path(args.duplicate_audit_path)),
            },
            "planned_steps": ["load-inputs", "score-stories", "score-gap-signals", "emit-summary"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    payload = analyze(
        repo_root=repo_root,
        tasks_json_path=Path(args.tasks_json_path),
        tasks_back_path=Path(args.tasks_back_path),
        tasks_gameplay_path=Path(args.tasks_gameplay_path),
        design_doc_path=Path(args.design_doc_path),
        epics_doc_path=Path(args.epics_doc_path),
        duplicate_audit_path=Path(args.duplicate_audit_path),
        delivery_profile=args.delivery_profile,
    )
    out = Path(args.out_json) if args.out_json else (
        repo_root / "logs" / "ci" / _today() / "chapter7-backlog-gap" / "summary.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(
        "CHAPTER7_BACKLOG_GAP "
        f"status={payload['status']} candidate_gaps={len(payload['candidate_task_gaps'])} out={str(out).replace('\\\\', '/')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
