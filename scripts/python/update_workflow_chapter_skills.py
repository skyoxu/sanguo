
#!/usr/bin/env python3
"""Update local workflow chapter skills from a sibling business repo.

The business repo is read-only input. Generated skill files and evidence notes are
written in English with UTF-8 encoding under this template repo.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path
from typing import Any

SKILLS = {
    "workflow-chapter2-repository-bootstrap": {
        "title": "Workflow Chapter 2 Repository Bootstrap",
        "desc": "Run the fixed Chapter 2 repository bootstrap workflow from workflow.md. Use when a new business repo is copied from the template and needs name/path cleanup, entry index rebuild, local hard checks, optional project-health dashboard service, or explicit opt-in OpenAI backend bootstrap.",
        "chapter": "2",
        "purpose": "bootstrap a copied template repository into a clean business repository before task triplets and overlays are created",
        "default": "Clean project identity and indexes first, run repository-level hard checks immediately after that, and start project-health only when an interactive local dashboard is useful.",
        "command": "py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin \"$env:GODOT_BIN\"",
        "evidence": "Chapter 2 is an early bootstrap workflow. Prefer direct repository checks and project-health artifacts over historical task logs; OpenAI backend bootstrap is explicit opt-in only.",
        "steps": [
            "Resolve the target business repo as a sibling of the template repo.",
            "Clean copied template names, paths, workflow names, release names, project paths, and PRD ids.",
            "Rebuild entry indexes in README.md, AGENTS.md, docs/PROJECT_DOCUMENTATION_INDEX.md, and docs/agents/00-index.md.",
            "Run repository-level hard checks immediately after cleanup and index repair.",
            "Optionally start the local project-health service when browser-based health inspection is useful; keep it bound to 127.0.0.1.",
            "Use OpenAI backend bootstrap only when the repo explicitly opts into openai-api transport, and keep it out of default CI until checklist self-checks are clean.",
        ],
    },
    "workflow-chapter3-task-triplet-baseline": {
        "title": "Workflow Chapter 3 Task Triplet Baseline",
        "desc": "Run the fixed Chapter 3 source-ledger, semantic-conservation, task-triplet, and knowledge-refresh workflow from workflow.md.",
        "chapter": "3",
        "purpose": "create or refresh the task triplet from a complete Source Block Ledger and validated semantic projection before Chapter 4/6 depend on it",
        "default": "Build the complete source ledger first, process deterministic semantic batches with explicit per-block accounting, validate semantic conservation, then generate coarse tasks and refresh Workspace attempt/stable topology.",
        "command": "py -3 scripts/python/build_source_ledger.py --mode <init|add> ... && py -3 scripts/python/project_semantics_from_sources.py prepare --max-blocks-per-batch 40 --max-chars-per-batch 24000 && <approved model explicitly reviews every block_result and reconciles batch counts> && py -3 scripts/python/project_semantics_from_sources.py compile && py -3 scripts/python/validate_semantic_conservation.py --stage projection && py -3 scripts/python/normalize_task_intents.py --mode <init|add> && py -3 scripts/python/generate_task_candidates_from_sources.py --mode <init|add> && py -3 scripts/python/enrich_task_candidates.py && py -3 scripts/python/audit_task_candidate_coverage.py && py -3 scripts/python/validate_semantic_conservation.py --stage closure && py -3 scripts/python/compile_task_triplet.py --mode <init|add>",
        "evidence": "Original planning sources remain authority. Source-block accounting and semantic sink coverage are primary; legacy P0/P1 anchors remain downstream packaging evidence only. Capability is optional and Chapter 3 dependency edges are provisional.",
        "steps": [
            "Resolve init versus add and allocate a trigger_run_id. Interactive/multi-turn runs call dev_cli.py refresh-knowledge --source chapter3 --trigger-run-id <run-id> --begin-run before expensive/model-backed work; scripted top-level automation wraps its child workflow with dev_cli.py run-chapter3-guarded so both start and final Attempt refresh are enforced.",
            "Build the complete Source Block Ledger before any requirement-like filter and fail on declared missing sources."
            "Generate the legacy anchor index from the ledger only as downstream packaging evidence.",
            "Prepare deterministic semantic batches bounded by block count and character budget. Oversized single blocks fail rather than truncate.",
            "The approved model must read every batch, explicitly set delivery_potential, fill atoms or a disposition for every block_result, and reconcile output_accounted_count; requirement_like_hint is diagnostic only.",
            "Compile Semantic Projection A and run the projection conservation gate; stop on silent loss, invalid refs, source drift, or unresolved delivery-potential semantics.",
            "Normalize implementation-shaped task intents from active validated semantics. When Capability is absent, use source heading before source-path fallback and CJK-aware heading/statement focus for stable titles. Preserve all semantic_refs/capability_refs; emit shared multi-Capability grouping only as advisory shadow evidence. Mark generated dependencies provisional.",
            "Audit intent quality, generate candidates, and enrich them with repository evidence plus implementation-overlap/file-churn advisory signals.",
            "Audit semantic sink coverage; retain the old P0/P1 coverage only as a Source-Block-bridged packaging gate.",
            "Run the closure conservation gate; active delivery Requirements require Task/non-Task sinks and task complexity must be at most 7.",
            "Compile and review a task-triplet patch, write only after review, rebuild tasks.json, backfill semantic review tier, then run attest_chapter3_triplet_baseline.py so validator results are bound to the current triplet hashes.",
            "At every Chapter 3 run end, call dev_cli.py refresh-knowledge --source chapter3 --trigger-run-id <run-id> --refresh-local. Failed runs update Last Attempt only; passed closure may update Latest Successful only when semantic closure, task coverage, and triplet attestation all verify.",
            "Only passed closure may write planning topology artifacts. KCP publication remains explicit, clean trusted-ref/main-only, and never a recovery side effect.",
            "Use run_chapter3_regression_check.py as read-only evidence and report full Source Block counts against legacy anchor counts.",
        ],
    },
        "workflow-chapter4-overlays-contracts-baseline": {
        "title": "Workflow Chapter 4 Overlays And Contracts Baseline",
        "desc": "Run the fixed Chapter 4 overlays and contracts baseline workflow from workflow.md. Use when a business repo needs overlay skeleton generation after a valid triplet baseline, overlay refs freezing, contract skeleton creation or adjustment, contract baseline validation, or idempotent overlay/contract recovery before Chapter 5 and Chapter 6.",
        "chapter": "4",
        "purpose": "establish overlay skeletons, freeze task overlay refs, and validate Game.Core contract baselines after the task triplet is valid",
        "default": "Enter Chapter 4 only after the Chapter 3 triplet baseline is clean. Use batch dry-run, batch simulate, outlier single-page repair, then limited apply; never start with full apply.",
        "command": "py -3 scripts/python/sync_task_overlay_refs.py --prd-id <PRD-ID> --write && py -3 scripts/python/validate_overlay_execution.py --prd-id <PRD-ID> --strict-refs",
        "evidence": "Chapter 4 depends on real overlay and contract files. Use business-repo overlays and Game.Core/Contracts as structural evidence, but keep workflow.md as the execution policy source.",
        "steps": [
            "Confirm the Chapter 3.9 triplet baseline is clean before generating overlays.",
            "Generate overlay skeletons through batch dry-run, batch simulate, single-page repair for outliers, and limited apply.",
            "Do not perform full apply in the first overlay pass, and do not mix acceptance rewrites into overlay generation.",
            "Freeze overlay refs with sync_task_overlay_refs and validate_overlay_execution, then rerun task refs and triplet validators.",
            "Create or adjust contract skeletons under Game.Core/Contracts only, using the workflow contract templates.",
            "Validate contract baseline with validate_contracts, check_domain_contracts, and Game.Core.Tests before leaving Chapter 4.",
        ],
    },
    "workflow-chapter5-semantics-stabilization": {
        "title": "Workflow Chapter 5 Semantics Stabilization",
        "desc": "Run the fixed Chapter 5 semantic reconciliation workflow from workflow.md. Use when a business repo needs Independent Extraction B, global orphan/omission audit, bidirectional Requirement/Acceptance validation, dependency/overlap stabilization, readiness gating, Knowledge refresh, or the legacy lightweight acceptance lane before Chapter 6.",
        "chapter": "5",
        "purpose": "stabilize task semantics before daily task execution enters the Chapter 6 loop",
        "default": "Build or reuse one revision-bound Independent Extraction B snapshot for the complete authoritative source scope, then run task-scoped reconciliation. Keep the existing lightweight lane for acceptance authoring and only escalate batch instability when repeated failure evidence warrants it.",
        "command": "py -3 scripts/python/chapter5_semantic_reconciliation.py prepare && <independent review of every block> && py -3 scripts/python/chapter5_semantic_reconciliation.py compile && py -3 scripts/python/chapter5_semantic_reconciliation.py reconcile --task-id <id> --decisions <decisions.json>",
        "evidence": "Chapter 5 closure requires complete source scope, an independent Extraction B snapshot, global orphan/omission audit, task/acceptance reconciliation, dependency and overlap decisions, and READY or policy-allowed CONCERNS. Task refs may locate implementation context but never define the semantic audit scope.",
        "steps": [
            "Resolve the target business repo and verify the Chapter 3 source manifest, Source Block Ledger, semantic projection, and Chapter 4 overlay/contract backlinks.",
            "Prepare Independent Extraction B from the complete authoritative source scope. Reuse the snapshot only when source_manifest_sha, source_block_ledger_sha, parser_revision, and extractor_revision match exactly.",
            "Review every Extraction B block directly from raw authority and compile the snapshot before any task-scoped acceptance stabilization.",
            "Run global orphan/omission reconciliation before task-scoped checks; missing_in_ch3/orphan_delivery_semantic must not depend on task.semantic_refs. Lexical similarity is diagnostic only; semantic match verdicts require explicit status plus rationale.",
            "Use the existing lightweight lane to stabilize acceptance, bind every acceptance to Requirement/ADR/Contract plus test refs, and explicitly review every relevant ADR/Contract as compatible/conflict/out_of_scope with rationale before rerunning reconciliation.",
            "Resolve provisional dependencies with producer/consumer/contract/schema/state/asset-scene evidence and record overlap decisions with rationale.",
            "Require READY or policy-allowed CONCERNS before Chapter 6; BLOCKED must stop Chapter 6 and Review.",
            "At Chapter 5 run end call the registered refresh-knowledge hook so Last Attempt always records findings and only a current full input fingerprint may advance workspace-latest-stabilized; guarded scripted runs invoke this final refresh automatically.",
        ],
    },
    "workflow-chapter6-single-task-daily-loop": {
        "title": "Workflow Chapter 6 Single Task Daily Loop",
        "desc": "Run the fixed Chapter 6 single-task daily loop from workflow.md. Use when a business repo needs resume-task, chapter6-route, TDD red/green/refactor, 6.7 review pipeline, 6.8 Needs Fix cleanup, 6.9 repository validation, stop-loss, rerun guard, or idempotent recovery from Chapter 6 logs.",
        "chapter": "6",
        "purpose": "drive one task through implementation, review, repair, and repository validation",
        "default": "Use the top-level Chapter 6 orchestrator unless active-task or chapter6-route already recommends a narrower recovery command.",
        "command": "py -3 scripts/python/dev_cli.py run-single-task-chapter6 --task-id <id> --godot-bin \\\"$env:GODOT_BIN\\\" --delivery-profile <profile>",
        "evidence": "Chapter 6 has dense business-repo logs. Always read active-task, latest.json, summary.json, repair-guide, agent-review, and run-events before paying for another 6.7 or 6.8.",
        "steps": [
            "Read active-task first when a task id exists.",
            "Run resume-task and chapter6-route recommendation-only before expensive reruns.",
            "Use the TDD order 6.3, 6.4, 6.5, 6.6 before 6.7 unless recovery evidence says otherwise.",
            "Run 6.7 only when deterministic evidence is stale or required by changed implementation, tests, contracts, scripts, or runtime assets.",
            "Run 6.8 only when route evidence says Needs Fix cleanup is the right lane.",
            "Run 6.9 repository validation before commit or PR closure using run-local-hard-checks --skip-project-health so Chapter 6 never refreshes Project Health or global Knowledge as a side effect.",
        ],
    },
    "workflow-chapter7-ui-wiring-closure": {
        "title": "Workflow Chapter 7 UI Wiring Closure",
        "desc": "Run the fixed Chapter 7 UI wiring closure workflow from workflow.md. Use when a business repo needs UI/GDD closure after Chapter 6, chapter7 profile overrides, UI wiring GDD generation, candidate sidecars, artifact manifests, hard gates, task generation, or idempotent Chapter 7 readiness checks.",
        "chapter": "7",
        "purpose": "convert completed domain and gameplay capabilities into player-facing UI wiring and governed Chapter 7 artifacts",
        "default": "Start with self-check, then write-doc, then create-tasks only after the candidate sidecar and artifact manifest are valid.",
        "command": "py -3 scripts/python/dev_cli.py run-chapter7-ui-wiring --delivery-profile <profile> --self-check",
        "evidence": "Chapter 7 currently has little or no business-repo runtime history. Use workflow.md, chapter7-profile.json, the profile guide, and generated manifests as the stable source until real logs exist.",
        "steps": [
            "Confirm Chapter 6 has no unrecorded P0/P1 Needs Fix.",
            "Confirm real task triplet files exist before treating the Chapter 7 gate as complete.",
            "Use a Chapter 7 profile override for policy-level business repo differences instead of forking scripts.",
            "Run self-check before write-doc.",
            "Validate UI GDD, candidates, artifact manifest, and hard gate outputs before task creation.",
            "Stop when backlog-gap evidence says candidate tasks are already covered.",
        ],
    },
}

KEYWORDS = {
    "chapter2": ["repository bootstrap", "project-health", "run-local-hard-checks", "serve-project-health", "openai-api", "template-bootstrap"],
    "chapter3": ["task triplet", "triplet", "task_links_validate", "check_tasks_all_refs", "validate_task_master_triplet", "build_taskmaster_tasks", "semantic_review_tier"],
    "chapter4": ["overlay", "overlays", "contract", "contracts", "llm_generate_overlays_batch", "llm_generate_overlays_from_prd", "sync_task_overlay_refs", "validate_overlay_execution", "validate_contracts", "check_domain_contracts"],
    "chapter5": ["phase 3", "semantic", "semantics", "independent extraction", "extraction b", "reconciliation", "readiness", "acceptance extract", "batch instability", "extract_family"],
    "chapter6": ["chapter6", "chapter 6", "6.7", "6.8", "run_review_pipeline", "llm_review_needs_fix", "chapter6-route", "artifact_integrity", "planned_only", "needs fix", "rerun_guard"],
    "chapter7": ["chapter7", "chapter 7", "ui wiring", "chapter7-profile", "run-chapter7-ui-wiring", "ui-gdd-flow", "artifact-manifest"],
}

AREAS = ["execution-plans", "decision-logs", "logs/ci/active-tasks"]


def read_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def count_keyword_files(repo: Path) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for area in AREAS:
        base = repo / area
        counts = {k: 0 for k in KEYWORDS}
        if base.exists():
            files = [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".json", ".jsonl", ".txt"}]
            for path in files[:12000]:
                text = path.read_text(encoding="utf-8", errors="replace").lower()
                for chapter, words in KEYWORDS.items():
                    if any(w in text for w in words):
                        counts[chapter] += 1
        result[area] = counts
    return result


def counter_lines(counter: collections.Counter[str], limit: int = 10) -> list[str]:
    if not counter:
        return ["- None observed."]
    return [f"- `{name}`: {count}" for name, count in counter.most_common(limit)]


def active_task_summary(repo: Path) -> dict[str, Any]:
    out = {
        "count": 0,
        "actions": collections.Counter(),
        "blocked": collections.Counter(),
        "reasons": collections.Counter(),
        "run_types": collections.Counter(),
        "diagnostics": collections.Counter(),
        "forbidden": 0,
        "skip67": 0,
        "go68": 0,
        "samples": [],
    }
    base = repo / "logs" / "ci" / "active-tasks"
    if not base.exists():
        return out
    for path in sorted(base.glob("*.active.json")):
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        out["count"] += 1
        action = str(data.get("recommended_action") or "")
        if action:
            out["actions"][action] += 1
        hints = data.get("chapter6_hints") if isinstance(data.get("chapter6_hints"), dict) else {}
        blocked = str(hints.get("blocked_by") or "")
        if blocked:
            out["blocked"][blocked] += 1
        if hints.get("can_skip_6_7") is True:
            out["skip67"] += 1
        if hints.get("can_go_to_6_8") is True:
            out["go68"] += 1
        latest = data.get("latest_summary_signals") if isinstance(data.get("latest_summary_signals"), dict) else {}
        reason = str(latest.get("reason") or data.get("reason") or "")
        run_type = str(latest.get("run_type") or data.get("run_type") or "")
        if reason:
            out["reasons"][reason] += 1
        if run_type:
            out["run_types"][run_type] += 1
        for key in latest.get("diagnostics_keys") or []:
            out["diagnostics"][str(key)] += 1
        forbidden = data.get("forbidden_commands") or []
        if isinstance(forbidden, list) and forbidden:
            out["forbidden"] += 1
        if len(out["samples"]) < 8:
            out["samples"].append({
                "task": str(data.get("task_id") or re.sub(r"\D+", "", path.stem) or path.stem),
                "action": action,
                "blocked": blocked,
                "forbidden": len(forbidden) if isinstance(forbidden, list) else 0,
                "command": str(data.get("recommended_command") or ""),
            })
    return out


def latest_summary(repo: Path) -> dict[str, Any]:
    out = {"latest": 0, "pipeline": 0, "status": collections.Counter(), "reason": collections.Counter(), "run_type": collections.Counter(), "reuse": collections.Counter(), "diagnostics": collections.Counter(), "route": collections.Counter()}
    ci = repo / "logs" / "ci"
    if not ci.exists():
        return out
    for path in sorted(ci.rglob("latest.json")):
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        out["latest"] += 1
        for src, key in [("status", "status"), ("reason", "reason"), ("run_type", "run_type"), ("reuse", "reuse_mode")]:
            val = str(data.get(key) or "")
            if val:
                out[src][val] += 1
        diag = data.get("diagnostics")
        if isinstance(diag, dict):
            for key in diag:
                out["diagnostics"][str(key)] += 1
    for path in sorted(ci.rglob("summary.json")):
        r = rel(path, repo)
        if "sc-review-pipeline-task-" not in r and "llm-review" not in r:
            continue
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        out["pipeline"] += 1
        route = data.get("route_preflight")
        if isinstance(route, dict):
            lane = str(route.get("preferred_lane") or route.get("recommended_action") or "")
            if lane:
                out["route"][lane] += 1
        diag = data.get("diagnostics")
        if isinstance(diag, dict):
            for key in diag:
                out["diagnostics"][str(key)] += 1
    return out


def chapter7_files(repo: Path) -> list[str]:
    pats = ["logs/ci/**/chapter7-ui-wiring/**", "logs/ci/**/chapter7-ui-wiring-inputs/**", "docs/gdd/ui-gdd-flow.md", "docs/gdd/ui-gdd-flow.candidates.json", "docs/workflows/chapter7-profile.json"]
    files: list[str] = []
    for pat in pats:
        for path in repo.glob(pat):
            if path.is_file():
                files.append(rel(path, repo))
    return sorted(set(files))[:30]


def overlay_contract_summary(repo: Path) -> list[str]:
    lines: list[str] = []
    overlay_root = repo / "docs" / "architecture" / "overlays"
    contract_root = repo / "Game.Core" / "Contracts"
    overlay_files = [p for p in overlay_root.rglob("*") if p.is_file()] if overlay_root.exists() else []
    contract_files = [p for p in contract_root.rglob("*") if p.is_file()] if contract_root.exists() else []
    cs_contracts = [p for p in contract_files if p.suffix.lower() == ".cs"]
    uid_contracts = [p for p in contract_files if p.suffix.lower() == ".uid"]
    manifest_files = [p for p in overlay_files if p.name == "overlay-manifest.json"]
    acceptance_files = [p for p in overlay_files if p.name.upper() == "ACCEPTANCE_CHECKLIST.MD"]
    index_files = [p for p in overlay_files if p.name == "_index.md"]
    lines.append(f"- `docs/architecture/overlays`: exists={overlay_root.exists()}, file_count={len(overlay_files)}")
    lines.append(f"- Overlay manifests: {len(manifest_files)}")
    lines.append(f"- Overlay acceptance checklists: {len(acceptance_files)}")
    lines.append(f"- Overlay indexes: {len(index_files)}")
    for sample in overlay_files[:12]:
        lines.append(f"  - `{rel(sample, repo)}`")
    lines.append(f"- `Game.Core/Contracts`: exists={contract_root.exists()}, file_count={len(contract_files)}, cs_files={len(cs_contracts)}, uid_files={len(uid_contracts)}")
    for sample in cs_contracts[:12]:
        lines.append(f"  - `{rel(sample, repo)}`")
    template_paths = [
        "docs/workflows/contracts-template-v1.md",
        "docs/workflows/templates/contracts-event-template-v1.md",
        "docs/workflows/templates/contracts-dto-template-v1.md",
        "docs/workflows/templates/contracts-interface-template-v1.md",
    ]
    for template in template_paths:
        lines.append(f"- `{template}`: exists={(repo / template).exists()}")
    return lines


def task_triplet_summary(repo: Path) -> list[str]:
    files = [
        ".taskmaster/tasks/tasks.json",
        ".taskmaster/tasks/tasks_back.json",
        ".taskmaster/tasks/tasks_gameplay.json",
    ]
    lines: list[str] = []
    for rel_path in files:
        path = repo / rel_path
        if not path.exists():
            lines.append(f"- `{rel_path}`: missing")
            continue
        size = path.stat().st_size
        data = read_json(path)
        shape = "unknown"
        count = "unknown"
        if isinstance(data, dict):
            if isinstance(data.get("master"), dict) and isinstance(data["master"].get("tasks"), list):
                shape = "dict.master.tasks"
                count = str(len(data["master"]["tasks"]))
            elif isinstance(data.get("tasks"), list):
                shape = "dict.tasks"
                count = str(len(data["tasks"]))
            else:
                shape = "dict"
        elif isinstance(data, list):
            shape = "list"
            count = str(len(data))
        lines.append(f"- `{rel_path}`: exists, shape=`{shape}`, task_count={count}, bytes={size}")
    return lines


def evidence_markdown(repo: Path, repo_name: str) -> str:
    density = count_keyword_files(repo)
    active = active_task_summary(repo)
    latest = latest_summary(repo)
    c7 = chapter7_files(repo)
    lines = [
        f"# Business Repo Evidence: {repo_name}",
        "",
        "Generated by `scripts/python/update_workflow_chapter_skills.py`. Do not edit by hand.",
        "",
        "## Repository",
        "",
        f"- Path: `{repo}`",
        f"- Exists: `{repo.exists()}`",
        "",
        "## Chapter Evidence Density",
        "",
    ]
    for area, counts in density.items():
        lines += [f"### `{area}`", ""]
        for chapter in ["chapter2", "chapter3", "chapter4", "chapter5", "chapter6", "chapter7"]:
            lines.append(f"- `{chapter}` keyword-bearing files: {counts.get(chapter, 0)}")
        lines.append("")
    lines += [
        "## Chapter 3 Task Triplet Evidence",
        "",
    ]
    lines += task_triplet_summary(repo)
    lines += [
        "",
        "### Chapter 3 Operational Conclusions",
        "",
        "- Do not assume the three triplet files have identical item counts; validate their mapping instead.",
        "- For a new project, build or confirm the authoritative triplet before Chapter 4 overlays.",
        "- For added tasks, rerun the Chapter 3.8 baseline before overlay sync or Chapter 6 execution.",
        "- Backfill and validate semantic review tier after task additions unless the repo already has a clean conservative baseline.",
        "",
        "## Chapter 4 Overlay And Contract Evidence",
        "",
    ]
    lines += overlay_contract_summary(repo)
    lines += [
        "",
        "### Chapter 4 Operational Conclusions",
        "",
        "- Do not enter overlay generation unless the Chapter 3.9 triplet baseline is clean.",
        "- Use dry-run and simulate before apply; repair outliers before limited apply.",
        "- Freeze overlay refs after apply and rerun refs/triplet validators.",
        "- Keep contracts under Game.Core/Contracts and validate them before Chapter 5 or Chapter 6 depends on them.",
        "",
        "## Chapter 5 Notes",
        "",
        "- Treat sparse Chapter 5 evidence as expected unless keyword counts show repeated semantic drift.",
        "- Do not add Chapter 5 complexity when the observed bottleneck is still acceptance extraction or triplet quality.",
        "",
        "## Chapter 6 Active Task Evidence",
        "",
        f"- Active task JSON files: {active['count']}",
        f"- Active tasks with forbidden commands: {active['forbidden']}",
        f"- Active tasks where `can_skip_6_7` is true: {active['skip67']}",
        f"- Active tasks where `can_go_to_6_8` is true: {active['go68']}",
        "",
        "### Recommended Actions",
        "",
    ]
    lines += counter_lines(active["actions"])
    lines += ["", "### Blockers", ""] + counter_lines(active["blocked"])
    lines += ["", "### Latest Reasons", ""] + counter_lines(active["reasons"])
    lines += ["", "### Run Types", ""] + counter_lines(active["run_types"])
    lines += ["", "### Diagnostics", ""] + counter_lines(active["diagnostics"])
    lines += ["", "### Sample Active Tasks", ""]
    if active["samples"]:
        for item in active["samples"]:
            lines.append(f"- Task `{item['task']}`: action=`{item['action']}`, blocked_by=`{item['blocked']}`, forbidden_commands={item['forbidden']}, command=`{item['command']}`")
    else:
        lines.append("- None observed.")
    lines += [
        "",
        "## Chapter 6 Pipeline Evidence",
        "",
        f"- `latest.json` files: {latest['latest']}",
        f"- Pipeline or LLM review summaries: {latest['pipeline']}",
        "",
        "### Latest Status",
        "",
    ]
    lines += counter_lines(latest["status"])
    lines += ["", "### Latest Reason", ""] + counter_lines(latest["reason"])
    lines += ["", "### Latest Run Type", ""] + counter_lines(latest["run_type"])
    lines += ["", "### Route Preflight", ""] + counter_lines(latest["route"])
    lines += ["", "### Summary Diagnostics", ""] + counter_lines(latest["diagnostics"])
    lines += [
        "",
        "## Chapter 6 Operational Conclusions",
        "",
        "- Read active-task and route evidence before starting another full 6.7 run.",
        "- Obey `forbidden_commands`; do not manually rerun blocked commands.",
        "- Prefer 6.8 only when route evidence says the next lane is Needs Fix cleanup.",
        "- Treat planned-only and artifact-integrity signals as evidence-only until a real producer run is recovered or recreated.",
        "- Treat repeated deterministic failures as root-cause work, not timeout tuning.",
        "",
        "## Chapter 7 Notes",
        "",
        f"- Chapter 7 files observed: {len(c7)}",
    ]
    if c7:
        lines += [f"- `{p}`" for p in c7]
    else:
        lines.append("- No Chapter 7 runtime artifacts were found. Use workflow.md, profile docs, and future manifests as the source of truth until real runs exist.")
    lines.append("")
    return "\n".join(lines)


def workflow_chapter_summary(template: Path, chapter: str) -> str:
    workflow_path = template / "workflow.md"
    raw = workflow_path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    start_prefix = f"## {chapter}."
    next_prefix = f"## {int(chapter) + 1}."
    start = None
    end = len(lines)
    for idx, line in enumerate(lines):
        if line.startswith(start_prefix):
            start = idx
            break
    if start is None:
        return f"# Workflow Source Summary: Chapter {chapter}\n\n- Source: `workflow.md`\n- Chapter heading: not found.\n"
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith(next_prefix):
            end = idx
            break
    headings = []
    commands = []
    artifacts = []
    for line in lines[start:end]:
        stripped = line.strip()
        if stripped.startswith("#"):
            normalized = stripped.lstrip("#").strip()
            headings.append(normalized)
        if "py -3 " in stripped or "run_review_pipeline.py" in stripped or "llm_review_needs_fix" in stripped:
            commands.append(stripped.strip("`"))
        for token in ["summary.json", "latest.json", "active.md", "agent-review", "repair-guide", "artifact-manifest", "ui-gdd-flow", "chapter7-profile"]:
            if token in stripped:
                artifacts.append(stripped)
                break
    title_map = {
        "2": "Repository Bootstrap",
        "3": "Phase 1: Task Triplet Initialization",
        "4": "Phase 2: Overlays And Contracts Baseline",
        "5": "Phase 3: Conditional Semantics Stabilization",
        "6": "Phase 4: Single Task Daily Loop",
        "7": "Phase 5: Chapter 7 UI Wiring Closure",
    }
    out = [
        f"# Workflow Source Summary: Chapter {chapter}",
        "",
        "Generated from the template repo `workflow.md` by `scripts/python/update_workflow_chapter_skills.py`.",
        "",
        f"- Canonical English name: {title_map.get(chapter, 'Unknown')}",
        f"- Source line span: {start + 1}-{end}",
        f"- Heading count: {len(headings)}",
        f"- Command-like line count: {len(commands)}",
        f"- Artifact/reference line count: {len(artifacts)}",
        "",
        "## Headings",
        "",
    ]
    # Keep the source summary English-only: preserve numeric section ids and map known labels.
    heading_aliases = {
        "2.1": "2.1 Clean name and path residue",
        "2.2": "2.2 Rebuild entry indexes",
        "2.3": "2.3 Run repository-level hard checks immediately",
        "2.4": "2.4 Optional local project-health page service",
        "2.5": "2.5 Optional OpenAI backend bootstrap",
        "2.": "2. Repository Bootstrap",
        "3.0": "3.0 Choose the Chapter 3 route first",
        "3.1": "3.1 Prepare planning inputs",
        "3.2": "3.2 Extract requirement anchors",
        "3.3": "3.3 Normalize task intents",
        "3.4": "3.4 Generate task candidates",
        "3.5": "3.5 Enrich task candidates",
        "3.6": "3.6 Audit the coverage matrix",
        "3.7": "3.7 Compile a task triplet patch",
        "3.8": "3.8 Build the authoritative triplet",
        "3.9": "3.9 Validate the triplet baseline",
        "3.10": "3.10 Standardize semantic review tier early",
        "3.11": "3.11 Chapter 3 stop-loss",
        "3.12": "3.12 Optional regression check",
        "3.": "3. Phase 1: Task Triplet Initialization",
        "4.1": "4.1 Generate overlay skeletons only after the triplet is valid",
        "4.2": "4.2 Freeze overlay refs after apply",
        "4.3": "4.3 Create or adjust contract skeletons",
        "4.4": "4.4 Solidify contract baseline",
        "4.": "4. Phase 2: Overlays And Contracts Baseline",
        "5. Phase 3": "5. Phase 3: Conditional Semantics Stabilization",
        "5.0": "5.0 Independent Extraction B / Global Reconciliation / Readiness Gate",
        "5.1": "5.1 Single-task lightweight lane",
        "5.2": "5.2 Batch instability lane",
        "6. Phase 4": "6. Phase 4: Single Task Daily Loop",
        "6.0.1": "6.0.1 Chapter 6 Knowledge no-refresh hard boundary",
        "6.0": "6.0 Choose the Chapter 6 entrypoint first",
        "6.1": "6.1 Recover state first",
        "6.2": "6.2 Create recovery documents only when useful",
        "6.3": "6.3 TDD preflight decision",
        "6.4": "6.4 Red stage",
        "6.5": "6.5 Green stage",
        "6.6": "6.6 Refactor stage",
        "6.7": "6.7 Unified task-level review pipeline",
        "6.8": "6.8 Clean up Needs Fix",
        "6.9": "6.9 Repository-level validation before commit",
        "6.10": "6.10 PR incremental quick path",
        "6.11": "6.11 Fast mode fastest template",
        "7. Phase 5": "7. Phase 5: Chapter 7 UI Wiring Closure",
        "7.1": "7.1 Entry conditions",
        "7.2": "7.2 Top-level orchestrator",
        "7.3": "7.3 Input collection rules",
        "7.4": "7.4 UI/GDD flow design rules",
        "7.5": "7.5 Hard gate",
        "7.6": "7.6 Task generation rules",
        "7.7": "7.7 Stop and inspect",
    }
    for heading in headings:
        alias = None
        for prefix, mapped in sorted(heading_aliases.items(), key=lambda item: len(item[0]), reverse=True):
            if heading.startswith(prefix):
                alias = mapped
                break
        out.append(f"- {alias or heading.encode('ascii', errors='ignore').decode('ascii').strip() or 'Non-English source heading'}")
    out += ["", "## Command And Artifact Signals", ""]
    seen = set()
    for line in commands + artifacts:
        ascii_line = line.encode("ascii", errors="ignore").decode("ascii").strip()
        if ascii_line.startswith("- "):
            ascii_line = ascii_line[2:].strip()
        if ascii_line.startswith("`") and ascii_line.endswith("`"):
            ascii_line = ascii_line[1:-1].strip()
        if not ascii_line or ascii_line in seen:
            continue
        seen.add(ascii_line)
        out.append(f"- `{ascii_line[:220]}`")
        if len(seen) >= 40:
            break
    if not seen:
        out.append("- None observed.")
    out.append("")
    return "\n".join(out)


def skill_markdown(name: str, cfg: dict[str, Any]) -> str:
    steps = "\n".join(f"{i}. {step}" for i, step in enumerate(cfg["steps"], 1))
    if cfg["chapter"] == "2":
        required_reading = (
            "1. Read the relevant Chapter 2 section in the template repo `workflow.md`.\n"
            "2. Inspect the target repository state directly; Chapter 2 does not use historical business-repo evidence.\n"
            "3. Refresh this skill with `py -3 scripts/python/update_workflow_chapter_skills.py <repo>` when `workflow.md` changes."
        )
    elif cfg["chapter"] in {"4", "5", "6"}:
        required_reading = (
            f"1. Read the relevant Chapter {cfg['chapter']} section in the template repo `workflow.md`.\n"
            "2. Read `docs/workflows/knowledge-context-shadow.md` before using optional Knowledge routing/preflight.\n"
            "3. Optionally read `references/business-repos/<repo>.md` only as empirical validation evidence when the target business repo has a generated reference.\n"
            "4. If that optional evidence file is missing or stale, run `py -3 scripts/python/update_workflow_chapter_skills.py <repo>` from the template repo."
        )
    else:
        required_reading = (
            f"1. Read the relevant Chapter {cfg['chapter']} section in the template repo `workflow.md`.\n"
            "2. Optionally read `references/business-repos/<repo>.md` only as empirical validation evidence when the target business repo has a generated reference.\n"
            "3. If that optional evidence file is missing or stale, run `py -3 scripts/python/update_workflow_chapter_skills.py <repo>` from the template repo."
        )

    operating_extra = ""
    stop_loss_extra = ""
    if cfg["chapter"] == "4":
        operating_extra = (
            "- During Knowledge Control Plane migration, Locator candidates are shadow-only and cannot satisfy architecture/semantic obligations without direct-source reread and consumer judgment.\n"
        )
    elif cfg["chapter"] == "5":
        operating_extra = (
            "- During Knowledge Control Plane migration, Locator candidates are shadow-only. Complete source scope comes from the authoritative manifest/Ledger A, never task refs.\n"
            "- Chapter 5 is a registered closure producer: every run may update Last Attempt, but only READY or policy-allowed CONCERNS may advance Latest Stabilized.\n"
        )
        stop_loss_extra = (
            "- A Locator candidate cannot be re-read/hash-verified from repository authority; reject it and use the direct-source path.\n"
            "- Extraction B source scope is incomplete, stale, or task-selected; stop before task-local reconciliation.\n"
        )
    elif cfg["chapter"] == "6":
        operating_extra = (
            "- Chapter 6 may query bounded Knowledge only before RED; a frozen context must not silently widen during RED/GREEN/REFACTOR.\n"
            "- Chapter 6 is not a global Knowledge producer. Execution, recovery, 6.7, 6.8, and 6.9 must not refresh Project Health, rebuild catalogs, or publish KCP as side effects.\n"
        )
        stop_loss_extra = (
            "- A task scope change would require a new knowledge query after RED; stop and create a new explicit preflight/context revision instead of widening context invisibly.\n"
        )
    return f"""---
