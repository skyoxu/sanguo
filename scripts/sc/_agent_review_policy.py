from __future__ import annotations

from pathlib import Path
from typing import Any


OWNER_STEP_AXES = {
    "sc-test": "implementation",
    "sc-acceptance-check": "governance",
    "sc-llm-review": "governance",
    "producer-pipeline": "governance",
}

RESUME_BIAS_CATEGORIES = {
    "llm-review",
    "prompt-budget",
    "review-noise",
    "style",
    "naming",
    "formatting",
}

REFRESH_BIAS_CATEGORIES = {
    "acceptance-refs",
    "task-context",
    "contracts-drift",
    "overlay-task-drift",
    "adr-linkage",
}

FORK_ALWAYS_CATEGORIES = {
    "schema-integrity",
    "summary-integrity",
}

FORK_ON_HIGH_CATEGORIES = {
    "artifact-integrity",
    "cross-layer-contract-break",
}

CATEGORY_AXES = {
    "acceptance-refs": {"governance"},
    "task-context": {"governance"},
    "overlay-task-drift": {"governance"},
    "adr-linkage": {"governance"},
    "llm-review": {"governance"},
    "prompt-budget": {"governance"},
    "review-noise": {"governance"},
    "style": {"governance"},
    "naming": {"governance"},
    "formatting": {"governance"},
    "artifact-integrity": {"governance"},
    "schema-integrity": {"governance"},
    "summary-integrity": {"governance"},
    "contracts-drift": {"contracts"},
    "cross-layer-contract-break": {"contracts", "implementation"},
}


def _stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _normalize_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings = payload.get("findings")
    return [item for item in findings if isinstance(item, dict)] if isinstance(findings, list) else []


def _axes_for_finding(finding: dict[str, Any]) -> list[str]:
    axes: list[str] = []
    owner_axis = OWNER_STEP_AXES.get(str(finding.get("owner_step") or "").strip())
    if owner_axis:
        axes.append(owner_axis)
    category = str(finding.get("category") or "").strip()
    axes.extend(sorted(CATEGORY_AXES.get(category) or set()))
    return _stable_unique(axes)


def _categories_by_severity(findings: list[dict[str, Any]], categories: set[str], severity: str) -> list[str]:
    matched: list[str] = []
    for item in findings:
        category = str(item.get("category") or "").strip()
        if category not in categories:
            continue
        if str(item.get("severity") or "").strip().lower() != severity:
            continue
        matched.append(category)
    return _stable_unique(matched)


def _categories_in(findings: list[dict[str, Any]], categories: set[str]) -> list[str]:
    matched: list[str] = []
    for item in findings:
        category = str(item.get("category") or "").strip()
        if category in categories:
            matched.append(category)
    return _stable_unique(matched)


def summarize_agent_review(payload: dict[str, Any]) -> dict[str, Any]:
    findings = _normalize_findings(payload)
    review_verdict = str(payload.get("review_verdict") or "").strip().lower()
    owner_steps = _stable_unique([str(item.get("owner_step") or "") for item in findings])
    categories = _stable_unique([str(item.get("category") or "") for item in findings])
    severity_counts = {"low": 0, "medium": 0, "high": 0}
    for item in findings:
        severity = str(item.get("severity") or "").strip().lower()
        if severity in severity_counts:
            severity_counts[severity] += 1

    semantic_axes = _stable_unique([axis for item in findings for axis in _axes_for_finding(item)])
    governance_owner_steps = [step for step in owner_steps if OWNER_STEP_AXES.get(step) == "governance"]
    implementation_owner_steps = [step for step in owner_steps if OWNER_STEP_AXES.get(step) == "implementation"]
    cross_step = len(owner_steps) >= 2
    core_axes = [axis for axis in semantic_axes if axis in {"governance", "implementation", "contracts", "tests"}]
    cross_axis = len(core_axes) >= 2
    resume_bias_categories = _categories_in(findings, RESUME_BIAS_CATEGORIES)
    refresh_bias_categories = _categories_in(findings, REFRESH_BIAS_CATEGORIES)
    fork_always_categories = _categories_in(findings, FORK_ALWAYS_CATEGORIES)
    high_refresh_categories = _categories_by_severity(findings, REFRESH_BIAS_CATEGORIES, "high")
    high_fork_categories = _categories_by_severity(findings, FORK_ON_HIGH_CATEGORIES, "high")
    low_noise_only = bool(findings) and all(
        str(item.get("category") or "").strip() in RESUME_BIAS_CATEGORIES for item in findings
    )

    reasons: list[str] = []
    recommended_action = "none"
    if fork_always_categories:
        reasons.extend([f"agent_review_integrity_reset({category})" for category in fork_always_categories])
        recommended_action = "fork"
    elif high_fork_categories:
        reasons.extend([f"agent_review_high_severity_fork_category({category})" for category in high_fork_categories])
        recommended_action = "fork"
    elif review_verdict == "block":
        if cross_step:
            if cross_axis or not low_noise_only or severity_counts["high"] > 0:
                reasons.append("agent_review_cross_step_block")
        if cross_axis:
            reasons.append("agent_review_semantic_axis_mix")
        if reasons:
            recommended_action = "fork"
        elif high_refresh_categories:
            reasons.extend([f"agent_review_high_severity_refresh_category({category})" for category in high_refresh_categories])
            recommended_action = "refresh"
        else:
            recommended_action = "resume" if findings else "none"
    elif review_verdict == "needs-fix":
        if high_refresh_categories:
            reasons.extend([f"agent_review_high_severity_refresh_category({category})" for category in high_refresh_categories])
            recommended_action = "refresh"
        elif cross_step and (cross_axis or bool(refresh_bias_categories)):
            reasons.append("agent_review_cross_step_needs_fix")
            if cross_axis:
                reasons.append("agent_review_semantic_axis_mix")
            reasons.extend([f"agent_review_structural_drift_category({category})" for category in refresh_bias_categories])
            recommended_action = "refresh"
        else:
            recommended_action = "resume" if findings else "none"
    elif review_verdict == "pass":
        recommended_action = "none"
    elif findings:
        recommended_action = "resume"

    return {
        "review_verdict": review_verdict,
        "recommended_action": recommended_action,
        "recommended_refresh_reasons": reasons,
        "owner_steps": owner_steps,
        "categories": categories,
        "semantic_axes": semantic_axes,
        "governance_owner_steps": governance_owner_steps,
        "implementation_owner_steps": implementation_owner_steps,
        "resume_bias_categories": resume_bias_categories,
        "refresh_bias_categories": refresh_bias_categories,
        "fork_always_categories": fork_always_categories,
        "high_refresh_categories": high_refresh_categories,
        "high_fork_categories": high_fork_categories,
        "cross_step": cross_step,
        "cross_axis": cross_axis,
        "severity_counts": severity_counts,
        "findings_count": len(findings),
    }


