#!/usr/bin/env python3
"""
Validate lock consistency between PRD machine appendix and config contracts.

This checker includes a built-in ruleset originally used by a concrete game
project. In template repositories, missing domain files are treated as
"skipped" by default to avoid false blocking.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any


EXPECTED_VALUES = {
    "prd_unlock_policy": "clear-to-unlock-config-driven-no-cross-tier-skip",
    "prd_difficulty_unlock_policy": "clear-to-unlock-config-driven",
    "prd_boss_count_policy": "config-driven",
    "prd_boss_count_default": 2,
    "prd_audit_source": "script-only",
    "prd_spawn_no_eligible": "discard_tick_budget",
    "prd_night_weight_semantics": "sampling-priority-only-not-channel-budget",
    "difficulty_unlock_policy": "clear-to-unlock-config-driven",
    "audit_writer_source": "script-only",
    "spawn_boss_mode": "config-driven",
    "debt_in_progress_policy": "continue-until-complete",
    "debt_unlock_threshold": "gold-at-least-zero",
    "build_soft_limit_scope": "player-global",
    "reward_popup_timing": "immediately-after-night-settlement",
    "reward_popup_pause": "pause-day-night-timer-until-choice",
    "reward_gold_fallback_scaling": "fixed-600-not-affected-by-difficulty",
    "path_fail_primary": "nearest-blocking-structure-by-path-cost",
    "path_fail_when_no_blocker": "attack-castle",
    "path_fail_gate_policy": "enemy-cannot-pass-alive-gate-can-attack-gate-destroyed-passable",
    "clone_cap_scope": "global",
    "clone_cap_max": 10,
    "clone_kills_counted": True,
    "clone_budget_accounting": "not-counted-as-boss-channel-budget",
    "integer_pipeline": "multiply-then-divide",
    "integer_rounding": "floor",
    "integer_bankers_rounding": False,
    "damage_pipeline_order": [
        "base_damage",
        "offense_defense_modifiers",
        "difficulty_modifiers",
        "armor_reduction",
        "min_damage_clamp_1",
    ],
    "summary_fallback_castle": "fallback target is `castle` (no idle wait)",
    "summary_gate_policy": "enemy cannot pass alive gate, can attack gate body, destroyed gate becomes passable",
    "summary_clone_policy": "Clone policy: `global cap 10`; clone kills counted in report; clones do not consume boss channel budget.",
    "summary_damage_pipeline": "Damage pipeline order: `base_damage -> offense_defense_modifiers -> difficulty_modifiers -> armor_reduction -> min_damage_clamp_1`.",
    "summary_debt_cross_zero": "Debt cross-zero behavior: in-progress spend actions continue to completion; only new spend requests are blocked.",
    "summary_debt_unlock": "Debt unlock threshold: spending unlocks immediately when gold returns to `>=0`.",
    "summary_build_soft_limit": "Build soft limit scope: `player-global 100ms per placement`.",
    "summary_reward_popup": "Reward popup timing: `immediately after night settlement`; day/night timer pauses until selection.",
    "summary_reward_gold_scaling": "Gold fallback scaling: `fixed 600`, not affected by difficulty multipliers.",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def today_str() -> str:
    return dt.date.today().strftime("%Y-%m-%d")


def default_output_path(root: Path) -> Path:
    return root / "logs" / "ci" / today_str() / "config-contract-sync-check.json"


def auto_find_prd(root: Path) -> Path | None:
    candidates = sorted(root.glob("docs/prd/*GAMEDESIGN*.md"))
    return candidates[0] if candidates else None


def auto_find_summary(root: Path) -> Path | None:
    candidates = sorted(root.glob("docs/prd/*LOCKED-SUMMARY*.md"))
    return candidates[0] if candidates else None


def required_contract_paths(root: Path) -> list[Path]:
    return [
        root / "Game.Core/Contracts/Config/difficulty-config.schema.json",
        root / "Game.Core/Contracts/Config/difficulty-config.sample.json",
        root / "Game.Core/Contracts/Config/spawn-config.schema.json",
        root / "Game.Core/Contracts/Config/spawn-config.sample.json",
        root / "Game.Core/Contracts/Config/config-change-audit.schema.json",
        root / "Game.Core/Contracts/Config/spawn-config.validator.rules.md",
    ]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_machine_appendix_json(prd_path: Path) -> dict[str, Any]:
    text = prd_path.read_text(encoding="utf-8")
    heading_pattern = r"^##\s+16\.\s+Machine-Readable Appendix \(JSON\)\s*$"
    heading_match = re.search(heading_pattern, text, flags=re.MULTILINE)
    if not heading_match:
        raise ValueError(f"Cannot find machine appendix heading in {prd_path.as_posix()}")
    remaining = text[heading_match.end() :]
    block_match = re.search(r"```json\s*\n(.*?)\n```", remaining, flags=re.DOTALL)
    if not block_match:
        raise ValueError(f"Cannot find JSON code fence under machine appendix in {prd_path.as_posix()}")
    return json.loads(block_match.group(1))


def nested_get(obj: Any, path: list[str], default: Any = None) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def add_check(results: list[dict[str, Any]], check_id: str, actual: Any, expected: Any) -> None:
    results.append({"check_id": check_id, "ok": actual == expected, "actual": actual, "expected": expected})


def run_checks(root: Path, prd_path: Path, summary_path: Path) -> list[dict[str, Any]]:
    difficulty_schema = load_json(root / "Game.Core/Contracts/Config/difficulty-config.schema.json")
    difficulty_sample = load_json(root / "Game.Core/Contracts/Config/difficulty-config.sample.json")
    spawn_schema = load_json(root / "Game.Core/Contracts/Config/spawn-config.schema.json")
    spawn_sample = load_json(root / "Game.Core/Contracts/Config/spawn-config.sample.json")
    audit_schema = load_json(root / "Game.Core/Contracts/Config/config-change-audit.schema.json")
    rules_text = (root / "Game.Core/Contracts/Config/spawn-config.validator.rules.md").read_text(encoding="utf-8")
    summary_text = summary_path.read_text(encoding="utf-8")
    prd_json = parse_machine_appendix_json(prd_path)
    locked = nested_get(prd_json, ["locked_constraints"], {})

    results: list[dict[str, Any]] = []
    checks: list[tuple[str, Any, Any]] = [
        ("prd.difficulty.unlock_policy", nested_get(locked, ["difficulty", "unlock_policy"]), EXPECTED_VALUES["prd_unlock_policy"]),
        ("prd.difficulty_unlock_policy", nested_get(locked, ["difficulty_unlock_policy"]), EXPECTED_VALUES["prd_difficulty_unlock_policy"]),
        ("prd.difficulty_unlock_cross_tier_skip", nested_get(locked, ["difficulty_unlock_cross_tier_skip"]), False),
        ("prd.boss_night.boss_count_policy", nested_get(locked, ["boss_night", "boss_count_policy"]), EXPECTED_VALUES["prd_boss_count_policy"]),
        ("prd.boss_night.boss_count_default", nested_get(locked, ["boss_night", "boss_count_default"]), EXPECTED_VALUES["prd_boss_count_default"]),
        ("prd.config_change_audit_source", nested_get(locked, ["config_change_audit_source"]), EXPECTED_VALUES["prd_audit_source"]),
        ("prd.budget_to_spawn.on_no_eligible_candidates", nested_get(locked, ["budget_to_spawn", "on_no_eligible_candidates"]), EXPECTED_VALUES["prd_spawn_no_eligible"]),
        ("prd.budget_to_spawn.night_type_weight_semantics", nested_get(locked, ["budget_to_spawn", "night_type_weight_semantics"]), EXPECTED_VALUES["prd_night_weight_semantics"]),
        ("prd.debt_guardrails.in_progress_spend_actions_when_gold_below_zero", nested_get(locked, ["debt_guardrails", "in_progress_spend_actions_when_gold_below_zero"]), EXPECTED_VALUES["debt_in_progress_policy"]),
        ("prd.debt_guardrails.unlock_threshold", nested_get(locked, ["debt_guardrails", "unlock_threshold"]), EXPECTED_VALUES["debt_unlock_threshold"]),
        ("prd.build_soft_limit_scope", nested_get(locked, ["build_soft_limit_scope"]), EXPECTED_VALUES["build_soft_limit_scope"]),
        ("prd.reward_popup_timing", nested_get(locked, ["reward_popup_timing"]), EXPECTED_VALUES["reward_popup_timing"]),
        ("prd.reward_popup_pause", nested_get(locked, ["reward_popup_pause"]), EXPECTED_VALUES["reward_popup_pause"]),
        ("prd.reward_gold_fallback_scaling", nested_get(locked, ["reward_gold_fallback_scaling"]), EXPECTED_VALUES["reward_gold_fallback_scaling"]),
        ("prd.path_fail_fallback.primary", nested_get(locked, ["path_fail_fallback", "primary"]), EXPECTED_VALUES["path_fail_primary"]),
        ("prd.path_fail_fallback.when_no_blocker", nested_get(locked, ["path_fail_fallback", "when_no_blocker"]), EXPECTED_VALUES["path_fail_when_no_blocker"]),
        ("prd.path_fail_fallback.gate_policy", nested_get(locked, ["path_fail_fallback", "gate_policy"]), EXPECTED_VALUES["path_fail_gate_policy"]),
        ("prd.boss_clone_policy.cap_scope", nested_get(locked, ["boss_clone_policy", "cap_scope"]), EXPECTED_VALUES["clone_cap_scope"]),
        ("prd.boss_clone_policy.cap_max", nested_get(locked, ["boss_clone_policy", "cap_max"]), EXPECTED_VALUES["clone_cap_max"]),
        ("prd.boss_clone_policy.kills_counted_in_report", nested_get(locked, ["boss_clone_policy", "kills_counted_in_report"]), EXPECTED_VALUES["clone_kills_counted"]),
        ("prd.boss_clone_policy.boss_budget_accounting", nested_get(locked, ["boss_clone_policy", "boss_budget_accounting"]), EXPECTED_VALUES["clone_budget_accounting"]),
        ("prd.integer_rounding_policy.pipeline", nested_get(locked, ["integer_rounding_policy", "pipeline"]), EXPECTED_VALUES["integer_pipeline"]),
        ("prd.integer_rounding_policy.rounding", nested_get(locked, ["integer_rounding_policy", "rounding"]), EXPECTED_VALUES["integer_rounding"]),
        ("prd.integer_rounding_policy.bankers_rounding", nested_get(locked, ["integer_rounding_policy", "bankers_rounding"]), EXPECTED_VALUES["integer_bankers_rounding"]),
        ("prd.damage_pipeline_order", nested_get(locked, ["damage_pipeline_order"]), EXPECTED_VALUES["damage_pipeline_order"]),
        ("difficulty.schema.unlock_policy.enum", nested_get(difficulty_schema, ["properties", "unlock_policy", "enum"], [None])[0], EXPECTED_VALUES["difficulty_unlock_policy"]),
        ("difficulty.schema.allow_cross_tier_skip.const", nested_get(difficulty_schema, ["properties", "allow_cross_tier_skip", "const"]), False),
        ("difficulty.sample.unlock_policy", nested_get(difficulty_sample, ["unlock_policy"]), EXPECTED_VALUES["difficulty_unlock_policy"]),
        ("difficulty.sample.allow_cross_tier_skip", nested_get(difficulty_sample, ["allow_cross_tier_skip"]), False),
        ("spawn.schema.night_schedule.required_has_boss_count", "boss_count" in nested_get(spawn_schema, ["properties", "night_schedule", "required"], []), True),
        ("spawn.schema.boss_count.mode.enum", nested_get(spawn_schema, ["properties", "night_schedule", "properties", "boss_count", "properties", "mode", "enum"], [None])[0], EXPECTED_VALUES["spawn_boss_mode"]),
        ("spawn.sample.boss_count.mode", nested_get(spawn_sample, ["night_schedule", "boss_count", "mode"]), EXPECTED_VALUES["spawn_boss_mode"]),
        ("spawn.sample.boss_count.default", nested_get(spawn_sample, ["night_schedule", "boss_count", "default"]), 2),
        ("audit.schema.writer_source.const", nested_get(audit_schema, ["properties", "writer_source", "const"]), EXPECTED_VALUES["audit_writer_source"]),
        ("rules.spawn.r005_contains_mode_rule", "boss_count.mode == config-driven" in rules_text, True),
        ("rules.spawn.r005_contains_default_rule", "boss_count.default >= 1" in rules_text, True),
        ("summary.path_fail_fallback_castle", EXPECTED_VALUES["summary_fallback_castle"] in summary_text, True),
        ("summary.path_fail_gate_policy", EXPECTED_VALUES["summary_gate_policy"] in summary_text, True),
        ("summary.clone_policy", EXPECTED_VALUES["summary_clone_policy"] in summary_text, True),
        ("summary.damage_pipeline_order", EXPECTED_VALUES["summary_damage_pipeline"] in summary_text, True),
        ("summary.debt_cross_zero", EXPECTED_VALUES["summary_debt_cross_zero"] in summary_text, True),
        ("summary.debt_unlock_threshold", EXPECTED_VALUES["summary_debt_unlock"] in summary_text, True),
        ("summary.build_soft_limit_scope", EXPECTED_VALUES["summary_build_soft_limit"] in summary_text, True),
        ("summary.reward_popup_timing", EXPECTED_VALUES["summary_reward_popup"] in summary_text, True),
        ("summary.reward_gold_scaling", EXPECTED_VALUES["summary_reward_gold_scaling"] in summary_text, True),
    ]
    for check_id, actual, expected in checks:
        add_check(results, check_id, actual, expected)
    return results


def resolve_rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except Exception:
        return str(path)


def write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check lock consistency across PRD and config contracts.")
    parser.add_argument("--prd", default="", help="Path to PRD file with machine appendix JSON. Empty means auto-discover docs/prd/*GAMEDESIGN*.md.")
    parser.add_argument("--out", default="", help="Optional output report path (default: logs/ci/<YYYY-MM-DD>/config-contract-sync-check.json)")
    parser.add_argument("--summary", default="", help="Path to LOCKED-SUMMARY markdown file. Empty means auto-discover docs/prd/*LOCKED-SUMMARY*.md.")
    parser.add_argument("--strict-presence", action="store_true", help="Fail if required files are missing. Default behavior is template-safe skip.")
    args = parser.parse_args()

    root = repo_root()
    prd_path = Path(args.prd) if str(args.prd).strip() else auto_find_prd(root)
    if prd_path is not None and not prd_path.is_absolute():
        prd_path = (root / prd_path).resolve()
    summary_path = Path(args.summary) if str(args.summary).strip() else auto_find_summary(root)
    if summary_path is not None and not summary_path.is_absolute():
        summary_path = (root / summary_path).resolve()
    out_path = Path(args.out) if str(args.out).strip() else default_output_path(root)
    if not out_path.is_absolute():
        out_path = (root / out_path).resolve()

    missing: list[str] = []
    if prd_path is None:
        missing.append("docs/prd/*GAMEDESIGN*.md")
    elif not prd_path.exists():
        missing.append(str(prd_path))
    if summary_path is None:
        missing.append("docs/prd/*LOCKED-SUMMARY*.md")
    elif not summary_path.exists():
        missing.append(str(summary_path))
    for path in required_contract_paths(root):
        if not path.exists():
            missing.append(str(path))
    if missing:
        status = "fail" if bool(args.strict_presence) else "skipped"
        payload = {
            "timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": status,
            "reason": "required_files_missing",
            "missing": sorted(set(missing)),
            "report": [],
        }
        write_payload(out_path, payload)
        print(f"Status: {status.upper()}")
        print(f"Report: {resolve_rel(out_path, root)}")
        for item in payload["missing"]:
            print(f"- missing: {item}")
        return 1 if bool(args.strict_presence) else 0

    try:
        assert prd_path is not None
        assert summary_path is not None
        checks = run_checks(root, prd_path, summary_path)
    except Exception as exc:
        payload = {
            "timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "error",
            "error": str(exc),
            "report": [],
        }
        write_payload(out_path, payload)
        print(f"ERROR: {exc}")
        print(f"Report: {resolve_rel(out_path, root)}")
        return 1

    failed = [item for item in checks if not item["ok"]]
    status = "pass" if not failed else "fail"
    payload = {
        "timestamp": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "total_checks": len(checks),
        "failed_checks": len(failed),
        "prd": resolve_rel(prd_path, root),
        "summary": resolve_rel(summary_path, root),
        "report": checks,
    }
    write_payload(out_path, payload)

    print(f"Status: {status.upper()}")
    print(f"Checks: {len(checks)} | Failed: {len(failed)}")
    print(f"Report: {resolve_rel(out_path, root)}")
    if failed:
        for item in failed:
            print(f"- {item['check_id']}: actual={item['actual']!r}, expected={item['expected']!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
