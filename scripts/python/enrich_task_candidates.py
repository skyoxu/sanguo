#!/usr/bin/env python3
"""Enrich normalized task candidates before triplet compilation.

The enrichment layer is deterministic and repository-aware. It uses existing ADRs,
overlays, contract event constants, tests, and task views as evidence to improve
candidates, but it still does not write final task files directly.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

DEFAULT_CANDIDATES = "logs/ci/task-generation/task-candidates.normalized.json"
DEFAULT_OUT = "logs/ci/task-generation/task-candidates.enriched.json"
ALLOWED_LAYERS = {"docs", "core", "adapter", "ci"}
CHAPTER_DEFAULTS = {
    "ci": ["CH01", "CH06", "CH07", "CH10"],
    "core": ["CH01", "CH05", "CH06", "CH07", "CH09"],
    "adapter": ["CH01", "CH05", "CH06", "CH07"],
    "docs": ["CH01", "CH07"],
}
ADR_HINTS = {
    "ci": ["ADR-0005", "ADR-0011"],
    "core": ["ADR-0004", "ADR-0005", "ADR-0024"],
    "adapter": ["ADR-0007", "ADR-0024"],
    "docs": ["ADR-0005"],
}
EVENT_CONST_RE = re.compile(r'public\s+const\s+string\s+(\w+)\s*=\s*"([a-z0-9._-]+)"\s*;')


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def words(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z0-9]{3,}", text)}


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def collect_adr_ids(root: Path) -> set[str]:
    ids = set()
    for path in (root / "docs" / "adr").glob("ADR-*.md"):
        match = re.match(r"ADR-\d+", path.stem)
        if match:
            ids.add(match.group(0))
    return ids


def collect_overlay_paths(root: Path) -> list[str]:
    base = root / "docs" / "architecture" / "overlays"
    if not base.exists():
        return []
    return sorted(rel(p, root) for p in base.rglob("*.md") if p.is_file())


def collect_test_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for base_rel in ["Game.Core.Tests", "Tests.Godot"]:
        base = root / base_rel
        if base.exists():
            paths.extend(rel(p, root) for p in base.rglob("*") if p.is_file() and p.suffix.lower() in {".cs", ".gd"})
    return sorted(paths)


def collect_contract_events(root: Path) -> list[dict[str, str]]:
    base = root / "Game.Core" / "Contracts"
    if not base.exists():
        return []
    events: list[dict[str, str]] = []
    for path in sorted(base.rglob("*.cs")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for symbol, event_type in EVENT_CONST_RE.findall(text):
            events.append({"event": event_type, "symbol": symbol, "source": rel(path, root)})
    by_event: dict[str, dict[str, str]] = {}
    for item in events:
        by_event.setdefault(item["event"], item)
    return sorted(by_event.values(), key=lambda x: x["event"])


def load_existing_tasks(root: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for rel_path in [".taskmaster/tasks/tasks_back.json", ".taskmaster/tasks/tasks_gameplay.json"]:
        data = load_json(root / rel_path, [])
        if isinstance(data, list):
            tasks.extend(x for x in data if isinstance(x, dict))
    return tasks


def normalize_layer(raw: str) -> str:
    low = raw.strip().lower()
    if low in ALLOWED_LAYERS:
        return low
    if low in {"architecture", "overlay", "adr", "documentation"}:
        return "docs"
    if low in {"test", "qa", "quality", "tool", "pipeline", "bootstrap"}:
        return "ci"
    if low in {"domain", "contract", "model", "service"}:
        return "core"
    if low in {"feature", "gameplay", "ui", "godot", "presentation"}:
        return "adapter"
    return "core"


def infer_layer(task: dict[str, Any]) -> str:
    text = " ".join(str(task.get(k, "")) for k in ["title", "description", "owner"])
    labels = {str(x).lower() for x in task.get("labels", [])}
    low = text.lower()
    if labels & {"docs", "doc", "adr", "overlay"} or any(token in low for token in ["adr", "overlay", "document"]):
        return "docs"
    if labels & {"test", "acceptance", "qa", "ci"} or any(token in low for token in ["test", "acceptance", "qa", "pipeline", "bootstrap", "validator"]):
        return "ci"
    if labels & {"core", "contract", "domain"} or any(token in low for token in ["contract", "domain", "core", "rng", "combat", "reward", "rule"]):
        return "core"
    if labels & {"gdd", "gameplay", "ui", "godot", "adapter", "prd", "feature"} or any(token in low for token in ["ui", "godot", "player", "scene", "hud", "input"]):
        return "adapter"
    return normalize_layer(str(task.get("layer") or "core"))


def infer_owner(task: dict[str, Any], layer: str) -> str:
    labels = {str(x).lower() for x in task.get("labels", [])}
    raw = str(task.get("owner") or "").strip().lower()
    if raw in {"gameplay", "architecture"}:
        return raw
    if labels & {"gdd", "gameplay"}:
        return "gameplay"
    if layer in {"core", "adapter"} and any(token in str(task.get("description", "")).lower() for token in ["player", "gameplay", "godot", "ui", "combat", "reward"]):
        return "gameplay"
    return "architecture"


def task_search_text(task: dict[str, Any]) -> str:
    return " ".join([
        str(task.get("title", "")),
        str(task.get("description", "")),
        " ".join(map(str, task.get("labels", []))),
    ])


def match_by_words(task: dict[str, Any], paths: list[str], limit: int) -> list[str]:
    query = words(task_search_text(task))
    scored: list[tuple[int, str]] = []
    for path in paths:
        score = len(query & words(path))
        if score:
            scored.append((score, path))
    return [path for _score, path in sorted(scored, key=lambda x: (-x[0], x[1]))[:limit]]


def match_contract_events(task: dict[str, Any], events: list[dict[str, str]], limit: int) -> list[str]:
    generic = {"core", "game", "event", "events", "type", "types", "task", "tasks"}
    query = words(task_search_text(task)) - generic
    scored: list[tuple[int, str]] = []
    for item in events:
        haystack = f"{item['event']} {item['symbol']} {item['source']}"
        score = len(query & (words(haystack) - generic))
        if score >= 2:
            scored.append((score, item["event"]))
    return [event for _score, event in sorted(scored, key=lambda x: (-x[0], x[1]))[:limit]]


def detect_duplicates(task: dict[str, Any], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    title = str(task.get("title", ""))
    out = []
    for old in existing:
        ratio = similarity(title, str(old.get("title", "")))
        if ratio >= 0.82:
            out.append({"id": old.get("id"), "title": old.get("title"), "similarity": round(ratio, 3)})
    return out[:8]


def ensure_list(task: dict[str, Any], key: str) -> list[Any]:
    value = task.get(key)
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def unique(items: list[Any]) -> list[Any]:
    seen = set()
    out = []
    for item in items:
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if marker not in seen:
            seen.add(marker)
            out.append(item)
    return out


def enrich(root: Path, candidates: dict[str, Any]) -> dict[str, Any]:
    adr_ids = collect_adr_ids(root)
    overlays = collect_overlay_paths(root)
    tests = collect_test_paths(root)
    contract_events = collect_contract_events(root)
    known_events = {item["event"] for item in contract_events}
    existing = load_existing_tasks(root)
    enriched = []
    for raw in candidates.get("candidates", []):
        task = dict(raw)
        layer = infer_layer(task)
        owner = infer_owner(task, layer)
        labels = [str(x) for x in ensure_list(task, "labels")]
        labels.extend([layer, owner])
        if task.get("generation_mode"):
            labels.append(str(task["generation_mode"]))
        adr_refs = [str(x) for x in ensure_list(task, "adr_refs")]
        for adr in ADR_HINTS.get(layer, []):
            if adr in adr_ids:
                adr_refs.append(adr)
        overlay_refs = [str(x) for x in ensure_list(task, "overlay_refs")]
        if not overlay_refs:
            overlay_refs.extend(match_by_words(task, overlays, 4))
        if not overlay_refs and overlays:
            overlay_refs.append(next((p for p in overlays if p.endswith("_index.md")), overlays[0]))
        test_refs = [str(x) for x in ensure_list(task, "test_refs")]
        if not test_refs:
            test_refs.extend(match_by_words(task, tests, 6))
        contract_refs = [str(x) for x in ensure_list(task, "contractRefs") if str(x) in known_events]
        if not contract_refs and layer in {"core", "adapter"}:
            contract_refs.extend(match_contract_events(task, contract_events, 6))
        acceptance = [str(x) for x in ensure_list(task, "acceptance")]
        if not acceptance:
            for rid in ensure_list(task, "requirement_ids")[:4]:
                acceptance.append(f"Requirement {rid} is implemented with traceable tests and evidence. Refs: {' '.join(test_refs[:2])}".strip())
        else:
            acceptance = [a if "Refs:" in a or not test_refs else f"{a} Refs: {' '.join(test_refs[:2])}" for a in acceptance]
        test_strategy = [str(x) for x in ensure_list(task, "test_strategy")]
        if not test_strategy:
            test_strategy = ["Run targeted unit or Godot tests referenced by test_refs, then run the Chapter 3.8 triplet baseline validators."]
        elif not any("Chapter 3.8" in item or "Chapter 3.7" in item for item in test_strategy):
            test_strategy.append("Run the Chapter 3.8 triplet baseline validators after writing this task to a task view.")
        evidence_refs = [str(x) for x in ensure_list(task, "evidence_refs")]
        evidence_refs.extend(str(x) for x in ensure_list(task, "source_refs"))
        evidence_refs.extend(overlay_refs[:2])
        evidence_refs.extend(test_refs[:2])
        task.update({
            "layer": layer,
            "owner": owner,
            "labels": sorted(set(labels)),
            "adr_refs": sorted(set(x for x in adr_refs if x in adr_ids)),
            "chapter_refs": sorted(set([str(x) for x in ensure_list(task, "chapter_refs")] + CHAPTER_DEFAULTS.get(layer, []))),
            "overlay_refs": unique(overlay_refs),
            "test_refs": unique(test_refs),
            "contractRefs": unique(contract_refs),
            "acceptance": unique(acceptance),
            "test_strategy": unique(test_strategy),
            "evidence_refs": unique(evidence_refs),
            "duplicate_candidates": detect_duplicates(task, existing),
            "enrichment_status": "ok",
        })
        enriched.append(task)
    return {
        "schema": "task-generation.enriched-candidates.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "candidate_count": len(enriched),
        "inventory": {
            "adr_count": len(adr_ids),
            "overlay_count": len(overlays),
            "test_count": len(tests),
            "contract_event_count": len(contract_events),
            "existing_task_count": len(existing),
        },
        "candidates": enriched,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich task candidates using repository evidence.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    result = enrich(root, load_json(root / args.candidates, {"candidates": []}))
    out = root / args.out
    write_json(out, result)
    print(f"enriched_candidates={out} candidates={result['candidate_count']} inventory={result['inventory']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
