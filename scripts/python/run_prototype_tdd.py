#!/usr/bin/env python3
"""Lightweight TDD runner for prototype-lane work."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cmd(args: list[str], *, cwd: Path, timeout_sec: int) -> tuple[int, str]:
    proc = subprocess.Popen(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    try:
        out, _ = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        return 124, out
    return proc.returncode or 0, out


def _sanitize_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-_")
    return cleaned or "prototype"


def _section_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip().lower())
    cleaned = re.sub(r"_{2,}", "_", cleaned).strip("_")
    return cleaned or "section"


def _prototype_record_path(*, root: Path, prototype_dir: str, record_path: str, slug: str) -> Path:
    if str(record_path or "").strip():
        return (root / record_path).resolve()
    return root / prototype_dir / f"{today_str()}-{slug}.md"


def _render_record(
    *,
    slug: str,
    owner: str,
    related_task_ids: list[str],
    hypothesis: str,
    core_player_fantasy: str,
    minimum_playable_loop: str,
    game_feature: str,
    core_gameplay_loop: str,
    win_fail_conditions: str,
    game_type_specific_game_type: str,
    game_type_specific_guide_path: str,
    game_type_specific_sections: list[str],
    scope_in: list[str],
    scope_out: list[str],
    success_criteria: list[str],
    promote_signals: list[str],
    archive_signals: list[str],
    discard_signals: list[str],
    evidence: list[str],
    decision: str,
    next_step: str,
) -> str:
    related = ", ".join(related_task_ids) if related_task_ids else "none yet"
    scope_in_lines = "\n".join(f"  - {item}" for item in (scope_in or ["TBD"]))
    scope_out_lines = "\n".join(f"  - {item}" for item in (scope_out or ["TBD"]))
    criteria_lines = "\n".join(f"- {item}" for item in (success_criteria or ["TBD"]))
    evidence_lines = "\n".join(f"  - {item}" for item in (evidence or ["TBD"]))
    game_type_specific_lines = [
        "## Game Type Specifics",
        f"- Game Type: {game_type_specific_game_type or 'TBD'}",
        f"- Guide Path: {game_type_specific_guide_path or 'TBD'}",
    ]
    for item in game_type_specific_sections or []:
        game_type_specific_lines.append(f"- {item}")
    lines = [
        f"# Prototype: {slug}",
        "",
        "- Status: active",
        f"- Owner: {owner}",
        f"- Date: {today_str()}",
        f"- Related formal task ids: {related}",
        "",
        "## Hypothesis",
        f"- {hypothesis}",
        "",
        "## Core Player Fantasy",
        f"- {core_player_fantasy}",
        "",
        "## Minimum Playable Loop",
        f"- {minimum_playable_loop}",
        "",
        "## Game Feature",
        f"- {game_feature}",
        "",
        "## Core Gameplay Loop",
        f"- {core_gameplay_loop}",
        "",
        "## Win / Fail Conditions",
        f"- {win_fail_conditions}",
        "",
        *game_type_specific_lines,
        "",
        "## Scope",
        "- In:",
        scope_in_lines,
        "- Out:",
        scope_out_lines,
        "",
        "## Success Criteria",
        criteria_lines,
        "",
        "## Promote Signals",
        "\n".join(f"- {item}" for item in (promote_signals or ["TBD"])),
        "",
        "## Archive Signals",
        "\n".join(f"- {item}" for item in (archive_signals or ["TBD"])),
        "",
        "## Discard Signals",
        "\n".join(f"- {item}" for item in (discard_signals or ["TBD"])),
        "",
        "## Evidence",
        "- Code paths:",
        evidence_lines,
        "- Logs / media / notes:",
        "  - TBD",
        "",
        "## Decision",
        f"- {decision}",
        "",
        "## Next Step",
        f"- {next_step}",
        "",
    ]
    return "\n".join(lines)


def _ensure_record(
    *,
    root: Path,
    slug: str,
    prototype_dir: str,
    record_path: str,
    skip_record: bool,
    owner: str,
    related_task_ids: list[str],
    hypothesis: str,
    core_player_fantasy: str,
    minimum_playable_loop: str,
    game_feature: str,
    core_gameplay_loop: str,
    win_fail_conditions: str,
    game_type_specific_game_type: str,
    game_type_specific_guide_path: str,
    game_type_specific_sections: list[str],
    scope_in: list[str],
    scope_out: list[str],
    success_criteria: list[str],
    promote_signals: list[str],
    archive_signals: list[str],
    discard_signals: list[str],
    evidence: list[str],
    decision: str,
    next_step: str,
) -> str:
    if skip_record:
        return ""
    record = _prototype_record_path(root=root, prototype_dir=prototype_dir, record_path=record_path, slug=slug)
    if not record.exists():
        write_text(
            record,
            _render_record(
                slug=slug,
                owner=owner,
                related_task_ids=related_task_ids,
                hypothesis=hypothesis,
                core_player_fantasy=core_player_fantasy,
                minimum_playable_loop=minimum_playable_loop,
                game_feature=game_feature,
                core_gameplay_loop=core_gameplay_loop,
                win_fail_conditions=win_fail_conditions,
                game_type_specific_game_type=game_type_specific_game_type,
                game_type_specific_guide_path=game_type_specific_guide_path,
                game_type_specific_sections=game_type_specific_sections,
                scope_in=scope_in,
                scope_out=scope_out,
                success_criteria=success_criteria,
                promote_signals=promote_signals,
                archive_signals=archive_signals,
                discard_signals=discard_signals,
                evidence=evidence,
                decision=decision,
                next_step=next_step,
            ),
        )
    try:
        return str(record.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(record).replace("\\", "/")


def _normalize_heading(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().strip(":：")).lower()


def _parse_game_type_specifics_from_record(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_section = False
    result: dict[str, object] = {"game_type": "", "guide_path": "", "selected_sections": []}
    sections: list[dict[str, str]] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            in_section = _normalize_heading(stripped[3:]) in {"game type specifics", "游戏类型细节", "游戏类型特定设计"}
            continue
        if not in_section or not stripped.startswith("- "):
            continue
        entry = stripped[2:].strip()
        if ":" not in entry and "：" not in entry:
            continue
        key, value = re.split(r"[:：]", entry, maxsplit=1)
        normalized_key = _normalize_heading(key)
        value = value.strip()
        if normalized_key in {"game type", "游戏类型"}:
            result["game_type"] = _sanitize_slug(value) if value and value.upper() != "TBD" else ""
        elif normalized_key in {"guide path", "game type guide path", "类型模板路径", "游戏类型模板路径"}:
            result["guide_path"] = value if value.upper() != "TBD" else ""
        else:
            sections.append({"id": _section_id(key), "title": key.strip(), "answer": value})
    result["selected_sections"] = sections
    if not result["game_type"] and not result["guide_path"] and not sections:
        return {}
    return result


def _split_question_answer(entry: str) -> tuple[str, str]:
    if "？" in entry:
        question, answer = entry.split("？", 1)
        return question.strip() + "？", answer.strip()
    if "?" in entry:
        question, answer = entry.split("?", 1)
        return question.strip() + "?", answer.strip()
    if ":" in entry or "：" in entry:
        question, answer = re.split(r"[:：]", entry, maxsplit=1)
        return question.strip(), answer.strip()
    return entry.strip(), ""


def _parse_prototype_type_kit_from_record(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    result: dict[str, object] = {"game_type": "", "kit_path": "", "gameplay_flow": [], "prototype_scene_ui": []}
    in_kit = False
    subsection = ""
    gameplay_flow: list[dict[str, str]] = []
    prototype_scene_ui: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            in_kit = _normalize_heading(stripped[3:]) in {"prototype type kit", "原型类型模板", "prototype 类型模板"}
            subsection = ""
            continue
        if not in_kit:
            continue
        if stripped.startswith("### "):
            heading = _normalize_heading(stripped[4:])
            if heading in {"gameplay flow / gdd route", "gameplay flow", "gdd route", "玩法动线", "玩法流程"}:
                subsection = "gameplay_flow"
            elif heading in {"prototype scene ui", "scene ui", "原型场景 ui", "场景 ui"}:
                subsection = "prototype_scene_ui"
            else:
                subsection = ""
            continue
        if not stripped.startswith("- "):
            continue
        entry = stripped[2:].strip()
        if ":" in entry or "：" in entry:
            key, value = re.split(r"[:：]", entry, maxsplit=1)
            normalized_key = _normalize_heading(key)
            if normalized_key in {"game type", "游戏类型"}:
                result["game_type"] = _sanitize_slug(value.strip()) if value.strip().upper() != "TBD" else ""
                continue
            if normalized_key in {"kit path", "prototype type kit path", "模板路径", "原型类型模板路径"}:
                result["kit_path"] = value.strip() if value.strip().upper() != "TBD" else ""
                continue
        question, answer = _split_question_answer(entry)
        item = {"id": _section_id(question), "question": question, "answer": answer}
        if subsection == "gameplay_flow":
            gameplay_flow.append(item)
        elif subsection == "prototype_scene_ui":
            prototype_scene_ui.append(item)
    result["gameplay_flow"] = gameplay_flow
    result["prototype_scene_ui"] = prototype_scene_ui
    if not result["game_type"] and not result["kit_path"] and not gameplay_flow and not prototype_scene_ui:
        return {}
    return result


def _load_prototype_intake(*, root: Path, prototype_record: str) -> dict[str, object]:
    if not prototype_record:
        return {}
    record = Path(prototype_record)
    if not record.is_absolute():
        record = (root / prototype_record).resolve()
    specifics = _parse_game_type_specifics_from_record(record)
    type_kit = _parse_prototype_type_kit_from_record(record)
    intake: dict[str, object] = {}
    if specifics:
        intake["game_type_specifics"] = specifics
    if type_kit:
        intake["prototype_type_kit"] = type_kit
    return intake


def _build_dotnet_steps(*, targets: list[str], configuration: str, filter_expr: str) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    for idx, target in enumerate(targets, start=1):
        cmd = ["dotnet", "test", target, "-c", configuration]
        if filter_expr:
            cmd += ["--filter", filter_expr]
        steps.append(
            {
                "name": f"dotnet-{idx}",
                "kind": "dotnet-test",
                "cmd": cmd,
            }
        )
    return steps


def _build_gdunit_step(*, godot_bin: str, gdunit_paths: list[str], timeout_sec: int, report_dir: str) -> dict[str, object]:
    cmd = [
        "py",
        "-3",
        "scripts/python/run_gdunit.py",
        "--prewarm",
        "--godot-bin",
        godot_bin,
        "--project",
        "Tests.Godot",
    ]
    for path in gdunit_paths:
        cmd += ["--add", path]
    cmd += ["--timeout-sec", str(timeout_sec), "--rd", report_dir]
    return {
        "name": "gdunit",
        "kind": "gdunit",
        "cmd": cmd,
    }


def _expected_outcome(stage: str, expect: str) -> str:
    if expect in {"fail", "pass"}:
        return expect
    return "fail" if stage == "red" else "pass"


def _evaluate_steps(*, expected: str, steps: list[dict[str, object]]) -> tuple[str, str]:
    failed = [step for step in steps if int(step.get("rc", 0)) != 0]
    if expected == "fail":
        if failed:
            return "ok", "Prototype red evidence captured at least one failing verification step."
        return "unexpected_green", "Prototype red stage expected a failing verification step, but all checks passed."
    if failed:
        return "unexpected_red", "Prototype green/refactor stage expected all verification steps to pass."
    return "ok", "Prototype verification steps passed."


def _build_report(*, payload: dict[str, object]) -> str:
    lines = [
        f"# Prototype TDD Summary ({payload.get('slug', '')})",
        "",
        f"- Stage: {payload.get('stage', '')}",
        f"- Expected: {payload.get('expected', '')}",
        f"- Status: {payload.get('status', '')}",
        f"- Message: {payload.get('message', '')}",
        f"- Prototype record: {payload.get('prototype_record', '') or 'skipped'}",
        "",
        "## Verification Steps",
        "",
    ]
    steps = payload.get("steps", [])
    if isinstance(steps, list) and steps:
        for step in steps:
            if not isinstance(step, dict):
                continue
            lines.append(
                f"- {step.get('name', '')}: rc={step.get('rc', '')} kind={step.get('kind', '')} log={step.get('log', '')}"
            )
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Run a lightweight prototype-lane TDD loop without entering the formal task pipeline.")
    ap.add_argument("--slug", required=True, help="Prototype slug used for docs/prototypes and log artifacts.")
    ap.add_argument("--stage", choices=["red", "green", "refactor"], default="red")
    ap.add_argument("--expect", choices=["auto", "fail", "pass"], default="auto")
    ap.add_argument("--prototype-dir", default="docs/prototypes")
    ap.add_argument("--record-path", default="")
    ap.add_argument("--skip-record", action="store_true", help="Do not create or update a prototype record.")
    ap.add_argument("--owner", default="operator")
    ap.add_argument("--related-task-id", action="append", default=[])
    ap.add_argument("--hypothesis", default="TODO: describe the prototype hypothesis.")
    ap.add_argument("--core-player-fantasy", default="TODO: describe what the player should feel or understand in the first minute.")
    ap.add_argument("--minimum-playable-loop", default="TODO: describe the smallest end-to-end loop the player must complete.")
    ap.add_argument("--game-feature", default="TODO: describe the gameplay uniqueness.")
    ap.add_argument("--core-gameplay-loop", default="TODO: describe the repeated gameplay loop.")
    ap.add_argument("--win-fail-conditions", default="TODO: define win and fail conditions.")
    ap.add_argument("--game-type-specific-game-type", default="")
    ap.add_argument("--game-type-specific-guide-path", default="")
    ap.add_argument("--game-type-specific-section", action="append", default=[])
    ap.add_argument("--scope-in", action="append", default=[])
    ap.add_argument("--scope-out", action="append", default=[])
    ap.add_argument("--success-criteria", action="append", default=[])
    ap.add_argument("--promote-signal", action="append", default=[])
    ap.add_argument("--archive-signal", action="append", default=[])
    ap.add_argument("--discard-signal", action="append", default=[])
    ap.add_argument("--evidence", action="append", default=[])
    ap.add_argument("--decision", default="pending")
    ap.add_argument("--next-step", default="Decide discard | archive | promote after the prototype result is clear.")
    ap.add_argument("--create-record-only", action="store_true", help="Create the prototype record and exit without running verification.")
    ap.add_argument("--dotnet-target", action="append", default=[], help="Repeatable dotnet test project or solution target.")
    ap.add_argument("--filter", default="", help="Optional dotnet test filter applied to every --dotnet-target.")
    ap.add_argument("--configuration", default="Debug")
    ap.add_argument("--godot-bin", default="")
    ap.add_argument("--gdunit-path", action="append", default=[], help="Repeatable Tests.Godot relative path for prototype GdUnit checks.")
    ap.add_argument("--timeout-sec", type=int, default=300)
    ap.add_argument("--out-dir", default="")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    slug = _sanitize_slug(args.slug)
    out_dir = Path(args.out_dir) if str(args.out_dir or "").strip() else (root / "logs" / "ci" / today_str() / f"prototype-tdd-{slug}-{args.stage}")
    ensure_dir(out_dir)

    prototype_record = _ensure_record(
        root=root,
        slug=slug,
        prototype_dir=str(args.prototype_dir),
        record_path=str(args.record_path),
        skip_record=bool(args.skip_record),
        owner=str(args.owner),
        related_task_ids=[str(item) for item in args.related_task_id],
        hypothesis=str(args.hypothesis),
        core_player_fantasy=str(args.core_player_fantasy),
        minimum_playable_loop=str(args.minimum_playable_loop),
        game_feature=str(args.game_feature),
        core_gameplay_loop=str(args.core_gameplay_loop),
        win_fail_conditions=str(args.win_fail_conditions),
        game_type_specific_game_type=str(args.game_type_specific_game_type),
        game_type_specific_guide_path=str(args.game_type_specific_guide_path),
        game_type_specific_sections=[str(item) for item in args.game_type_specific_section],
        scope_in=[str(item) for item in args.scope_in],
        scope_out=[str(item) for item in args.scope_out],
        success_criteria=[str(item) for item in args.success_criteria],
        promote_signals=[str(item) for item in args.promote_signal],
        archive_signals=[str(item) for item in args.archive_signal],
        discard_signals=[str(item) for item in args.discard_signal],
        evidence=[str(item) for item in args.evidence],
        decision=str(args.decision),
        next_step=str(args.next_step),
    )

    steps: list[dict[str, object]] = []
    if args.dotnet_target:
        steps.extend(_build_dotnet_steps(targets=[str(item) for item in args.dotnet_target], configuration=str(args.configuration), filter_expr=str(args.filter)))
    if args.gdunit_path:
        if not str(args.godot_bin or "").strip():
            print("PROTOTYPE_TDD ERROR: --godot-bin is required when --gdunit-path is used.", file=sys.stderr)
            return 2
        steps.append(
            _build_gdunit_step(
                godot_bin=str(args.godot_bin),
                gdunit_paths=[str(item) for item in args.gdunit_path],
                timeout_sec=int(args.timeout_sec),
                report_dir=str((out_dir / "gdunit-report").as_posix()),
            )
        )

    if not steps and not args.create_record_only:
        print("PROTOTYPE_TDD ERROR: provide at least one --dotnet-target or --gdunit-path, or use --create-record-only.", file=sys.stderr)
        return 2

    if not args.create_record_only:
        for index, step in enumerate(steps, start=1):
            log_path = out_dir / f"step-{index:02d}-{step['name']}.log"
            rc, out = run_cmd([str(item) for item in step["cmd"]], cwd=root, timeout_sec=int(args.timeout_sec))
            write_text(log_path, out)
            step["rc"] = rc
            step["log"] = str(log_path.relative_to(root)).replace("\\", "/")

    expected = _expected_outcome(stage=str(args.stage), expect=str(args.expect))
    if args.create_record_only:
        status = "ok"
        message = "Prototype record scaffold created; no verification steps were requested."
    else:
        status, message = _evaluate_steps(expected=expected, steps=steps)

    payload: dict[str, object] = {
        "cmd": "prototype-tdd",
        "slug": slug,
        "stage": str(args.stage),
        "expected": expected,
        "status": status,
        "message": message,
        "prototype_record": prototype_record,
        "steps": steps,
        "create_record_only": bool(args.create_record_only),
    }
    payload["prototype_intake"] = _load_prototype_intake(root=root, prototype_record=prototype_record)
    write_json(out_dir / "summary.json", payload)
    write_text(out_dir / "report.md", _build_report(payload=payload))
    print(f"PROTOTYPE_TDD status={status} stage={args.stage} expected={expected} out={out_dir}")
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
