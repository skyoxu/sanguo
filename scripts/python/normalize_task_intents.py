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


SEMANTIC_LAYER = {
    "functional": "core",
    "non_functional": "ci",
    "invariant": "core",
    "failure": "core",
    "scope": "core",
    "metric": "ci",
    "constraint": "ci",
    "risk": "docs",
}
SEMANTIC_OWNER = {
    "functional": "gameplay",
    "non_functional": "architecture",
    "invariant": "gameplay",
    "failure": "gameplay",
    "scope": "gameplay",
    "metric": "architecture",
    "constraint": "architecture",
    "risk": "architecture",
}


def semantic_to_anchors(
    semantics: dict[str, Any],
    source_blocks: dict[str, Any],
    capabilities: dict[str, Any],
) -> list[dict[str, Any]]:
    blocks = {
        str(row.get("block_id")): row
        for row in source_blocks.get("blocks", [])
        if isinstance(row, dict) and row.get("block_id")
    }
    cap_by_req: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for capability in capabilities.get("capabilities", []):
        if not isinstance(capability, dict):
            continue
        for rid in capability.get("requirement_ids", []):
            cap_by_req[str(rid)].append(capability)
    anchors: list[dict[str, Any]] = []
    for requirement in semantics.get("requirements", []):
        if not isinstance(requirement, dict):
            continue
        if str(requirement.get("status", "active")).casefold() != "active":
            continue
        if requirement.get("delivery_relevant") is not True:
            continue
        non_task_sinks = [
            row for row in requirement.get("non_task_sinks", [])
            if isinstance(row, dict) and row.get("type") and row.get("id")
        ]
        policy = str(requirement.get("sink_policy") or "task_or_global_constraint").casefold()
        if non_task_sinks and policy not in {"task", "task_required"}:
            continue
        if policy in {"global_constraint", "quality_gate", "adr_owned", "deferred", "exclusion"}:
            continue
        rid = str(requirement.get("requirement_id"))
        refs = [str(value) for value in requirement.get("source_block_ids", [])]
        first = blocks.get(refs[0]) if refs else None
        source_path = str((first or {}).get("source_path") or "docs/gdd/unknown.md")
        line = int((first or {}).get("line_start") or 1)
        caps = cap_by_req.get(rid, [])
        primary_cap = caps[0] if caps else None
        kind = str(requirement.get("kind") or "functional")
        anchors.append({
            "requirement_id": rid,
            "source_path": source_path,
            "line": line,
            "kind": kind,
            "priority": str(requirement.get("priority") or "P2").upper(),
            "text": str(requirement.get("statement") or ""),
            "refs": [],
            "source_block_ids": refs,
            "heading_path": [
                str(value) for value in (first or {}).get("heading_path", [])
                if str(value).strip()
            ],
            "capability_id": str((primary_cap or {}).get("capability_id") or ""),
            "capability_title": str((primary_cap or {}).get("title") or ""),
            "capability_ids": sorted({
                str(row.get("capability_id"))
                for row in caps
                if str(row.get("capability_id") or "").strip()
            }),
            "capability_titles": sorted({
                str(row.get("title"))
                for row in caps
                if str(row.get("title") or "").strip()
            }),
            "layer_hint": str(requirement.get("layer_hint") or SEMANTIC_LAYER.get(kind, "core")),
            "owner_hint": str(requirement.get("owner_hint") or SEMANTIC_OWNER.get(kind, "gameplay")),
            "semantic": True,
        })
    return anchors


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


CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def anchor_capability_ids(anchor: dict[str, Any]) -> list[str]:
    values = anchor.get("capability_ids")
    if isinstance(values, list):
        result = sorted({
            str(value).strip() for value in values if str(value).strip()
        })
        if result:
            return result
    legacy = str(anchor.get("capability_id") or "").strip()
    return [legacy] if legacy else []


def semantic_grouping_stem(anchor: dict[str, Any]) -> str:
    primary_capability = str(anchor.get("capability_id") or "").strip()
    if primary_capability:
        # Preserve the pre-shadow primary Capability partition exactly.
        return primary_capability
    capability_ids = anchor_capability_ids(anchor)
    if capability_ids:
        return capability_ids[0]
    heading_path = [
        str(value).strip()
        for value in anchor.get("heading_path", [])
        if str(value).strip()
    ]
    if heading_path:
        return f"{source_stem(anchor)}::{' > '.join(heading_path).casefold()}"
    return source_stem(anchor)


