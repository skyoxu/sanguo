#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from _chapter7_profile import bucket_names, bucket_profile, feature_bucket, load_chapter7_profile
from collect_ui_wiring_inputs import OVERLAY_ROOT, TASKS_BACK, TASKS_GAMEPLAY, TASKS_JSON, UI_GDD_FLOW, build_summary


def _today() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def _title_case_slug(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return "Project"
    return "".join(part[:1].upper() + part[1:] for part in cleaned.replace("_", "-").split("-") if part)


def _repo_display_name(repo_root: Path) -> str:
    readme = repo_root / "README.md"
    if readme.exists():
        for line in readme.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = re.match(r"^#\s+([^\s(]+)", line.strip())
            if match:
                return _title_case_slug(match.group(1))
    sln_names = sorted(path.stem for path in repo_root.glob("*.sln") if path.stem.lower() not in {"game", "godotgame"})
    if sln_names:
        return sln_names[0]
    return _title_case_slug(repo_root.name)


def _repo_gdd_slug(repo_root: Path) -> str:
    display = _repo_display_name(repo_root)
    slug = "".join(ch if ch.isalnum() else "-" for ch in display).strip("-")
    return slug.upper() or "PROJECT"


def _bucket_title(profile: dict[str, Any], bucket: str) -> str:
    return str(bucket_profile(profile, bucket).get("slice_title") or bucket)


def _bucket_audience(profile: dict[str, Any], bucket: str) -> str:
    return str(bucket_profile(profile, bucket).get("audience") or "player-facing")


def _bucket_surface(profile: dict[str, Any], bucket: str) -> str:
    return str(bucket_profile(profile, bucket).get("ui_entry") or "UI surface")


def _bucket_action(profile: dict[str, Any], bucket: str) -> str:
    return str(bucket_profile(profile, bucket).get("player_action") or "Interact with the governed surface")


def _bucket_response(profile: dict[str, Any], bucket: str) -> str:
    return str(bucket_profile(profile, bucket).get("system_response") or "Show governed runtime state")


def _merge_top_refs(summary: dict[str, Any], *, limit: int = 8) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for item in summary["needed_wiring_features"]:
        for ref in item.get("test_refs") or []:
            value = str(ref).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            merged.append(value)
            if len(merged) >= limit:
                return merged
    return merged


def _sort_requirement_ids(values: list[str]) -> list[str]:
    priority = {
        "RQ-I18N-LANG-SWITCH": 10,
        "RQ-AUDIO-CHANNEL-SETTINGS": 20,
        "RQ-PERF-GATE": 30,
        "RQ-SAVE-MIGRATION-CLOUD": 40,
        "RQ-CAMERA-SCROLL": 10,
        "RQ-RUNTIME-SPEED-MODES": 20,
        "RQ-RUNTIME-ERROR-FEEDBACK": 30,
        "RQ-RUNTIME-INTERACTION": 40,
        "RQ-CONFIG-CONTRACT-GOV": 10,
        "RQ-CORE-LOOP-STATE": 90,
        "RQ-ECONOMY-BUILD-RULES": 90,
        "RQ-COMBAT-QUEUE-TECH": 90,
    }
    return sorted(values, key=lambda item: (priority.get(item, 50), item))


def _suggested_surfaces(profile: dict[str, Any], bucket: str) -> str:
    values = list(bucket_profile(profile, bucket).get("suggested_surfaces") or [])
    return ", ".join(f"`{value}`" for value in values)


def _overlay_acceptance_lines(summary: dict[str, Any], *, profile: dict[str, Any]) -> list[str]:
    bucket_order = bucket_names(profile)
    grouped: dict[str, dict[str, Any]] = {}
    for item in summary["needed_wiring_features"]:
        bucket = feature_bucket(profile, item)
        data = grouped.setdefault(
            bucket,
            {
                "requirement_ids": [],
                "expected_logs": [],
                "minimum_fields": [],
                "acceptance_notes": [],
            },
        )
        for field, key in [
            ("overlay_requirement_ids", "requirement_ids"),
            ("overlay_expected_logs", "expected_logs"),
            ("overlay_minimum_fields", "minimum_fields"),
            ("overlay_acceptance_notes", "acceptance_notes"),
        ]:
            for value in item.get(field) or []:
                if value not in data[key]:
                    data[key].append(value)

    lines: list[str] = []
    for bucket in bucket_order:
        data = grouped.get(bucket)
        if not data:
            continue
        requirement_ids = data["requirement_ids"]
        expected_logs = data["expected_logs"]
        minimum_fields = data["minimum_fields"]
        acceptance_notes = data["acceptance_notes"]
        if not requirement_ids and not expected_logs and not minimum_fields and not acceptance_notes:
            continue
        lines.append(f"### {_screen_group_title(profile, bucket)}")
        if requirement_ids:
            lines.append(f"- Requirement IDs: {', '.join(f'`{value}`' for value in _sort_requirement_ids(requirement_ids))}.")
        if expected_logs:
            lines.append(f"- Expected artifacts: {', '.join(f'`{value}`' for value in expected_logs[:4])}.")
        if minimum_fields:
            lines.append(f"- Evidence fields: {', '.join(minimum_fields[:8])}.")
        if acceptance_notes:
            lines.append(f"- Overlay acceptance notes: {acceptance_notes[0]}")
        lines.append("")
    return lines


def _screen_group_title(profile: dict[str, Any], bucket: str) -> str:
    return str(bucket_profile(profile, bucket).get("screen_group") or bucket)


def _merge_adrs(summary: dict[str, Any], *, repo_root: Path) -> list[str]:
    try:
        import json

        payload = json.loads((repo_root / TASKS_JSON).read_text(encoding="utf-8"))
    except Exception:
        return []
    tasks = payload.get("master", {}).get("tasks", []) if isinstance(payload, dict) else []
    seen: set[str] = set()
    out: list[str] = []
    needed_ids = {int(item["task_id"]) for item in summary["needed_wiring_features"]}
    for task in tasks:
        if int(task.get("id", -1)) not in needed_ids:
            continue
        for adr in task.get("adrRefs") or []:
            value = str(adr).strip()
            if value and value not in seen:
                seen.add(value)
                out.append(value)
    return out


def _extract_semantics(items: list[dict[str, Any]], *, bucket: str, profile: dict[str, Any]) -> dict[str, str]:
    failure_texts: list[str] = []
    empty_texts: list[str] = []
    completion_texts: list[str] = []
    for item in items:
        for acc in item.get("acceptance") or []:
            text = str(acc).strip()
            low = text.lower()
            if any(key in low for key in ["must not", "fail", "fails", "failure", "invalid", "fallback", "warning", "block", "denied", "retry"]):
                failure_texts.append(text)
            if any(key in low for key in ["if no", "before", "no active", "missing", "without", "empty state", "outside that window"]):
                empty_texts.append(text)
            if any(key in low for key in ["complete only when", "passes only if", "must", "visible", "show", "display", "enters", "render", "publishes"]):
                completion_texts.append(text)

    def pick(texts: list[str], default: str) -> str:
        for text in texts:
            candidate = text.split("Refs:")[0].strip()
            if candidate:
                return candidate
        return default

    defaults = dict(bucket_profile(profile, bucket).get("semantics_defaults") or {})

    return {
        "failure": pick(failure_texts, str(defaults.get("failure") or "")),
        "empty": pick(empty_texts, str(defaults.get("empty") or "")),
        "completion": pick(completion_texts, str(defaults.get("completion") or "")),
    }


def _build_candidate_specs(summary: dict[str, Any], *, profile: dict[str, Any]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in bucket_names(profile)}
    for feature in summary["needed_wiring_features"]:
        buckets[feature_bucket(profile, feature)].append(feature)

    candidates: list[dict[str, Any]] = []
    for bucket, items in buckets.items():
        if not items:
            continue
        title = _bucket_title(profile, bucket)
        semantics = _extract_semantics(items, bucket=bucket, profile=profile)
        scope_task_ids = sorted(int(item["task_id"]) for item in items)
        task_refs = ", ".join(f"T{task_id:02d}" for task_id in scope_task_ids)
        refs: list[str] = []
        seen_refs: set[str] = set()
        for item in items:
            for ref in item.get("test_refs") or []:
                value = str(ref).strip()
                if value and value not in seen_refs:
                    seen_refs.add(value)
                    refs.append(value)
        requirement_ids = _sort_requirement_ids(
            [
                value
                for item in items
                for value in (item.get("overlay_requirement_ids") or [])
            ]
        )
        expected_logs: list[str] = []
        for item in items:
            for value in item.get("overlay_expected_logs") or []:
                if value not in expected_logs:
                    expected_logs.append(value)
        candidates.append(
            {
                "bucket": bucket,
                "screen_group": _screen_group_title(profile, bucket),
                "matrix_link": f"## 5. UI Wiring Matrix row {title} ({task_refs})",
                "scope_task_ids": scope_task_ids,
                "scope_task_refs": task_refs,
                "ui_entry": _bucket_surface(profile, bucket),
                "candidate_type": "task-shaped UI wiring spec",
                "player_action": _bucket_action(profile, bucket),
                "system_response": _bucket_response(profile, bucket),
                "empty_state": semantics["empty"],
                "failure_state": semantics["failure"],
                "completion_result": semantics["completion"],
                "requirement_ids": requirement_ids,
                "validation_artifact_targets": expected_logs[:4],
                "suggested_standalone_surfaces": [part.strip().strip("`") for part in _suggested_surfaces(profile, bucket).split(",") if part.strip()],
                "test_refs": refs[:4],
            }
        )
    return candidates


def _slice_lines(summary: dict[str, Any], *, profile: dict[str, Any]) -> tuple[list[str], list[str], list[str], list[str], list[str], list[str]]:
    buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in bucket_names(profile)}
    for feature in summary["needed_wiring_features"]:
        buckets[feature_bucket(profile, feature)].append(feature)

    candidate_specs = _build_candidate_specs(summary, profile=profile)
    candidate_specs_by_bucket = {item["bucket"]: item for item in candidate_specs}

    inventory: list[str] = []
    flow: list[str] = []
    matrix: list[str] = []
    unwired: list[str] = []
    candidates: list[str] = []
    requirements: list[str] = []

    for bucket, items in buckets.items():
        if not items:
            continue
        title = _bucket_title(profile, bucket)
        audience = _bucket_audience(profile, bucket)
        task_refs = ", ".join(f"T{int(item['task_id']):02d}" for item in items)
        semantics = _extract_semantics(items, bucket=bucket, profile=profile)
        inventory.append(
            f"| {title} | {audience} | {task_refs} | "
            f"{_bucket_response(profile, bucket)} | {_bucket_surface(profile, bucket)} |"
        )
        flow.append(f"### {title}\n")
        for item in items:
            flow.append(f"- T{int(item['task_id']):02d} `{item['task_title']}`")
        refs: list[str] = []
        seen_refs: set[str] = set()
        for item in items:
            for ref in item.get("test_refs") or []:
                value = str(ref).strip()
                if value and value not in seen_refs:
                    seen_refs.add(value)
                    refs.append(value)
        refs_text = ", ".join(f"`{ref}`" for ref in refs[:4]) if refs else "`Add task-scoped validation refs.`"
        requirement_ids = _sort_requirement_ids(
            [
                value
                for item in items
                for value in (item.get("overlay_requirement_ids") or [])
            ]
        )
        expected_logs = []
        for item in items:
            for value in item.get("overlay_expected_logs") or []:
                if value not in expected_logs:
                    expected_logs.append(value)
        matrix.append(
            f"| {title} ({task_refs}) | {_bucket_surface(profile, bucket)} | {_bucket_action(profile, bucket)} | "
            f"{_bucket_response(profile, bucket)} | {refs_text} |"
        )
        unwired.append(
            f"- {title}: define concrete scene ownership, empty/failure states, and validation evidence for {task_refs}."
        )
        requirements.extend(
            [
                f"### {title}",
                f"- Audience: {audience}.",
                f"- Empty state: {semantics['empty']}",
                f"- Failure state: {semantics['failure']}",
                f"- Completion result: {semantics['completion']}",
                "",
            ]
        )
        candidate_spec = candidate_specs_by_bucket[bucket]
        requirement_ids = candidate_spec["requirement_ids"]
        expected_logs = candidate_spec["validation_artifact_targets"]
        test_refs = candidate_spec["test_refs"]
        candidates.append(
            "\n".join(
                [
                    f"### Candidate Slice {candidate_spec['screen_group']}",
                    "",
                    f"- Matrix link: `{candidate_spec['matrix_link']}`.",
                    f"- Scope: {candidate_spec['scope_task_refs']}.",
                    f"- UI entry: {candidate_spec['ui_entry']}.",
                    f"- Candidate type: {candidate_spec['candidate_type']}.",
                    f"- Screen group: {candidate_spec['screen_group']}.",
                    f"- Player action: {candidate_spec['player_action']}.",
                    f"- System response: {candidate_spec['system_response']}.",
                    f"- Empty state: {candidate_spec['empty_state']}",
                    f"- Failure state: {candidate_spec['failure_state']}",
                    f"- Completion result: {candidate_spec['completion_result']}",
                    f"- Requirement IDs: {', '.join(f'`{value}`' for value in requirement_ids)}." if requirement_ids else "- Requirement IDs: `Add requirement mapping before implementation.`",
                    f"- Validation artifact targets: {', '.join(f'`{value}`' for value in expected_logs[:4])}." if expected_logs else "- Validation artifact targets: `Add artifact target before implementation.`",
                    f"- Suggested standalone surfaces: {', '.join(f'`{value}`' for value in candidate_spec['suggested_standalone_surfaces'])}.",
                    f"- Test refs: {', '.join(f'`{value}`' for value in test_refs)}." if test_refs else "- Test refs: `Add task-scoped validation refs.`",
                ]
            )
        )
    return inventory, flow, matrix, unwired, candidates, requirements


