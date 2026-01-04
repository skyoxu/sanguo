#!/usr/bin/env python3
"""
Risk summary (deterministic) for sc-acceptance-check.

Goal:
  Produce a machine-readable "scorecard" that can be consumed by sc-llm-review.

Non-goals:
  - This module must NOT call any LLM.
  - This module must NOT re-run acceptance steps.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from _step_result import StepResult
from _util import repo_root, today_str, write_json


def _to_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _level_from_score(score: int, *, low_min: int, medium_min: int) -> str:
    if score >= low_min:
        return "low"
    if score >= medium_min:
        return "medium"
    return "high"


def _max_level(*levels: str) -> str:
    # high > medium > low
    order = {"low": 0, "medium": 1, "high": 2}
    best = "low"
    best_v = -1
    for lv in levels:
        v = order.get(str(lv or ""), -1)
        if v > best_v:
            best_v = v
            best = str(lv)
    return best


def _step_by_name(steps: list[StepResult], name: str) -> StepResult | None:
    for s in steps:
        if s.name == name:
            return s
    return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _add_signal(
    signals: list[dict[str, Any]],
    *,
    signal_id: str,
    domain: str,
    severity: str,
    message: str,
    step: str | None = None,
    evidence: str | None = None,
) -> None:
    signals.append(
        {
            "id": signal_id,
            "domain": domain,
            "severity": severity,
            "message": message,
            "step": step,
            "evidence": evidence,
        }
    )


def build_risk_summary(
    *,
    out_dir: Path,
    task_id: str,
    run_id: str,
    acceptance_status: str,
    steps: list[StepResult],
    metrics: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Returns the JSON payload (caller decides where to write it).
    """
    root = repo_root()
    thresholds = {"low_min": 85, "medium_min": 60}

    signals: list[dict[str, Any]] = []

    # --- Security
    security_score = 100
    security_hard = _step_by_name(steps, "security-hard")
    if not security_hard:
        security_score -= 10
        _add_signal(
            signals,
            signal_id="security-checks-missing",
            domain="security",
            severity="P2",
            message="security-hard step not executed (missing evidence for path/sql/audit hard gates)",
            step="security-hard",
        )
    elif security_hard.status == "fail":
        security_score -= 70
        _add_signal(
            signals,
            signal_id="security-hard-failed",
            domain="security",
            severity="P0",
            message="security-hard failed (path/sql/audit schema invariant violated)",
            step="security-hard",
            evidence=_to_posix((out_dir / "security-hard.json").relative_to(root)) if (out_dir / "security-hard.json").exists() else None,
        )
    else:
        details = security_hard.details if isinstance(security_hard.details, dict) else {}
        hard_steps = details.get("steps") if isinstance(details.get("steps"), list) else []
        for st in hard_steps:
            if not isinstance(st, dict):
                continue
            d = st.get("details") if isinstance(st.get("details"), dict) else {}
            if str(d.get("mode") or "").lower() == "warn" and _safe_int(d.get("rc"), 0) != 0:
                security_score -= 5
                _add_signal(
                    signals,
                    signal_id=f"security-hard-warn:{st.get('name')}",
                    domain="security",
                    severity="P2",
                    message=f"security hard gate reported violations under warn mode: {st.get('name')}",
                    step="security-hard",
                    evidence=_to_posix((out_dir / "security-hard.json").relative_to(root)) if (out_dir / "security-hard.json").exists() else None,
                )

    ui_event = _step_by_name(steps, "ui-event-security")
    if ui_event and ui_event.status == "fail":
        security_score -= 20
        _add_signal(
            signals,
            signal_id="ui-event-security-failed",
            domain="security",
            severity="P1",
            message="ui-event-security failed (JSON guard/source verification violations)",
            step="ui-event-security",
            evidence=_to_posix((out_dir / "ui-event-security.json").relative_to(root)) if (out_dir / "ui-event-security.json").exists() else None,
        )

    audit_evidence = _step_by_name(steps, "security-audit-executed-evidence")
    if audit_evidence and audit_evidence.status != "ok":
        security_score -= 15
        _add_signal(
            signals,
            signal_id="security-audit-evidence-missing",
            domain="security",
            severity="P1",
            message="security-audit execution evidence missing for this run_id",
            step="security-audit-executed-evidence",
            evidence=_to_posix((out_dir / "security-audit-executed-evidence.json").relative_to(root))
            if (out_dir / "security-audit-executed-evidence.json").exists()
            else None,
        )

    security_level = _level_from_score(security_score, **thresholds)

    # --- Performance
    perf_score = 100
    perf_step = _step_by_name(steps, "perf-budget")
    if not perf_step:
        perf_score -= 10
        _add_signal(
            signals,
            signal_id="perf-step-missing",
            domain="performance",
            severity="P2",
            message="perf-budget step not executed (missing performance evidence)",
            step="perf-budget",
        )
    else:
        perf_details = perf_step.details if isinstance(perf_step.details, dict) else {}
        max_p95_ms = perf_details.get("max_p95_ms")
        budget_status = str(perf_details.get("budget_status") or perf_details.get("status") or "")
        if perf_step.status == "fail":
            perf_score -= 70
            _add_signal(
                signals,
                signal_id="perf-budget-failed",
                domain="performance",
                severity="P0",
                message="perf-budget failed (p95 exceeded or evidence missing while enabled)",
                step="perf-budget",
                evidence=_to_posix((out_dir / "perf-budget.json").relative_to(root)) if (out_dir / "perf-budget.json").exists() else None,
            )
        elif _safe_int(max_p95_ms, 0) <= 0:
            perf_score -= 5
            _add_signal(
                signals,
                signal_id="perf-budget-disabled",
                domain="performance",
                severity="P2",
                message="perf budget gate disabled (max_p95_ms=0); treat as missing deterministic SLO enforcement",
                step="perf-budget",
                evidence=_to_posix((out_dir / "perf-budget.json").relative_to(root)) if (out_dir / "perf-budget.json").exists() else None,
            )
        elif budget_status and budget_status not in {"pass", "disabled"}:
            perf_score -= 10
            _add_signal(
                signals,
                signal_id=f"perf-budget-status:{budget_status}",
                domain="performance",
                severity="P2",
                message=f"perf budget status is not pass: {budget_status}",
                step="perf-budget",
                evidence=_to_posix((out_dir / "perf-budget.json").relative_to(root)) if (out_dir / "perf-budget.json").exists() else None,
            )

    perf_level = _level_from_score(perf_score, **thresholds)

    # --- Technical debt / maintainability
    debt_score = 100
    quality_rules = _step_by_name(steps, "quality-rules")
    if not quality_rules:
        debt_score -= 10
        _add_signal(
            signals,
            signal_id="quality-rules-missing",
            domain="debt",
            severity="P2",
            message="quality-rules step not executed (missing deterministic maintainability scan)",
            step="quality-rules",
        )
    else:
        qr = quality_rules.details if isinstance(quality_rules.details, dict) else {}
        counts = qr.get("counts") if isinstance(qr.get("counts"), dict) else {}
        p0 = _safe_int(counts.get("p0"), 0)
        p1 = _safe_int(counts.get("p1"), 0)
        if p0 > 0:
            debt_score -= 60
            _add_signal(
                signals,
                signal_id="quality-rules-p0",
                domain="debt",
                severity="P0",
                message=f"quality-rules reported p0 findings: {p0}",
                step="quality-rules",
                evidence=_to_posix((out_dir / "quality-rules.json").relative_to(root)) if (out_dir / "quality-rules.json").exists() else None,
            )
        if p1 > 0:
            debt_score -= 25
            _add_signal(
                signals,
                signal_id="quality-rules-p1",
                domain="debt",
                severity="P1",
                message=f"quality-rules reported p1 findings: {p1}",
                step="quality-rules",
                evidence=_to_posix((out_dir / "quality-rules.json").relative_to(root)) if (out_dir / "quality-rules.json").exists() else None,
            )

    test_quality = _step_by_name(steps, "test-quality")
    if test_quality:
        verdict = str((test_quality.details or {}).get("verdict") or "OK")
        if verdict == "Needs Fix":
            debt_score -= 15
            _add_signal(
                signals,
                signal_id="test-quality-needs-fix",
                domain="debt",
                severity="P2",
                message="test-quality verdict is Needs Fix (naming/refs/anchors/coverage heuristics)",
                step="test-quality",
                evidence=_to_posix((out_dir / "test-quality.json").relative_to(root)) if (out_dir / "test-quality.json").exists() else None,
            )

    arch_boundary = _step_by_name(steps, "architecture-boundary")
    if arch_boundary and arch_boundary.status == "fail":
        debt_score -= 40
        _add_signal(
            signals,
            signal_id="architecture-boundary-failed",
            domain="debt",
            severity="P1",
            message="architecture-boundary failed (Core/Adapters/Scenes boundary violated)",
            step="architecture-boundary",
            evidence=_to_posix((out_dir / "architecture-boundary.json").relative_to(root)) if (out_dir / "architecture-boundary.json").exists() else None,
        )

    debt_level = _level_from_score(debt_score, **thresholds)

    overall_level = _max_level(security_level, perf_level, debt_level, "high" if acceptance_status == "fail" else "low")
    overall_score = int(round((security_score + perf_score + debt_score) / 3))
    verdict = "Needs Fix" if overall_level == "high" else "OK"

    payload = {
        "cmd": "sc-risk-summary",
        "date": today_str(),
        "task_id": task_id,
        "run_id": run_id,
        "acceptance_status": acceptance_status,
        "thresholds": thresholds,
        "scores": {
            "security": security_score,
            "performance": perf_score,
            "debt": debt_score,
            "overall": overall_score,
        },
        "levels": {
            "security": security_level,
            "performance": perf_level,
            "debt": debt_level,
            "overall": overall_level,
        },
        "signals": signals,
        "metrics": metrics or {},
        "steps": [asdict(s) for s in steps],
        "verdict": verdict,
    }
    return payload


def write_risk_summary(
    *,
    out_dir: Path,
    task_id: str,
    run_id: str,
    acceptance_status: str,
    steps: list[StepResult],
    metrics: dict[str, Any] | None,
) -> tuple[Path, dict[str, Any]]:
    payload = build_risk_summary(
        out_dir=out_dir,
        task_id=task_id,
        run_id=run_id,
        acceptance_status=acceptance_status,
        steps=steps,
        metrics=metrics,
    )
    path = out_dir / "risk_summary.json"
    write_json(path, payload)
    return path, payload