def compact_cjk_focus(text: str, limit: int = 28) -> str:
    value = re.sub(r"^[\s#>*+\-\d.)、]+", "", str(text or "")).strip()
    value = re.sub(r"\s+", " ", value)
    if not value:
        return ""
    first_clause = re.split(r"[。！？；;!?\n]", value, maxsplit=1)[0].strip()
    candidate = first_clause or value
    return candidate if len(candidate) <= limit else candidate[:limit].rstrip() + "…"


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
    if anchor.get("semantic"):
        capability_id = str(anchor.get("capability_id") or "").strip()
        topic = capability_id.lower() if capability_id else str(anchor.get("kind") or "requirement").lower()
        return (
            topic,
            str(anchor.get("layer_hint") or "core"),
            str(anchor.get("owner_hint") or "gameplay"),
        )
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
    headings = [
        str(anchor.get("heading_path", [])[-1]).strip()
        for anchor in anchors
        if isinstance(anchor.get("heading_path"), list)
        and anchor.get("heading_path")
        and str(anchor.get("heading_path", [])[-1]).strip()
    ]
    if headings:
        heading, _count = Counter(headings).most_common(1)[0]
        return heading

    for anchor in anchors:
        text = str(anchor.get("text", ""))
        if CJK_RE.search(text):
            focus = compact_cjk_focus(text)
            if focus:
                return focus

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
    ascii_key = " ".join(re.findall(r"[A-Za-z]+|\d+", title.lower())[:6])
    if ascii_key:
        return ascii_key
    unicode_parts = re.findall(r"[\w]+", title.casefold(), flags=re.UNICODE)
    return " ".join(unicode_parts[:6])[:80]


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
    if topic not in TOPIC_TEMPLATES and CJK_RE.search(focus):
        if split_index > 0:
            focus = f"第{split_index}部分：{focus}".strip()
        return collapse_repeated_words(f"实现{focus}".strip())
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
        # Compact may reduce packaging churn, but it must never bypass the
        # repository-wide Chapter 3 complexity ceiling.
        return max(1, min(max_anchors_per_intent, 7))
    if split_profile == "expanded":
        size = 4 if layer in {"ci", "docs"} else 3
    else:
        size = 6 if layer in {"ci", "docs"} or topic in {"validation-gates", "testing", "architecture-docs"} else 4
    if is_structured_requirement_group(anchors):
        size = min(size, 4)
    # Complexity governance is structural: never hide an oversized intent by
    # capping its score. Split before task generation so each Task skeleton is <= 7.
    return max(1, min(max_anchors_per_intent, size, 7))


def build_joint_capability_shadow(anchors: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str, tuple[str, ...]], list[dict[str, Any]]] = defaultdict(list)
    for anchor in anchors:
        capability_ids = anchor_capability_ids(anchor)
        if len(capability_ids) < 2:
            continue
        _topic, layer, owner = choose_topic(anchor)
        key = (
            str(anchor.get("kind", "requirement")),
            layer,
            owner,
            tuple(capability_ids),
        )
        grouped[key].append(anchor)

    candidates = []
    for (kind, layer, owner, capability_ids), rows in sorted(grouped.items(), key=lambda item: item[0]):
        requirement_ids = sorted({
            str(row.get("requirement_id"))
            for row in rows
            if str(row.get("requirement_id") or "").strip()
        })
        if len(requirement_ids) < 2:
            continue
        candidates.append({
            "kind": kind,
            "layer": layer,
            "owner": owner,
            "capability_refs": list(capability_ids),
            "requirement_ids": requirement_ids,
            "requirement_count": len(requirement_ids),
            "suggested_action": "consider_joint_slice",
            "advisory_only": True,
        })
    return {
        "mode": "advisory",
        "affects_default_grouping": False,
        "candidate_group_count": len(candidates),
        "candidates": candidates,
    }


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
        grouping_stem = semantic_grouping_stem(anchor)
        key = (str(anchor.get("kind", "requirement")), layer, owner, topic, grouping_stem)
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
            phrase = str(group[0].get("capability_title") or "").strip() or title_phrase(group, topic)
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
                    "dependency_status": "provisional",
                    "dependency_reason": (
                        "generation-order owner/layer skeleton; Chapter 5 must validate semantic dependency"
                        if depends_on else "none"
                    ),
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
                    "semantic_refs": requirement_ids,
                    "capability_refs": sorted({
                        capability_id
                        for anchor in group
                        for capability_id in anchor_capability_ids(anchor)
                    }),
                    "complexity_score": max(1, len(group)),
                    "complexity_split_applied": len(anchors) > len(group),
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
        "joint_capability_shadow": build_joint_capability_shadow(index.get("anchors", [])),
        "intents": intents,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize requirement anchors into implementation task intents.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--requirements", default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--semantics", default="logs/ci/task-generation/semantic-requirements.v1.json")
    parser.add_argument("--source-blocks", default="logs/ci/task-generation/source-blocks.v1.json")
    parser.add_argument("--capabilities", default="logs/ci/task-generation/capabilities.v1.json")
    parser.add_argument("--mode", choices=["init", "add"], default="init")
    parser.add_argument("--id-prefix", default="INT")
    parser.add_argument("--max-anchors-per-intent", type=int, default=8)
    parser.add_argument("--split-profile", choices=["compact", "balanced", "expanded"], default="balanced")
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    semantics_path = root / args.semantics
    if semantics_path.is_file():
        semantics = load_json(semantics_path)
        if semantics.get("schema_version") != "newrouge.semantic-requirements.v1":
            raise SystemExit("semantic requirements schema is invalid")
        index = {
            "schema": "chapter3.validated-semantics.v1",
            "anchors": semantic_to_anchors(
                semantics,
                load_json(root / args.source_blocks),
                load_json(root / args.capabilities) if (root / args.capabilities).is_file() else {"capabilities": []},
            ),
        }
    else:
        index = load_json(root / args.requirements)
    result = build_intents(
        index,
        args.mode,
        args.id_prefix,
        args.max_anchors_per_intent,
        args.split_profile,
    )
    result["source_schema"] = index.get("schema")
    out = root / args.out
    write_json(out, result)
    print(f"task_intents={out} intents={result['intent_count']} anchors={result['source_anchor_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