def _screen_contract_lines(*, profile: dict[str, Any]) -> list[str]:
    lines: list[str] = ["## 7. Screen-Level Contracts", ""]
    for index, bucket in enumerate(bucket_names(profile), start=1):
        config = bucket_profile(profile, bucket)
        contract = dict(config.get("screen_contract") or {})
        heading = f"7.{index} {_screen_group_title(profile, bucket)}"
        covered = _bucket_title(profile, bucket)
        must_show = str(contract.get("must_show") or "")
        must_not_hide = str(contract.get("must_not_hide") or "")
        validation = str(contract.get("validation_focus") or "")
        lines.extend(
            [
                f"### {heading}",
                f"- Covered slice: {covered}.",
                f"- Must show: {must_show}",
                f"- Must not hide: {must_not_hide}",
                f"- Validation focus: {validation}",
                "",
            ]
        )
    return lines


def _screen_state_matrix_lines(*, profile: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        "## 8. Screen State Matrix",
        "",
        "| Screen Group | Entry State | Interaction State | Failure State | Recovery / Exit |",
        "| --- | --- | --- | --- | --- |",
    ]
    for bucket in bucket_names(profile):
        config = bucket_profile(profile, bucket)
        state = dict(config.get("screen_state") or {})
        group = _screen_group_title(profile, bucket)
        entry = str(state.get("entry_state") or "")
        interaction = str(state.get("interaction_state") or "")
        failure = str(state.get("failure_state") or "")
        recovery = str(state.get("recovery_exit") or "")
        lines.append(f"| {group} | {entry} | {interaction} | {failure} | {recovery} |")
    lines.append("")
    return lines