name: {name}
description: {cfg["desc"]}
---

# {cfg["title"]}

## Role

Operate Chapter {cfg["chapter"]} from `workflow.md` idempotently for a business repository that is a sibling of the template repository.

## Operating Contract

- Treat `workflow.md` as the normative workflow source.
- Treat business-repo logs as empirical evidence, not policy overrides.
- Use Python with UTF-8 for documentation reads and writes.
- Keep generated code, scripts, tests, comments, and log messages in English.
- Do not modify the business repo unless the user explicitly asks for that change.
- Do not rerun expensive steps before reading existing recovery artifacts.
{operating_extra}
## Repository Layout

Template and business repositories are siblings under one parent directory, for example `<parent>/godotgame`, `<parent>/<business-repo-a>`, and `<parent>/<business-repo-b>`.

## Purpose

Use this skill to {cfg["purpose"]}.

## Default Lane

{cfg["default"]}

## Primary Command Or Action

`{cfg["command"]}`

## Evidence Rule

{cfg["evidence"]}

## Required Reading

{required_reading}

## Idempotent Procedure

{steps}

## Stop-Loss Signals

- Existing `forbidden_commands` blocks the command about to be run.
- `artifact_integrity`, `planned_only_incomplete`, or planned-only run type appears in recovery evidence.
- Route evidence recommends inspect-first, record-residual, fix-deterministic, repo-noise-stop, or pause.
- The same deterministic failure fingerprint appears repeatedly.
- The next action would duplicate work already covered by task, overlay, candidate, or manifest evidence.
{stop_loss_extra}
## Business Evidence References

