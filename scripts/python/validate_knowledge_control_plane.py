from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


EXPECTED_CONSUMERS = {"repository-session", "chapter4", "chapter5", "chapter6", "review"}
EXPECTED_DOMAINS = {"toolchain", "game-design", "game-runtime", "delivery"}
REQUIRED_EXCLUSION_IDS = {
    "logs",
    "backup",
    "migration",
    "godot-cache",
    "bin",
    "obj",
    "skill-business-evidence",
    "workflow-examples",
    "workflow-templates",
}
FORBIDDEN_RUNTIME_TOKENS = (
    "PhaseA.Platform",
    "HostedContextGate",
    "runtime/phase-a",
    "predecessor_judge_hash",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def _check_record(name: str, completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    record: dict[str, Any] = {"name": name, "returncode": completed.returncode}
    if completed.returncode:
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if stdout:
            record["stdout_tail"] = stdout[-4000:]
        if stderr:
            record["stderr_tail"] = stderr[-4000:]
    return record


def _static_checks(root: Path) -> list[str]:
    issues: list[str] = []
    resource_catalog = root / "docs/knowledge/catalog/knowledge-catalog.json"
    if not resource_catalog.is_file():
        issues.append("missing:docs/knowledge/catalog/knowledge-catalog.json")
    else:
        try:
            payload = _load(resource_catalog)
            entries = payload.get("entries", [])
            ids = [item.get("id") for item in entries]
            if len(ids) != len(set(ids)):
                issues.append("resource-catalog-duplicate-id")
        except (OSError, json.JSONDecodeError):
            issues.append("invalid:docs/knowledge/catalog/knowledge-catalog.json")
    required_files = [
        "docs/adr/ADR-0035-repository-knowledge-control-plane.md",
        "knowledge/README.md",
        "knowledge/contracts/knowledge-locator-request.v1.schema.json",
        "knowledge/contracts/knowledge-locator-result.v1.schema.json",
        "knowledge/contracts/knowledge-consumption-decision.v1.schema.json",
        "knowledge/contracts/knowledge-consumption-decision-set.v1.schema.json",
        "knowledge/contracts/knowledge-context-candidates.v1.schema.json",
        "knowledge/contracts/knowledge-frozen-context.v1.schema.json",
        "knowledge/contracts/knowledge-publication-generation.v1.schema.json",
        "knowledge/contracts/knowledge-index-pointer.v1.schema.json",
        "knowledge/policies/consumer-policies.v1.json",
        "knowledge/policies/source-exclusions.v1.json",
        "scripts/python/_knowledge_catalog_builder.py",
        "scripts/python/_knowledge_locator_core.py",
        "scripts/python/build_knowledge_catalog.py",
        "scripts/python/knowledge_locator.py",
        "scripts/python/evaluate_knowledge_queries.py",
        "scripts/python/prepare_knowledge_context.py",
        "scripts/python/freeze_knowledge_context.py",
        "scripts/python/publish_knowledge_catalog.py",
        "scripts/python/tests/test_knowledge_chapter5_routing.py",
        "scripts/python/tests/test_knowledge_chapter6_routing.py",
        "scripts/python/tests/test_run_single_task_chapter6_lane.py",
        "scripts/python/tests/test_knowledge_review_routing.py",
        "scripts/python/tests/test_knowledge_publication.py",
        "knowledge/evaluation/queries.v1.json",
        "docs/workflows/knowledge-context-shadow.md",
        "docs/workflows/knowledge-context-freeze.md",
        ".agents/skills/maintain-knowledge-base/SKILL.md",
    ]
    for relative in required_files:
        if not (root / relative).is_file():
            issues.append(f"missing:{relative}")

    policies = _load(root / "knowledge/policies/consumer-policies.v1.json")
    consumers = {item.get("consumer") for item in policies.get("policies", []) if isinstance(item, dict)}
    if consumers != EXPECTED_CONSUMERS:
        issues.append("consumer-policy-set-mismatch")
    for policy in policies.get("policies", []):
        if not set(policy.get("domains", [])).issubset(EXPECTED_DOMAINS):
            issues.append(f"invalid-domain:{policy.get('consumer')}")
        if not policy.get("required_context_classes"):
            issues.append(f"missing-required-context-class:{policy.get('consumer')}")
        supplement_classes = policy.get("context_query_supplement_classes", [])
        if isinstance(supplement_classes, list):
            declared = set(policy.get("required_context_classes", [])) | set(
                policy.get("optional_context_classes", [])
            )
            invalid = [value for value in supplement_classes if value not in declared]
            if invalid:
                issues.append(
                    f"invalid-context-supplement-class:{policy.get('consumer')}:{','.join(map(str, invalid))}"
                )

    exclusions = _load(root / "knowledge/policies/source-exclusions.v1.json")
    exclusion_ids = {rule.get("id") for rule in exclusions.get("rules", []) if isinstance(rule, dict)}
    missing_exclusions = sorted(REQUIRED_EXCLUSION_IDS - exclusion_ids)
    if missing_exclusions:
        issues.append("missing-exclusions:" + ",".join(missing_exclusions))

    request_schema = _load(root / "knowledge/contracts/knowledge-locator-request.v1.schema.json")
    enum = set(request_schema.get("properties", {}).get("consumer", {}).get("enum", []))
    if enum != EXPECTED_CONSUMERS:
        issues.append("locator-request-consumer-enum-mismatch")

    routing = (root / "docs/agents/13-rag-sources-and-session-ssot.md").read_text(encoding="utf-8")
    for marker in ("Knowledge Control Plane", "knowledge_locator.py", "direct authoritative source"):
        if marker not in routing:
            issues.append(f"routing-doc-missing:{marker}")

    for relative in (
        ".agents/skills/workflow-chapter4-overlays-contracts-baseline/SKILL.md",
        ".agents/skills/workflow-chapter5-semantics-stabilization/SKILL.md",
        ".agents/skills/workflow-chapter6-single-task-daily-loop/SKILL.md",
    ):
        if (root / relative).is_file():
            skill_text = (root / relative).read_text(encoding="utf-8")
            if "knowledge-context-shadow.md" not in skill_text:
                issues.append(f"shadow-routing-missing:{relative}")

    for relative in (
        "scripts/python/_knowledge_catalog_builder.py",
        "scripts/python/_knowledge_locator_core.py",
        "scripts/python/build_knowledge_catalog.py",
        "scripts/python/knowledge_locator.py",
        "scripts/python/publish_knowledge_catalog.py",
    ):
        text = (root / relative).read_text(encoding="utf-8")
        for token in FORBIDDEN_RUNTIME_TOKENS:
            if token in text:
                issues.append(f"saas-runtime-token:{relative}:{token}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Terminal validation for the newrouge repository Knowledge Control Plane.")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--require-generated", action="store_true")
    args = parser.parse_args()
    root = args.repository_root.resolve()

    issues = _static_checks(root)
    checks: list[dict[str, Any]] = []

    for name, script in (
        ("unit-kernel", "scripts/python/tests/test_knowledge_control_plane.py"),
        ("unit-chapter5-routing", "scripts/python/tests/test_knowledge_chapter5_routing.py"),
        ("unit-chapter6-routing", "scripts/python/tests/test_knowledge_chapter6_routing.py"),
        ("unit-chapter6-orchestrator", "scripts/python/tests/test_run_single_task_chapter6_lane.py"),
        ("unit-review-routing", "scripts/python/tests/test_knowledge_review_routing.py"),
        ("unit-freeze", "scripts/python/tests/test_knowledge_freeze.py"),
        ("unit-publication", "scripts/python/tests/test_knowledge_publication.py"),
    ):
        unit = _run([sys.executable, script], root)
        checks.append(_check_record(name, unit))
        if unit.returncode:
            issues.append(f"{name}-tests-failed")

    if args.require_generated:
        publication = _run([sys.executable, "scripts/python/publish_knowledge_catalog.py", "--check"], root)
        checks.append(_check_record("current-publication", publication))
        if publication.returncode:
            issues.append("current-publication-invalid")
        build = _run([sys.executable, "scripts/python/build_knowledge_catalog.py", "--check"], root)
        checks.append(_check_record("generated-layers", build))
        if build.returncode:
            issues.append("generated-layers-stale")
        evaluation = _run([sys.executable, "scripts/python/evaluate_knowledge_queries.py"], root)
        checks.append(_check_record("repository-query-evaluation", evaluation))
        if evaluation.returncode:
            issues.append("repository-query-evaluation-failed")

    result = {
        "schema_version": "newrouge.knowledge-terminal-validation.v1",
        "status": "passed" if not issues else "failed",
        "require_generated": args.require_generated,
        "checks": checks,
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
