#!/usr/bin/env python3
"""Normalize requirement anchors into implementation-shaped task intents.

This script is deterministic. It rewrites raw planning anchors into an
auditable middle layer that is closer to Task Master task semantics without
letting an LLM write final task files directly.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DEFAULT_REQUIREMENTS = "logs/ci/task-generation/requirements.index.json"
DEFAULT_OUT = "logs/ci/task-generation/task-intents.normalized.json"

STOP_WORDS = {
    "acceptance",
    "action",
    "adr",
    "adrs",
    "and",
    "any",
    "artifact",
    "based",
    "before",
    "candidate",
    "can",
    "chapter",
    "check",
    "current",
    "docs",
    "document",
    "empty",
    "ensure",
    "evidence",
    "feature",
    "file",
    "files",
    "flow",
    "for",
    "from",
    "game",
    "gate",
    "gates",
    "generated",
    "implementation",
    "integration",
    "json",
    "logs",
    "matrix",
    "must",
    "not",
    "player",
    "pass",
    "passes",
    "prd",
    "refs",
    "requirement",
    "requirements",
    "remain",
    "scenario",
    "should",
    "source",
    "system",
    "task",
    "taskmaster",
    "tasks",
    "test",
    "tests",
    "that",
    "this",
    "then",
    "update",
    "using",
    "validate",
    "when",
    "with",
}

TOPIC_RULES: list[tuple[str, set[str], str, str]] = [
    ("bootstrap", {"bootstrap", "startup", "start", "project", "baseline", "environment", "root"}, "ci", "architecture"),
    ("build-export", {"build", "export", "windows", "release", "startup", "runtime"}, "ci", "architecture"),
    ("validation-gates", {"validate", "validation", "gate", "audit", "evidence", "check", "coverage"}, "ci", "architecture"),
    ("testing", {"test", "tests", "testing", "qa", "acceptance", "fixture"}, "ci", "architecture"),
    ("combat-loop", {"combat", "damage", "target", "targeting", "attack", "enemy", "projectile", "battle"}, "core", "gameplay"),
    ("spawn-wave", {"spawn", "wave", "enemy", "cadence", "pressure", "elite"}, "core", "gameplay"),
    ("resource-economy", {"resource", "gold", "economy", "cost", "upgrade", "repair", "integer"}, "core", "gameplay"),
    ("reward-progression", {"reward", "progression", "choice", "relic", "card", "upgrade", "tech"}, "core", "gameplay"),
    ("run-state", {"run", "state", "turn", "day", "night", "cycle", "win", "lose", "terminal"}, "core", "gameplay"),
    ("save-meta", {"save", "autosave", "migration", "cloud", "achievement", "settings"}, "adapter", "gameplay"),
    ("ui-hud", {"ui", "hud", "screen", "surface", "panel", "display", "menu", "prompt"}, "adapter", "gameplay"),
    ("input-camera", {"input", "camera", "scroll", "keyboard", "mouse", "interaction"}, "adapter", "gameplay"),
    ("localization-audio", {"localization", "i18n", "language", "audio", "music", "sfx", "copy"}, "adapter", "gameplay"),
    ("content-authoring", {"content", "catalog", "id", "registry", "authoring", "glossary", "style"}, "docs", "architecture"),
    ("architecture-docs", {"architecture", "adr", "overlay", "contract", "traceability", "guide"}, "docs", "architecture"),
]

TOPIC_TEMPLATES: dict[str, tuple[str, str]] = {
    "bootstrap": ("Establish baseline {focus}", "Create the canonical baseline required by later implementation tasks."),
    "build-export": ("Set up {focus}", "Configure the build, export, and runtime startup path with repeatable evidence."),
    "validation-gates": ("Validate {focus}", "Create deterministic validation gates and evidence paths for this requirement slice."),
    "testing": ("Add test coverage for {focus}", "Add focused tests and fixtures for the covered behavior."),
    "combat-loop": ("Implement {focus}", "Implement the core combat behavior with deterministic resolution and traceable tests."),
    "spawn-wave": ("Create {focus}", "Create the spawning, cadence, or wave progression behavior for the playable loop."),
    "resource-economy": ("Implement {focus}", "Implement integer-safe economy or resource behavior in the core layer."),
    "reward-progression": ("Implement {focus}", "Implement reward, progression, card, relic, or upgrade behavior for the run loop."),
    "run-state": ("Develop {focus}", "Develop deterministic run-state progression and terminal state behavior."),
    "save-meta": ("Build {focus}", "Build persistence, settings, migration, or meta-game behavior with deterministic boundaries."),
    "ui-hud": ("Create {focus}", "Create player-facing UI surfaces and state presentation for this slice."),
    "input-camera": ("Implement {focus}", "Implement input, camera, scrolling, or interaction behavior with bounded runtime effects."),
    "localization-audio": ("Add {focus}", "Add localized copy, language switching, or audio setting behavior."),
    "content-authoring": ("Define {focus}", "Define content IDs, catalogs, authoring rules, or review constraints."),
    "architecture-docs": ("Document {focus}", "Document the architecture or planning contract without adding runtime behavior."),
}

KIND_LAYER = {
    "acceptance": "ci",
    "adr": "docs",
    "epic": "adapter",
    "gdd": "adapter",
    "overlay": "docs",
    "prd": "core",
    "requirement": "core",
    "story": "adapter",
}

KIND_OWNER = {
    "acceptance": "architecture",
    "adr": "architecture",
    "epic": "gameplay",
    "gdd": "gameplay",
    "overlay": "architecture",
    "prd": "gameplay",
    "requirement": "gameplay",
    "story": "gameplay",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def words(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[A-Za-z0-9]{3,}", text)]


def meaningful_words(text: str) -> list[str]:
    return [word for word in words(text) if word not in STOP_WORDS and not re.fullmatch(r"\d+", word)]


def source_words(text: str) -> list[str]:
    return [
        word
        for word in re.findall(r"[A-Za-z0-9]{2,}", text.lower())
        if word not in STOP_WORDS and not re.fullmatch(r"\d+", word)
    ]


def anchor_words(anchor: dict[str, Any]) -> set[str]:
    source = str(anchor.get("source_path", ""))
    text = str(anchor.get("text", ""))
    return set(words(source + " " + text))


def source_stem(anchor: dict[str, Any]) -> str:
    source = str(anchor.get("source_path", "unknown")).replace("\\", "/")
    return source.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()


def source_focus(anchors: list[dict[str, Any]], topic: str, limit: int = 5) -> list[str]:
    counts: Counter[str] = Counter()
    for anchor in anchors:
        for word in source_words(source_stem(anchor).replace("-", " ").replace("_", " ")):
            counts[word] += 1
    picked = [word for word, _count in counts.most_common(limit)]
    if picked:
        return picked
    if topic not in {"testing", "validation-gates", "architecture-docs"}:
        return [part for part in topic.split("-") if part and part not in STOP_WORDS]
    return ["requirement", "slice"]


def priority_of(anchors: list[dict[str, Any]]) -> str:
    values = [str(a.get("priority", "P2")).upper() for a in anchors]
    for priority in ["P0", "P1", "P2", "P3"]:
        if priority in values:
            return priority
    return "P2"


def choose_topic(anchor: dict[str, Any]) -> tuple[str, str, str]:
    tokens = anchor_words(anchor)
    best: tuple[int, str, str, str] | None = None
    for topic, needles, layer, owner in TOPIC_RULES:
        score = len(tokens & needles)
        if score and (best is None or score > best[0]):
            best = (score, topic, layer, owner)
    if best:
        return best[1], best[2], best[3]
    kind = str(anchor.get("kind", "requirement")).lower()
    stem = source_stem(anchor)
    topic_seed = "-".join([w for w in words(stem) if w not in STOP_WORDS][:3]) or kind
    return topic_seed, KIND_LAYER.get(kind, "core"), KIND_OWNER.get(kind, "gameplay")


def title_phrase(anchors: list[dict[str, Any]], topic: str) -> str:
    counts: Counter[str] = Counter()
    for anchor in anchors:
        text = str(anchor.get("text", ""))
        # Source refs and traceability lines are useful for coverage but noisy for task titles.
        if re.search(r"\b(ADR-Refs|Test-Refs|Refs):\s*$", text, re.IGNORECASE):
            continue
        for word in meaningful_words(text):
            counts[word] += 1
    picked = [word for word, _count in counts.most_common(5)]
    if not picked:
        picked = source_focus(anchors, topic)
    phrase = " ".join(picked[:5]).strip()
    return phrase or topic.replace("-", " ")


def title_key(title: str) -> str:
    return " ".join(re.findall(r"[A-Za-z]+|\d+", title.lower())[:6])


def collapse_repeated_words(text: str) -> str:
    words = text.split()
    out: list[str] = []
    idx = 0
    while idx < len(words):
        skipped = False
        for size in range(min(4, (len(words) - idx) // 2), 0, -1):
            left = [w.lower() for w in words[idx : idx + size]]
            right = [w.lower() for w in words[idx + size : idx + size * 2]]
            if left == right:
                out.extend(words[idx : idx + size])
                idx += size * 2
                skipped = True
                break
        if skipped:
            continue
        if not out or out[-1].lower() != words[idx].lower():
            out.append(words[idx])
        idx += 1
    return " ".join(out)


def intent_title(topic: str, focus: str, split_index: int = 0) -> str:
    template, _details = TOPIC_TEMPLATES.get(topic, ("Implement {focus}", "Implement the covered requirement slice."))
    if split_index > 0:
        focus = f"part {split_index} {focus}".strip()
    return collapse_repeated_words(template.format(focus=focus).strip())


def disambiguate_duplicate_titles(intents: list[dict[str, Any]]) -> None:
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for intent in intents:
        by_key[title_key(str(intent.get("title", "")))].append(intent)
    for rows in by_key.values():
        if len(rows) <= 1:
            continue
        for intent in rows:
            source_refs = [str(ref).split(":", 1)[0] for ref in intent.get("source_refs", [])]
            fake_anchors = [{"source_path": ref} for ref in source_refs]
            qualifier = " ".join(source_focus(fake_anchors, str(intent.get("topic", "")), limit=3))
            if not qualifier:
                continue
            title = str(intent.get("title", ""))
            topic = str(intent.get("topic", ""))
            template, _details = TOPIC_TEMPLATES.get(topic, ("Implement {focus}", ""))
            verbs = template.split("{focus}", 1)[0].strip()
            if verbs and title.startswith(verbs):
                remainder = title[len(verbs):].strip()
                intent["title"] = collapse_repeated_words(f"{verbs} {qualifier} {remainder}".strip())
            else:
                intent["title"] = collapse_repeated_words(f"{qualifier} {title}".strip())
    by_key.clear()
    for intent in intents:
        by_key[title_key(str(intent.get("title", "")))].append(intent)
    for rows in by_key.values():
        if len(rows) <= 1:
            continue
        for intent in rows:
            source_refs = [str(ref) for ref in intent.get("source_refs", [])]
            line = ""
            if len(source_refs) == 1 and ":" in source_refs[0]:
                line = source_refs[0].rsplit(":", 1)[-1]
            if line and line.isdigit():
                intent["title"] = collapse_repeated_words(f"{intent['title']} line {line}")


def intent_details(topic: str, layer: str, owner: str, focus: str) -> list[str]:
    _template, lead = TOPIC_TEMPLATES.get(topic, ("Implement {focus}", "Implement the covered requirement slice."))
    layer_hint = {
        "adapter": "Keep Godot-facing behavior behind adapter boundaries and avoid moving domain rules into scenes.",
        "ci": "Keep the validation deterministic and write evidence under logs/.",
        "core": "Keep the implementation in pure core code and avoid Godot dependencies.",
        "docs": "Keep this as planning or governance text and avoid duplicating runtime contracts.",
    }.get(layer, "Keep the implementation scoped and traceable.")
    owner_hint = "Route gameplay semantics to the gameplay view." if owner == "gameplay" else "Route governance and platform work to the back view."
    return [
        lead.format(focus=focus) if "{focus}" in lead else lead,
        layer_hint,
        owner_hint,
    ]


def intent_test_strategy(topic: str, layer: str) -> list[str]:
    if layer == "core":
        return [
            "Red: add or update xUnit coverage for the primary deterministic behavior.",
            "Green: implement the minimal pure-core logic required by the assertions.",
            "Refactor: preserve passing tests and rerun the Chapter 3 coverage audit.",
        ]
    if layer == "adapter":
        return [
            "Red: add or update Godot-side or adapter-facing coverage for the player-visible behavior.",
            "Green: wire the minimal scene, adapter, or UI behavior required by the assertions.",
            "Refactor: preserve deterministic core boundaries and rerun the Chapter 3 coverage audit.",
        ]
    if layer == "ci":
        return [
            "Red: add or update a deterministic validator or evidence fixture that fails on the missing behavior.",
            "Green: implement the smallest validation, script, or evidence path required to pass.",
            "Refactor: keep output stable and rerun the Chapter 3 baseline validators.",
        ]
    return [
        "Red: add or update a document or metadata validation check for this planning slice.",
        "Green: update the governed document or index with traceable references.",
        "Refactor: keep Chapter 4/5-derived fields out of Chapter 3 generation.",
    ]


def chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    if size <= 0:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]


def is_structured_requirement_group(anchors: list[dict[str, Any]]) -> bool:
    for anchor in anchors:
        text = str(anchor.get("text", ""))
        if "|" in text and text.count("|") >= 3:
            return True
        if re.search(r"\b(T|TASK|GM|SG|NG)[-_ ]?\d{1,5}\b", text, re.IGNORECASE):
            return True
    return False


def chunk_size_for_group(
    layer: str,
    topic: str,
    anchors: list[dict[str, Any]],
    max_anchors_per_intent: int,
    split_profile: str,
) -> int:
    if split_profile == "compact":
        return max_anchors_per_intent
    if split_profile == "expanded":
        size = 4 if layer in {"ci", "docs"} else 3
    else:
        size = 6 if layer in {"ci", "docs"} or topic in {"validation-gates", "testing", "architecture-docs"} else 4
    if is_structured_requirement_group(anchors):
        size = min(size, 4)
    return max(1, min(max_anchors_per_intent, size))


def build_intents(
    index: dict[str, Any],
    mode: str,
    id_prefix: str,
    max_anchors_per_intent: int,
    split_profile: str = "balanced",
) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for anchor in index.get("anchors", []):
        topic, layer, owner = choose_topic(anchor)
        key = (str(anchor.get("kind", "requirement")), layer, owner, topic, source_stem(anchor))
        grouped[key].append(anchor)

    intents: list[dict[str, Any]] = []
    next_index = 1
    previous_by_owner_layer: dict[tuple[str, str], str] = {}
    for (kind, layer, owner, topic, stem), anchors in sorted(grouped.items(), key=lambda item: item[0]):
        anchors = sorted(anchors, key=lambda a: (str(a.get("source_path", "")), int(a.get("line", 0))))
        chunk_size = chunk_size_for_group(layer, topic, anchors, max_anchors_per_intent, split_profile)
        for split_index, group in enumerate(chunked(anchors, chunk_size), 1):
            requirement_ids = [str(a.get("requirement_id")) for a in group]
            source_refs = [f"{a.get('source_path')}:{a.get('line')}" for a in group]
            refs = sorted({ref for a in group for ref in a.get("refs", []) if isinstance(ref, str)})
            phrase = title_phrase(group, topic)
            title_split_index = split_index if len(anchors) > chunk_size else 0
            current_id = f"{id_prefix}-{next_index:04d}"
            dependency_key = (owner, layer)
            depends_on = [previous_by_owner_layer[dependency_key]] if dependency_key in previous_by_owner_layer else []
            intents.append(
                {
                    "id": current_id,
                    "intent_key": f"{kind}:{layer}:{owner}:{topic}:{stem}:{split_index}",
                    "topic": topic,
                    "title": intent_title(topic, phrase, title_split_index),
                    "description": " ".join(str(group[0].get("text", "")).split())[:700],
                    "details": intent_details(topic, layer, owner, phrase),
                    "status": "pending",
                    "priority": priority_of(group),
                    "layer": layer,
                    "owner": owner,
                    "depends_on": depends_on,
                    "adr_refs": [r for r in refs if r.startswith("ADR-")],
                    "chapter_refs": [],
                    "overlay_refs": [r for r in refs if r.startswith("docs/architecture/overlays/")],
                    "labels": sorted({kind, layer, owner, mode, "generated", "intent", topic}),
                    "test_refs": [
                        r
                        for r in refs
                        if r.startswith("Game.") or r.startswith("Tests.") or r.endswith(".cs") or r.endswith(".gd")
                    ],
                    "acceptance": [
                        f"Requirement {rid} is implemented with traceable evidence. Source: {src}"
                        for rid, src in zip(requirement_ids[:8], source_refs[:8])
                    ],
                    "test_strategy": intent_test_strategy(topic, layer),
                    "source_refs": source_refs,
                    "requirement_ids": requirement_ids,
                    "covered_anchor_count": len(group),
                    "generation_mode": mode,
                }
            )
            previous_by_owner_layer[dependency_key] = current_id
            next_index += 1

    disambiguate_duplicate_titles(intents)

    return {
        "schema": "task-generation.task-intents.v1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": mode,
        "intent_count": len(intents),
        "max_anchors_per_intent": max_anchors_per_intent,
        "split_profile": split_profile,
        "source_anchor_count": len(index.get("anchors", [])),
        "intents": intents,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize requirement anchors into implementation task intents.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--requirements", default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--mode", choices=["init", "add"], default="init")
    parser.add_argument("--id-prefix", default="INT")
    parser.add_argument("--max-anchors-per-intent", type=int, default=8)
    parser.add_argument("--split-profile", choices=["compact", "balanced", "expanded"], default="balanced")
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    result = build_intents(
        load_json(root / args.requirements),
        args.mode,
        args.id_prefix,
        args.max_anchors_per_intent,
        args.split_profile,
    )
    out = root / args.out
    write_json(out, result)
    print(f"task_intents={out} intents={result['intent_count']} anchors={result['source_anchor_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
