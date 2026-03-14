"""
Validate frozen PRD v3 campaign rules.

Hard gate:
- JSON parse errors
- Schema violations
- Semantic invariant mismatches (frozen values)

Soft/optional:
- Source document hash drift (default warn, can be require)

Usage (Windows):
  py -3 scripts/python/validate_prd_v3_rules.py
  py -3 scripts/python/validate_prd_v3_rules.py --hash-mode require
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _today_ci_dir() -> Path:
    return _repo_root() / "logs" / "ci" / dt.date.today().isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _add_finding(findings: list[dict[str, str]], *, level: str, code: str, target: str, message: str) -> None:
    findings.append(
        {
            "level": level,
            "code": code,
            "target": target,
            "message": message,
        }
    )


def _validate_schema(
    *,
    schema_obj: dict[str, Any],
    rules_obj: dict[str, Any],
    findings: list[dict[str, str]],
    schema_path: Path,
    rules_path: Path,
) -> None:
    if jsonschema is None:
        # Minimal fallback when jsonschema package is unavailable.
        required = {
            "schemaVersion",
            "ruleSetId",
            "source",
            "mode",
            "difficultyProfiles",
            "bossRules",
            "objectiveRules",
            "rewardRules",
            "autosaveRules",
            "saveLoadRules",
            "eventRules",
            "uiRules",
            "immutableTimeline",
        }
        if not isinstance(rules_obj, dict):
            _add_finding(
                findings,
                level="fail",
                code="RULES_SCHEMA_FALLBACK_TYPE",
                target=rules_path.as_posix(),
                message="rules payload must be object.",
            )
            return
        missing = sorted(required - set(rules_obj.keys()))
        for key in missing:
            _add_finding(
                findings,
                level="fail",
                code="RULES_SCHEMA_FALLBACK_REQUIRED",
                target=f"$.{key}",
                message="missing required key.",
            )
        return

    validator = jsonschema.Draft202012Validator(schema_obj)
    errors = sorted(validator.iter_errors(rules_obj), key=lambda e: list(e.absolute_path))
    for err in errors:
        path = "$"
        if err.absolute_path:
            path = "$." + ".".join(str(p) for p in err.absolute_path)
        _add_finding(
            findings,
            level="fail",
            code="RULES_SCHEMA_INVALID",
            target=path,
            message=f"{err.message} (schema={schema_path.as_posix()})",
        )


def _expect_equal(
    *,
    rules_obj: dict[str, Any],
    findings: list[dict[str, str]],
    path: str,
    expected: Any,
    code: str,
) -> None:
    current: Any = rules_obj
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            _add_finding(
                findings,
                level="fail",
                code=code,
                target=f"$.{path}",
                message="missing required frozen field.",
            )
            return
        current = current[part]
    if current != expected:
        _add_finding(
            findings,
            level="fail",
            code=code,
            target=f"$.{path}",
            message=f"expected {expected!r}, got {current!r}.",
        )


def _validate_semantics(rules_obj: dict[str, Any], findings: list[dict[str, str]]) -> None:
    expected_values: dict[str, Any] = {
        "schemaVersion": 1,
        "ruleSetId": "Campaign-Rules-v1.0",
        "mode.campaignAiEnabled": False,
        "difficultyProfiles.normal.durationMinMinutes": 45,
        "difficultyProfiles.normal.durationMaxMinutes": 60,
        "difficultyProfiles.normal.bossCount": 2,
        "difficultyProfiles.normal.pressureGrowthCap": 5,
        "difficultyProfiles.hard.durationMinMinutes": 60,
        "difficultyProfiles.hard.durationMaxMinutes": 90,
        "difficultyProfiles.hard.bossCount": 3,
        "difficultyProfiles.hard.pressureGrowthCap": 8,
        "difficultyProfiles.hell.durationMinMinutes": 60,
        "difficultyProfiles.hell.durationMaxMinutes": 90,
        "difficultyProfiles.hell.bossCount": 3,
        "difficultyProfiles.hell.pressureGrowthCap": 12,
        "bossRules.revealBeforeForceChallenge": True,
        "bossRules.challengeOnlyInCamp": True,
        "bossRules.delayHardCapRounds": 10,
        "bossRules.forceChallengeOnLeaveCampAtCap": True,
        "bossRules.delayCounterStartAtRevealRound": 1,
        "bossRules.finalBossWinEndsRun": True,
        "bossRules.lossResetUnitStrengthTo": 1,
        "bossRules.regenPerRoundPercentByDifficulty.normal": 5,
        "bossRules.regenPerRoundPercentByDifficulty.hard": 10,
        "bossRules.regenPerRoundPercentByDifficulty.hell": 15,
        "bossRules.regenHasCap": False,
        "objectiveRules.name": "random_objective",
        "objectiveRules.questChainEnabled": False,
        "objectiveRules.phase1ObjectiveType": "reach_camp_this_round",
        "objectiveRules.settlePreviousOnCampEntry": True,
        "objectiveRules.publishAfterBossSettlement": True,
        "objectiveRules.skipPublishWhenRunEnded": True,
        "objectiveRules.failurePenalty": "none",
        "rewardRules.optionsPerDraft": 3,
        "rewardRules.dedupWithinDraft": True,
        "rewardRules.fallbackGuarantee": True,
        "rewardRules.cardsAllowDuplicate": True,
        "rewardRules.maxRelicOptionPerDraft": 1,
        "rewardRules.relicsRequireRedraw": True,
        "rewardRules.relicPoolExhaustedFallbackGold.normal": 100,
        "rewardRules.relicPoolExhaustedFallbackGold.hard": 150,
        "rewardRules.relicPoolExhaustedFallbackGold.hell": 200,
        "autosaveRules.channelSeparateFromManualSave": True,
        "autosaveRules.policy": "single_overwrite_slot",
        "autosaveRules.loadLatestValidatedAutosave": True,
        "autosaveRules.applyRewardBeforeAutosave": True,
        "autosaveRules.failurePolicy.firstFailure": "popup_warn_continue",
        "autosaveRules.failurePolicy.sameRoundRepeatedFailure": "silent_audit_continue",
        "saveLoadRules.compatibilityHardReject": True,
        "saveLoadRules.contentFingerprint.required": True,
        "saveLoadRules.contentFingerprint.algorithm": "sha256",
        "saveLoadRules.contentFingerprint.scope": "gameplay_impacting_files_only",
        "saveLoadRules.rejectedEventType": "core.sanguo.save.load.rejected",
        "eventRules.typePrefix": "core.sanguo.",
        "eventRules.roundNumberRequiredForRoundRelatedEvents": True,
        "eventRules.sequenceNoPerRound": True,
        "eventRules.sequenceNoValidationMode": "soft_warn_audit",
        "uiRules.criticalPopupRequiresManualConfirmation": True,
        "uiRules.normalPopupAutoCloseSeconds": 3,
        "uiRules.allowViewLogAndContinue": True,
    }
    for path, expected in expected_values.items():
        _expect_equal(
            rules_obj=rules_obj,
            findings=findings,
            path=path,
            expected=expected,
            code="RULES_SEMANTIC_MISMATCH",
        )

    required_match_fields = rules_obj.get("saveLoadRules", {}).get("requiredMatchFields")
    if required_match_fields != ["packId", "version", "content_fingerprint"]:
        _add_finding(
            findings,
            level="fail",
            code="RULES_SEMANTIC_MISMATCH",
            target="$.saveLoadRules.requiredMatchFields",
            message="expected exact frozen order: ['packId', 'version', 'content_fingerprint'].",
        )

    immutable_timeline = rules_obj.get("immutableTimeline")
    expected_timeline = [
        "settle_previous_objective_on_camp_entry",
        "start_new_round_at_camp",
        "camp_operations_then_leave_camp",
        "resolve_boss_flow_before_objective_publish",
        "publish_current_round_objective_for_board_phase",
        "skip_objective_publish_if_run_ends_in_boss",
    ]
    if immutable_timeline != expected_timeline:
        _add_finding(
            findings,
            level="fail",
            code="RULES_TIMELINE_MISMATCH",
            target="$.immutableTimeline",
            message="immutable timeline does not match frozen canonical sequence.",
        )


def _validate_source_hashes(
    *,
    repo_root: Path,
    rules_obj: dict[str, Any],
    findings: list[dict[str, str]],
    hash_mode: str,
) -> None:
    source = rules_obj.get("source")
    if not isinstance(source, dict):
        _add_finding(
            findings,
            level="fail",
            code="RULES_SOURCE_MISSING",
            target="$.source",
            message="missing source section.",
        )
        return

    files = source.get("files")
    if not isinstance(files, list):
        _add_finding(
            findings,
            level="fail",
            code="RULES_SOURCE_MISSING",
            target="$.source.files",
            message="source.files must be array.",
        )
        return

    for item in files:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("path") or "").strip()
        expected = str(item.get("sha256") or "").strip().lower()
        if not rel or not expected:
            continue
        path = repo_root / rel
        if not path.is_file():
            level = "warn" if hash_mode == "warn" else "fail"
            _add_finding(
                findings,
                level=level,
                code="RULES_SOURCE_FILE_MISSING",
                target=rel,
                message="source file not found.",
            )
            continue
        actual = _sha256_file(path).lower()
        if actual != expected:
            level = "warn" if hash_mode == "warn" else "fail"
            _add_finding(
                findings,
                level=level,
                code="RULES_SOURCE_HASH_MISMATCH",
                target=rel,
                message=f"expected {expected}, got {actual}.",
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PRD v3 frozen campaign rules.")
    parser.add_argument("--schema", default=".taskmaster/docs/prd-v3-rules.schema.json")
    parser.add_argument("--rules", default=".taskmaster/docs/prd-v3-rules.freeze.json")
    parser.add_argument("--hash-mode", choices=["skip", "warn", "require"], default="warn")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    repo_root = _repo_root()
    schema_path = (repo_root / args.schema).resolve()
    rules_path = (repo_root / args.rules).resolve()
    out_path = Path(args.out).resolve() if str(args.out).strip() else (_today_ci_dir() / "prd-v3-rules-validate.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    findings: list[dict[str, str]] = []
    schema_obj: dict[str, Any] = {}
    rules_obj: dict[str, Any] = {}

    try:
        schema_raw = _read_json(schema_path)
        if isinstance(schema_raw, dict):
            schema_obj = schema_raw
        else:
            _add_finding(
                findings,
                level="fail",
                code="RULES_SCHEMA_PARSE_ERROR",
                target=schema_path.as_posix(),
                message="schema root must be JSON object.",
            )
    except Exception as exc:
        _add_finding(
            findings,
            level="fail",
            code="RULES_SCHEMA_PARSE_ERROR",
            target=schema_path.as_posix(),
            message=str(exc),
        )

    try:
        rules_raw = _read_json(rules_path)
        if isinstance(rules_raw, dict):
            rules_obj = rules_raw
        else:
            _add_finding(
                findings,
                level="fail",
                code="RULES_PAYLOAD_PARSE_ERROR",
                target=rules_path.as_posix(),
                message="rules root must be JSON object.",
            )
    except Exception as exc:
        _add_finding(
            findings,
            level="fail",
            code="RULES_PAYLOAD_PARSE_ERROR",
            target=rules_path.as_posix(),
            message=str(exc),
        )

    if schema_obj and rules_obj:
        _validate_schema(
            schema_obj=schema_obj,
            rules_obj=rules_obj,
            findings=findings,
            schema_path=schema_path,
            rules_path=rules_path,
        )
        _validate_semantics(rules_obj, findings)
        if args.hash_mode != "skip":
            _validate_source_hashes(repo_root=repo_root, rules_obj=rules_obj, findings=findings, hash_mode=args.hash_mode)

    fail_count = sum(1 for x in findings if x.get("level") == "fail")
    warn_count = sum(1 for x in findings if x.get("level") == "warn")
    payload = {
        "cmd": "validate_prd_v3_rules",
        "status": "ok" if fail_count == 0 else "fail",
        "schema_path": schema_path.as_posix(),
        "rules_path": rules_path.as_posix(),
        "hash_mode": args.hash_mode,
        "jsonschema_available": jsonschema is not None,
        "fail_count": fail_count,
        "warn_count": warn_count,
        "findings": findings,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PRD_V3_RULES_VALIDATE status={payload['status']} fail={fail_count} warn={warn_count} out={out_path.as_posix()}")
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