Generated evidence may live under `references/business-repos/<repo>.md`. These files are optional regression evidence from known business repositories; they must not define production generation rules.

## Maintenance

Refresh optional evidence after new business-repo logs are generated:

```powershell
py -3 scripts/python/update_workflow_chapter_skills.py <business-repo>
py -3 scripts/python/update_workflow_chapter_skills.py <business-repo-a>,<business-repo-b>
```
"""


def resolve_repo(template: Path, value: str) -> tuple[str, Path]:
    raw = Path(value)
    if raw.exists():
        path = raw.resolve()
        return path.name, path
    return value, (template.parent / value).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("business_repo", help="Business repo name/path, or a comma-separated list such as repo_a,repo_b.")
    parser.add_argument("--template-root", default=".")
    args = parser.parse_args()
    template = Path(args.template_root).resolve()
    if not (template / "workflow.md").exists():
        raise SystemExit(f"workflow.md not found under {template}")
    repo_values = [part.strip() for part in args.business_repo.split(",") if part.strip()]
    if not repo_values:
        raise SystemExit("No business repo specified")

    resolved: list[tuple[str, Path]] = []
    for value in repo_values:
        repo_name, repo = resolve_repo(template, value)
        if not repo.exists():
            raise SystemExit(f"Business repo not found: {repo}")
        resolved.append((repo_name, repo))

    for name, cfg in SKILLS.items():
        root = template / ".agents" / "skills" / name
        ref = root / "references" / "business-repos"
        ref.mkdir(parents=True, exist_ok=True)
        (root / "SKILL.md").write_text(skill_markdown(name, cfg), encoding="utf-8", newline="\n")
        (root / "references").mkdir(parents=True, exist_ok=True)
        (root / "references" / "workflow-source.md").write_text(workflow_chapter_summary(template, cfg["chapter"]), encoding="utf-8", newline="\n")
        if cfg["chapter"] == "2":
            continue
        for repo_name, repo in resolved:
            evidence = evidence_markdown(repo, repo_name)
            (ref / f"{repo_name}.md").write_text(evidence, encoding="utf-8", newline="\n")

    repo_list = ", ".join(f"{repo_name}:{repo}" for repo_name, repo in resolved)
    print(f"Updated {len(SKILLS)} workflow chapter skills from {len(resolved)} business repo(s): {repo_list}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