def apply_agent_review_policy(state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    signal = summarize_agent_review(payload)
    return apply_agent_review_signal(state, signal)


def apply_agent_review_signal(state: dict[str, Any], signal: dict[str, Any]) -> dict[str, Any]:
    state["agent_review"] = signal
    if signal["recommended_action"] in {"refresh", "fork"}:
        current = [str(item) for item in (state.get("context_refresh_reasons") or []) if str(item).strip()]
        state["context_refresh_needed"] = True
        state["context_refresh_reasons"] = _stable_unique(current + list(signal["recommended_refresh_reasons"]))
    return state


def build_agent_review_explain(signal: dict[str, Any]) -> dict[str, Any]:
    recommended_action = str(signal.get("recommended_action") or "").strip().lower() or "none"
    reasons = [str(item) for item in (signal.get("recommended_refresh_reasons") or []) if str(item).strip()]
    owner_steps = [str(item) for item in (signal.get("owner_steps") or []) if str(item).strip()]
    categories = [str(item) for item in (signal.get("categories") or []) if str(item).strip()]
    semantic_axes = [str(item) for item in (signal.get("semantic_axes") or []) if str(item).strip()]
    categories_text = ", ".join(categories) if categories else "no categories"
    owner_steps_text = ", ".join(owner_steps) if owner_steps else "no owner steps"

    if recommended_action == "fork":
        if signal.get("fork_always_categories") or signal.get("high_fork_categories"):
            summary = (
                "Recommended fork because integrity categories "
                f"({categories_text}) make the current producer artifacts unreliable."
            )
        else:
            summary = (
                "Recommended fork because reviewer findings are not isolated and require a clean recovery branch: "
                f"{owner_steps_text}."
            )
    elif recommended_action == "refresh":
        if signal.get("high_refresh_categories"):
            summary = (
                "Recommended refresh because high-severity structural drift was detected in "
                f"{categories_text}."
            )
        else:
            summary = (
                "Recommended refresh because `needs-fix` findings spread across multiple structural contexts: "
                f"steps={owner_steps_text}; axes={', '.join(semantic_axes) or 'none'}."
            )
    elif recommended_action == "resume":
        summary = (
            "Recommended resume because the reviewer findings remain isolated and do not require a broader "
            f"context reset: {owner_steps_text}."
        )
    else:
        summary = "No follow-up action is required because the reviewer did not detect a blocking or repairable issue."

    return {
        "recommended_action": recommended_action,
        "summary": summary,
        "reasons": reasons,
        "owner_steps": owner_steps,
        "categories": categories,
        "semantic_axes": semantic_axes,
    }


def build_agent_review_recommendations(*, task_id: str, agent_review: dict[str, Any], out_dir: Path) -> list[dict[str, Any]]:
    review_verdict = str(agent_review.get("review_verdict") or "").strip().lower()
    recommended_action = str(agent_review.get("recommended_action") or "").strip().lower()
    if review_verdict not in {"needs-fix", "block"} or recommended_action != "resume":
        return []
    owner_steps = [str(item) for item in (agent_review.get("owner_steps") or []) if str(item).strip()]
    categories = [str(item) for item in (agent_review.get("categories") or []) if str(item).strip()]
    scope = ", ".join(owner_steps or categories or ["review findings"])
    return [
        {
            "id": "agent-review-resume",
            "title": "Resume from the reviewer findings",
            "why": f"The agent review stayed isolated to {scope}; a full context reset is not required yet.",
            "actions": [],
            "commands": [f"py -3 scripts/sc/run_review_pipeline.py --task-id {task_id} --resume"],
            "files": [str(out_dir / "agent-review.json"), str(out_dir / "agent-review.md")],
        }
    ]