def render_ui_gdd_flow(*, repo_root: Path, summary: dict[str, Any], profile: dict[str, Any]) -> str:
    inventory, flow, matrix, unwired, candidates, requirements = _slice_lines(summary, profile=profile)
    adr_refs = _merge_adrs(summary, repo_root=repo_root)
    top_test_refs = _merge_top_refs(summary)
    today = _today()
    screen_contracts = _screen_contract_lines(profile=profile)
    screen_state_matrix = _screen_state_matrix_lines(profile=profile)
    overlay_acceptance = _overlay_acceptance_lines(summary, profile=profile)
    repo_display = _repo_display_name(repo_root)
    title = f"{repo_display} Chapter 7 UI Wiring Board"

    header = [
        "---",
        f"GDD-ID: GDD-{_repo_gdd_slug(repo_root)}-UI-WIRING-V1",
        f"Title: {title}",
        "Status: Draft",
        "Owner: codex",
        f"Last Updated: {today}",
        "Encoding: UTF-8",
        "Applies-To:",
        "  - .taskmaster/tasks/tasks.json",
        "  - docs/gdd/ui-gdd-flow.md",
        "ADR-Refs:",
    ]
    if adr_refs:
        header.extend([f"  - {item}" for item in adr_refs[:12]])
    else:
        header.append("  - n/a")
    header.append("Test-Refs:")
    if top_test_refs:
        header.extend([f"  - {item}" for item in top_test_refs])
    else:
        header.append("  - n/a")
    header.append("---")

    lines = (
        header
        + [
            "",
            f"# {title}",
            "",
            "## 1. Design Goals",
            "",
            "### 1.1 Experience Pillars",
            "- Stable entry: startup, continue, and runtime entry must be explicit and recoverable.",
            "- Readable loop: phase, pressure, resources, HP, prompts, and outcomes must be understandable from the UI alone.",
            "- Explainable systems: config, governance, save, migration, and audit state must have visible ownership instead of hiding in logs.",
            "- Deterministic recovery: failure, invalid action, persistence, and fallback states must be reproducible and visible.",
            "",
            "### 1.2 Target Use",
            "- Provide one governed planning surface for all currently completed task capabilities.",
            "- Keep Chapter 7 focused on player-facing or operator-facing surface ownership before polish-only work.",
            "",
            "## 2. Core Player Loop",
            "",
            "1. Launch or continue from a stable entry surface.",
            "2. Enter the runtime loop with readable phase, timing, pressure, and survival state.",
            "3. Interact with combat, economy, progression, and meta systems through governed surfaces.",
            "4. Resolve win, loss, save/load, config-governance, and migration outcomes with visible feedback.",
            "",
            "## 3. Completed Capability Inventory",
            "",
            "| Capability Slice | Audience | Task IDs | Player-Facing Meaning | Primary UI Need |",
            "| --- | --- | --- | --- | --- |",
            *inventory,
            "",
            "## 4. Flow Recomposition",
            "",
            *flow,
            "",
            "## 5. UI Wiring Matrix",
            "",
            "| Feature | UI Surface | Player Action | System Response | Test Refs |",
            "| --- | --- | --- | --- | --- |",
            *matrix,
            "",
            "## 6. Screen And Surface Requirements",
            "",
            *requirements,
            "- Operator-facing read surfaces are allowed when player-facing interaction is not appropriate.",
            "",
            *screen_contracts,
            *screen_state_matrix,
            "## 9. Scope And Non-Goals",
            "",
            "- Chapter 7 covers UI or governed visible-surface ownership for every completed task in `.taskmaster/tasks/tasks.json`.",
            "- It does not require final production polish, animation, skinning, or marketing-grade copy.",
            "",
            "### 9.1 In Scope",
            "",
            "- Surface ownership for startup, loop, combat, economy, meta, and governance capabilities.",
            "- Empty state, failure state, and completion state for each major slice.",
            "- Task alignment and validation references back to completed backlog items.",
            "",
            "### 9.2 Non-Goals",
            "- Final UX polish, visual theming, animation tuning, and cosmetic-only layout work.",
            "- Replacing source-of-truth task status outside `.taskmaster/tasks/tasks.json`.",
            "",
            "## 10. Unwired UI Feature List",
            "",
            *unwired,
            "",
            "## 11. Next UI Wiring Task Candidates",
            "",
            *candidates,
            "",
            "## 12. Copy And Accessibility",
            "",
            "- Visible text should remain explicit and actionable.",
            "- Failure messages must tell the player or operator what happened and what to do next.",
            "- Do not rely on color only to convey terminal, invalid, or route-selection state.",
            "",
            "## 13. Test And Acceptance",
            "",
            "- Chapter 7 validation must keep `## 5. UI Wiring Matrix`, `## 10. Unwired UI Feature List`, and `## 11. Next UI Wiring Task Candidates` intact.",
            "- Evidence should resolve back to xUnit, GdUnit, smoke, or CI outputs already referenced by task views.",
            "- Any new UI slice should add or name a concrete validation path before implementation.",
            "",
            *overlay_acceptance,
            "",
            "## 14. Task Alignment",
            "",
            f"- Completed task count currently expected by Chapter 7: {summary['completed_master_tasks_count']}.",
            "- Chapter 7 uses `.taskmaster/tasks/tasks.json` as the completion-state SSoT.",
            "- View files remain enrichment sources for test refs, acceptance, labels, and contract context.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def export_candidate_sidecar(*, repo_root: Path, summary: dict[str, Any], ui_gdd_flow_path: Path = UI_GDD_FLOW, profile: dict[str, Any] | None = None) -> Path:
    effective_profile = profile or load_chapter7_profile(repo_root=repo_root)
    out = ui_gdd_flow_path.with_suffix(".candidates.json") if ui_gdd_flow_path.is_absolute() else (repo_root / ui_gdd_flow_path).with_suffix(".candidates.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": _today(),
        "source_gdd": str(ui_gdd_flow_path).replace("\\", "/"),
        "completed_master_tasks_count": summary["completed_master_tasks_count"],
        "needed_wiring_features_count": summary["needed_wiring_features_count"],
        "candidates": _build_candidate_specs(summary, profile=effective_profile),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out


def write_ui_gdd_flow(
    *,
    repo_root: Path,
    summary: dict[str, Any],
    ui_gdd_flow_path: Path = UI_GDD_FLOW,
    tasks_json_path: Path | None = None,
    tasks_back_path: Path | None = None,
    tasks_gameplay_path: Path | None = None,
    overlay_root_path: Path | None = None,
    chapter7_profile_path: Path | None = None,
) -> Path:
    profile = load_chapter7_profile(repo_root=repo_root, profile_path=chapter7_profile_path)
    out = ui_gdd_flow_path if ui_gdd_flow_path.is_absolute() else (repo_root / ui_gdd_flow_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_ui_gdd_flow(repo_root=repo_root, summary=summary, profile=profile), encoding="utf-8", newline="\n")
    export_candidate_sidecar(repo_root=repo_root, summary=summary, ui_gdd_flow_path=ui_gdd_flow_path, profile=profile)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the governed Chapter 7 UI wiring GDD artifact.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ui-gdd-flow-path", default=str(UI_GDD_FLOW))
    parser.add_argument("--tasks-json-path", default=str(TASKS_JSON))
    parser.add_argument("--tasks-back-path", default=str(TASKS_BACK))
    parser.add_argument("--tasks-gameplay-path", default=str(TASKS_GAMEPLAY))
    parser.add_argument("--overlay-root-path", default=str(OVERLAY_ROOT))
    parser.add_argument("--chapter7-profile-path", default="")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    summary = build_summary(
        repo_root=repo_root,
        tasks_json_path=Path(args.tasks_json_path),
        tasks_back_path=Path(args.tasks_back_path),
        tasks_gameplay_path=Path(args.tasks_gameplay_path),
        overlay_root_path=Path(args.overlay_root_path),
    )
    out = write_ui_gdd_flow(
        repo_root=repo_root,
        summary=summary,
        ui_gdd_flow_path=Path(args.ui_gdd_flow_path),
        chapter7_profile_path=Path(args.chapter7_profile_path) if args.chapter7_profile_path else None,
    )
    print(f"CHAPTER7_UI_GDD_WRITER status=ok tasks={summary['completed_master_tasks_count']} out={str(out).replace('\\', '/')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
