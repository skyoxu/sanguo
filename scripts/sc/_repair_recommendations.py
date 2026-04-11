from __future__ import annotations

from pathlib import Path
from typing import Any

from _agent_review_policy import build_agent_review_recommendations
from _util import repo_root


def _base_recommendation(
    *,
    rec_id: str,
    title: str,
    why: str,
    commands: list[str],
    files: list[str],
) -> dict[str, Any]:
    return {
        "id": rec_id,
        "title": title,
        "why": why,
        "actions": [],
        "commands": commands,
        "files": files,
    }


def _step_files(step: dict[str, Any]) -> list[str]:
    return [str(x) for x in [step.get("log"), step.get("summary_file")] if str(x or "").strip()]


def _resume_recommendation(task_id: str, step: dict[str, Any]) -> dict[str, Any]:
    return _base_recommendation(
        rec_id="pipeline-resume",
        title="Resume the pipeline after fixing the first blocking issue",
        why="Use the stored run artifacts instead of starting a fresh diagnostic branch when the failing step is already isolated.",
        commands=[f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --resume"],
        files=_step_files(step),
    )


def _fork_recommendation(task_id: str, step: dict[str, Any]) -> dict[str, Any]:
    return _base_recommendation(
        rec_id="pipeline-fork",
        title="Fork a new run when you want a clean recovery branch",
        why="Use a new run id when the current artifact set should remain immutable for diagnosis or comparison.",
        commands=[f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --fork"],
        files=_step_files(step),
    )


def _context_refresh_recommendation(task_id: str, step: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    files = _step_files(step)
    files.extend(
        [
            str(repo_root() / "AGENTS.md"),
            str(repo_root() / "docs" / "agents" / "00-index.md"),
            str(repo_root() / "docs" / "agents" / "01-session-recovery.md"),
        ]
    )
    joined_reasons = ", ".join(reasons) if reasons else "marathon heuristic requested refresh"
    return _base_recommendation(
        rec_id="pipeline-context-refresh",
        title="Refresh context before the next attempt",
        why=f"The pipeline crossed the refresh threshold: {joined_reasons}. Reload the recovery map before resuming.",
        commands=[
            f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --fork",
            f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --resume",
        ],
        files=files,
    )


def _wall_time_recommendation(task_id: str, step: dict[str, Any]) -> dict[str, Any]:
    return _base_recommendation(
        rec_id="pipeline-wall-time",
        title="Resume or fork after wall-time stop-loss",
        why="The current run exhausted its wall-time budget. Continue from the stored checkpoint instead of restarting from scratch.",
        commands=[
            f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --resume",
            f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --fork",
        ],
        files=_step_files(step),
    )


def _chapter6_route_repo_noise_recommendation(task_id: str, step: dict[str, Any]) -> dict[str, Any]:
    return _base_recommendation(
        rec_id="chapter6-route-repo-noise",
        title="Inspect repo-level noise before paying for another Chapter 6 rerun",
        why="The latest route classified the failure as repo noise or process contention, so another immediate 6.7/6.8 rerun is likely waste.",
        commands=[
            f"py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id {task_id} --recommendation-only",
            f"py -3 scripts/python/dev_cli.py chapter6-route --task-id {task_id} --recommendation-only",
        ],
        files=_step_files(step),
    )


def _chapter6_route_fix_deterministic_recommendation(task_id: str, step: dict[str, Any]) -> dict[str, Any]:
    return _base_recommendation(
        rec_id="chapter6-route-fix-deterministic",
        title="Fix the deterministic failure before reopening Chapter 6",
        why="The latest route says the blocking issue is still deterministic, so reopening 6.7 or paying for 6.8 would only repeat the same failure family.",
        commands=[
            f"py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id {task_id} --recommendation-only",
            f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --resume",
        ],
        files=_step_files(step),
    )


def _chapter6_route_needs_fix_fast_recommendation(task_id: str, step: dict[str, Any]) -> dict[str, Any]:
    return _base_recommendation(
        rec_id="chapter6-route-run-6-8",
        title="Use the narrow 6.8 lane instead of reopening a full 6.7 rerun",
        why="The latest route already proved deterministic evidence is sufficient for this task. Continue with the targeted Needs Fix closure lane.",
        commands=[
            f"py -3 scripts/python/dev_cli.py chapter6-route --task-id {task_id} --recommendation-only",
            f"py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id {task_id} --delivery-profile fast-ship --rerun-failing-only --max-rounds 1",
        ],
        files=_step_files(step),
    )


def _chapter6_route_inspect_recommendation(task_id: str, step: dict[str, Any]) -> dict[str, Any]:
    return _base_recommendation(
        rec_id="chapter6-route-inspect-first",
        title="Inspect the latest artifacts before choosing the next Chapter 6 lane",
        why="The latest route could not justify another rerun yet. Read the compact recovery recommendation first instead of paying for more pipeline cost.",
        commands=[
            f"py -3 scripts/python/dev_cli.py resume-task --task-id {task_id} --recommendation-only",
            f"py -3 scripts/python/dev_cli.py inspect-run --kind pipeline --task-id {task_id} --recommendation-only",
        ],
        files=_step_files(step),
    )


def _chapter6_route_runtime_recommendations(task_id: str, step: dict[str, Any], runtime_state: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = runtime_state.get("diagnostics") if isinstance(runtime_state.get("diagnostics"), dict) else {}
    rerun_guard = diagnostics.get("rerun_guard") if isinstance(diagnostics.get("rerun_guard"), dict) else {}
    guard_kind = str(rerun_guard.get("kind") or "").strip().lower()
    stop_reason = str(runtime_state.get("stop_reason") or "").strip().lower()
    effective_kind = guard_kind
    if not effective_kind and stop_reason.startswith("rerun_blocked:"):
        effective_kind = stop_reason.split(":", 1)[1].strip().lower()

    if effective_kind == "chapter6_route_repo_noise_stop":
        return [_chapter6_route_repo_noise_recommendation(task_id, step)]
    if effective_kind == "chapter6_route_fix_deterministic":
        return [_chapter6_route_fix_deterministic_recommendation(task_id, step)]
    if effective_kind == "chapter6_route_run_6_8":
        return [_chapter6_route_needs_fix_fast_recommendation(task_id, step)]
    if effective_kind == "chapter6_route_inspect_first":
        return [_chapter6_route_inspect_recommendation(task_id, step)]
    return []


def _test_recommendations(task_id: str, step: dict[str, Any], log_text: str) -> list[dict[str, Any]]:
    files = _step_files(step)
    recommendations = [
        _resume_recommendation(task_id, step),
        _base_recommendation(
            rec_id="sc-test-rerun",
            title="Rerun isolated sc-test first",
            why="Keep the failure surface small before rerunning the full review pipeline.",
            commands=[" ".join(step.get("cmd") or ["py", "-3", "scripts/sc/test.py", "--task-id", task_id])],
            files=files,
        ),
    ]
    if "MSB1009" in log_text or "Project file does not exist" in log_text:
        recommendations.append(
            _base_recommendation(
                rec_id="sc-test-project-path",
                title="Check solution and project targets",
                why="The test runner resolved a missing .csproj or solution path.",
                commands=[f"py -3 scripts/sc/test.py --task-id {task_id} --dry-run"],
                files=files,
            )
        )
    if "coverage" in log_text.lower():
        recommendations.append(
            _base_recommendation(
                rec_id="sc-test-coverage-gate",
                title="Inspect coverage gate before changing thresholds",
                why="A coverage failure should be fixed by adding tests or excluding non-domain code deliberately.",
                commands=[f"py -3 scripts/sc/test.py --task-id {task_id}"],
                files=files,
            )
        )
    if "godot" in log_text.lower() and "not found" in log_text.lower():
        recommendations.append(
            _base_recommendation(
                rec_id="sc-test-godot-bin",
                title="Provide an explicit Godot binary",
                why="The test step could not locate Godot for headless or integration work.",
                commands=[f'py -3 scripts/sc/test.py --task-id {task_id} --godot-bin "$env:GODOT_BIN"'],
                files=files,
            )
        )
    return recommendations


def _acceptance_recommendations(task_id: str, step: dict[str, Any], log_text: str) -> list[dict[str, Any]]:
    files = _step_files(step)
    recommendations = [
        _resume_recommendation(task_id, step),
        _base_recommendation(
            rec_id="acceptance-rerun",
            title="Rerun acceptance only after fixing the first hard failure",
            why="Acceptance failures usually point to missing refs, evidence, or architecture linkage.",
            commands=[" ".join(step.get("cmd") or ["py", "-3", "scripts/sc/acceptance_check.py", "--task-id", task_id])],
            files=files,
        ),
    ]
    lowered = log_text.lower()
    if "validate_task_test_refs" in lowered or "require-task-test-refs" in lowered:
        recommendations.append(
            _base_recommendation(
                rec_id="acceptance-test-refs",
                title="Fill task test refs before rerun",
                why="The acceptance gate expects `test_refs` to exist and resolve.",
                commands=[f"py -3 scripts/python/validate_task_test_refs.py --task-id {task_id}"],
                files=files + [str(repo_root() / "docs" / "testing-framework.md")],
            )
        )
    if "validate_acceptance_refs" in lowered or "acceptance refs" in lowered:
        recommendations.append(
            _base_recommendation(
                rec_id="acceptance-refs-align",
                title="Align acceptance refs with task and overlay docs",
                why="Acceptance refs drift usually means overlay, taskmaster, and tests are out of sync.",
                commands=[f"py -3 scripts/python/validate_acceptance_refs.py --task-id {task_id}"],
                files=files,
            )
        )
    if "strict-adr-status" in lowered or "adr" in lowered:
        recommendations.append(
            _base_recommendation(
                rec_id="acceptance-adr-status",
                title="Check ADR status and references",
                why="The acceptance step detected ADR status or linkage issues.",
                commands=["py -3 scripts/python/task_links_validate.py"],
                files=files + [str(repo_root() / "docs" / "architecture" / "ADR_INDEX_GODOT.md")],
            )
        )
    if "headless" in lowered or "e2e" in lowered:
        recommendations.append(
            _base_recommendation(
                rec_id="acceptance-headless",
                title="Inspect headless evidence and rerun only the failing path",
                why="Headless evidence failures are usually environment or resource-path issues.",
                commands=[f'py -3 scripts/sc/acceptance_check.py --task-id {task_id} --godot-bin "$env:GODOT_BIN"'],
                files=files,
            )
        )
    return recommendations


def _llm_review_recommendations(task_id: str, step: dict[str, Any], log_text: str) -> list[dict[str, Any]]:
    files = _step_files(step)
    recommendations = [
        _resume_recommendation(task_id, step),
        _base_recommendation(
            rec_id="llm-review-rerun",
            title="Fix findings before rerunning llm_review",
            why="LLM review should converge on a smaller diff, not be used as the first diagnostic tool.",
            commands=[" ".join(step.get("cmd") or ["py", "-3", "scripts/sc/llm_review.py", "--task-id", task_id])],
            files=files,
        ),
    ]
    lowered = log_text.lower()
    if "needs fix" in lowered or "needs-fix" in lowered:
        recommendations.append(
            _base_recommendation(
                rec_id="llm-review-needs-fix",
                title="Resolve the top Needs Fix items first",
                why="The reviewer already narrowed the problem set. Fix the highest-severity findings before asking for another pass.",
                commands=[f"py -3 scripts/sc/llm_review_needs_fix_fast.py --task-id {task_id}"],
                files=files,
            )
        )
    if "semantic" in lowered:
        recommendations.append(
            _base_recommendation(
                rec_id="llm-review-semantic",
                title="Re-align semantics before rerun",
                why="Semantic gate failures usually come from acceptance refs, task context, or contracts drifting apart.",
                commands=[f"py -3 scripts/sc/llm_semantic_gate_all.py --task-id {task_id}"],
                files=files,
            )
        )
    return recommendations


def build_step_recommendations(*, task_id: str, step_name: str, step: dict[str, Any], log_text: str) -> list[dict[str, Any]]:
    if step_name == "sc-test":
        return _test_recommendations(task_id, step, log_text)
    if step_name == "sc-acceptance-check":
        return _acceptance_recommendations(task_id, step, log_text)
    return _llm_review_recommendations(task_id, step, log_text)


def build_runtime_recommendations(
    *,
    task_id: str,
    out_dir: Path,
    runtime_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    agent_review = ((runtime_state or {}).get("agent_review") or {}) if isinstance(runtime_state, dict) else {}
    recommendations = build_agent_review_recommendations(task_id=task_id, agent_review=agent_review, out_dir=out_dir)
    synthetic_step = {"log": "", "summary_file": ""}
    if not isinstance(runtime_state, dict):
        return recommendations
    recommendations.extend(_chapter6_route_runtime_recommendations(task_id, synthetic_step, runtime_state))
    reasons = [str(x) for x in (runtime_state.get("context_refresh_reasons") or []) if str(x).strip()]
    if bool(runtime_state.get("context_refresh_needed")):
        recommendations.append(_context_refresh_recommendation(task_id, synthetic_step, reasons))
    if str(runtime_state.get("stop_reason") or "").strip().lower() == "wall_time_exceeded":
        recommendations.append(_wall_time_recommendation(task_id, synthetic_step))
    if recommendations:
        recommendations.append(_fork_recommendation(task_id, synthetic_step))
    return recommendations


def extend_with_runtime_recommendations(
    *,
    task_id: str,
    step: dict[str, Any],
    runtime_state: dict[str, Any] | None,
    recommendations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(runtime_state, dict):
        return recommendations
    recommendations.extend(_chapter6_route_runtime_recommendations(task_id, step, runtime_state))
    reasons = [str(x) for x in (runtime_state.get("context_refresh_reasons") or []) if str(x).strip()]
    if bool(runtime_state.get("context_refresh_needed")):
        recommendations.append(_context_refresh_recommendation(task_id, step, reasons))
    if str(runtime_state.get("stop_reason") or "").strip().lower() == "wall_time_exceeded":
        recommendations.append(_wall_time_recommendation(task_id, step))
    recommendations.append(_fork_recommendation(task_id, step))
    return recommendations
