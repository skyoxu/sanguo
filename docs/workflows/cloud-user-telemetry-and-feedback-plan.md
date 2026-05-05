# Cloud User Telemetry And Feedback Plan

This document describes which usage data is most valuable once the project moves to the cloud and starts serving real users.

The goal is not generic analytics. The goal is to capture the smallest set of structured signals that can directly improve:

- workflow speed
- workflow correctness
- stop-loss quality
- recovery quality
- prototype onboarding
- long-term template evolution

## Core Principle

The most valuable data is not raw chat content. It is structured workflow evidence about:

- where users enter
- where they stall
- which stop-loss rules trigger
- which recommendations they follow
- which paths converge
- which paths waste time

This project should prefer workflow telemetry over broad product analytics.

## Highest-Value Data Categories

## 1. Workflow Execution Data

This is the highest-value category because it directly shows where the harness should be improved.

Capture:

- which top-level entrypoint the user started from
- which task mode was used: prototype, Chapter 5, Chapter 6, repo scan, recovery
- which major steps ran
- which major steps were skipped
- step durations
- step outcome: `ok | fail | blocked | skipped`
- failure class: `timeout | deterministic_fail | llm_needs_fix | artifact_integrity | planned_only | approval_pending | repo_noise | unknown`
- number of reruns before convergence
- whether the final task converged or was abandoned

These signals can directly improve:

- default script parameters
- stop-loss rules
- fail-fast placement
- delivery profile defaults
- documentation order

## 2. Recovery And Resume Data

This repository relies heavily on sidecar-driven recovery, so recovery telemetry is first-class.

Capture:

- whether the user used `resume-task`
- whether the user used `chapter6-route`
- whether the user used `inspect-run`
- what recommendation was returned
- whether the user followed the recommendation
- whether following the recommendation reduced rerun cost
- which sidecars were opened most often
- which recovery recommendations later proved wrong

These signals can directly improve:

- `chapter6-route`
- `resume-task`
- active-task summaries
- sidecar prioritization
- artifact viewers and dashboard layout

## 3. Time, Cost, And Resource Data

This category determines whether users actually stay.

Capture:

- total task duration
- per-step duration
- deterministic vs LLM time split
- timeout location by step and reviewer
- repeated wait time before user abandonment
- API vs CLI transport cost and failure rate when both are used
- background task completion rate

These signals can directly improve:

- timeout defaults
- API vs CLI routing policy
- reviewer selection policy
- prompt trimming
- asynchronous orchestration priorities

## 4. Needs-Fix And Technical Debt Data

This category explains the real quality burden of the workflow.

Capture:

- count of `P0/P1/P2/P3/P4` findings per task
- time to resolve `P0/P1`
- whether `P2/P3/P4` became technical debt
- which reviewer produced each finding
- which findings repeated across tasks
- which findings were later shown to be false positives

These signals can directly improve:

- review prompts
- needs-fix-fast strategy
- technical debt register structure
- reviewer weighting
- failure taxonomy

## 5. Prototype Lane Data

If prototype onboarding is a future acquisition surface, this category matters a lot.

Capture:

- whether the user starts in prototype lane
- whether a prototype record is created
- whether a prototype scene scaffold is created
- whether prototype TDD is used
- whether the prototype ends as `discard | archive | promote`
- average time from prototype start to promote
- which day the prototype flow most often stalls on

These signals can directly improve:

- prototype documentation
- Day 2 scene scaffold
- prototype templates
- promotion criteria
- new-user onboarding

## 6. Retention And User Journey Data

This category matters for product viability, but it is still secondary to workflow telemetry.

Capture:

- first successful run
- first playable scene created
- first prototype promoted
- first Chapter 6 task completed
- second-day return
- second project created
- first export completed

For this project, the best early retention metrics are not page views. They are workflow milestones.

## 7. Documentation And Help Usage Data

This category helps tighten docs, not just code.

Capture:

- which docs are opened before or after failure
- whether users copy commands from docs and succeed
- which workflow chapter is opened most often
- which failures lead users to recovery docs
- which docs are opened but do not help the user continue

These signals can directly improve:

- README structure
- AGENTS routing
- workflow chapter ordering
- project-health dashboard links
- error message remediation hints

## 8. Project Shape And Template Adaptation Data

This category helps decide what the template should keep generic and what should become optional presets.

Capture:

- project genre or project type
- whether the project stays Windows-only
- whether the project is prototype-heavy or Chapter-6-heavy
- which modules users remove after cloning
- which modules users repeatedly add back
- which top-level capabilities are never used

These signals can directly improve:

- template defaults
- preset strategy
- optional modules
- game-specific prototype scaffolds

## 9. Approval Workflow Data

This category matters because the cloud product will eventually expose approvals in the browser, and approval friction can silently become one of the biggest workflow delays.

Capture:

- how often approval is required
- approval status distribution: `pending | approved | denied | invalid | mismatched`
- time from approval request to approval decision
- whether `approved -> fork` actually converged
- whether `denied -> resume` actually converged
- whether users repeatedly hit the same approval loop without new evidence
- whether `Forbidden commands` was the real blocker

These signals can directly improve:

- approval-sidecar structure
- browser approval UX
- fork vs resume policy
- approval stop-loss rules
- chapter routing stability

## 10. Project-Health And Artifact Viewer Data

Once there is a browser surface, it is important to know whether people are actually using the repository-native recovery substrate or are still navigating blindly.

Capture:

- whether users open project-health before or after task failure
- which project-health panels are opened most
- whether opening `latest.html` leads to successful remediation
- which artifact views are opened most often: `active-task`, `latest.json`, `summary.json`, `repair-guide`, `agent-review`
- whether the user continues from the artifact-linked next step or abandons the task
- whether dashboard views reduce repeated `inspect-run` usage

These signals can directly improve:

- dashboard information density
- artifact index priority
- recovery entrypoint ordering
- latest.html layout
- active-task summary design

## 11. Bootstrap And Environment Failure Data

This category is especially important during Phase A because hosted usability depends on the worker being ready without operator guesswork.

Capture:

- first workspace bootstrap success or failure
- missing dependency class: `git | python | node | codex | dotnet | godot | env-var | auth`
- bootstrap check duration
- repeated bootstrap failures per workspace
- whether the failure was fixed by documentation, automation, or operator intervention
- whether the user abandoned before first successful run

These signals can directly improve:

- `workspace-bootstrap-check`
- dependency layering
- operator setup docs
- hosted-worker image quality
- first-run experience

## 12. Export And Release Milestone Data

This category is not the first thing to instrument, but it becomes valuable once users are trying to ship and not just prototype.

Capture:

- first successful export
- export failure class
- first release-candidate task completion
- whether local hard checks passed before release
- whether release failures were deterministic, content-related, or review-related
- how often users fall back to manual release steps

These signals can directly improve:

- release docs
- release hard gates
- export troubleshooting guidance
- profile defaults for pre-release closure

## 13. Profile, Mode, And Transport Segmentation

Raw telemetry becomes much more actionable once it is segmented by the way the workflow was actually run.

Capture:

- `delivery_profile`: `playable-ea | fast-ship | standard`
- `task_mode`: `prototype | chapter5 | chapter6 | repo-health | recovery`
- transport mode: `codex-cli | openai-api | mixed`
- whether the run used narrow closure or full rerun
- whether the run used recommendation-only or execution mode

These signals can directly improve:

- profile defaults
- API vs CLI routing policy
- task-mode documentation
- timeout and retry policy by mode

## Recommended Priority Order

If telemetry must be implemented incrementally, use this order:

1. workflow execution data
2. recovery and resume data
3. time, cost, and resource data
4. needs-fix and technical-debt data
5. approval workflow data
6. bootstrap and environment failure data
7. prototype lane data
8. project-health and artifact-viewer data
9. retention milestones
10. documentation usage data
11. project-shape data
12. export and release milestone data
13. profile, mode, and transport segmentation

## Minimal Event Set

If only a small telemetry surface can be implemented first, capture these 10 events:

1. `project_created`
2. `prototype_record_created`
3. `prototype_scene_created`
4. `prototype_tdd_run_finished`
5. `task_chapter6_started`
6. `task_chapter6_route_decided`
7. `task_step_finished`
8. `task_stop_loss_triggered`
9. `needs_fix_generated`
10. `task_completed`

## Event Naming And Field Stability

Telemetry only becomes useful if event names and key fields remain stable across script iterations.

Use these rules:

- event names should be verb-oriented and repository-native, for example `task_step_finished` instead of generic UI analytics names
- avoid renaming existing high-value events once dashboards or replay tools depend on them
- do not overload one field with multiple meanings across workflow modes
- prefer additive evolution: add a new field instead of changing the meaning of an old one
- reserve enum-style fields for machine decisions, for example `status`, `failure_kind`, `delivery_profile`, `task_mode`, `transport_mode`
- if a field is only best-effort, mark it optional and do not silently treat missing values as false
- if a field affects dashboards, routing, or future replay datasets, document it before changing it

The most stability-sensitive fields are:

- `event`
- `timestamp`
- `project_id`
- `workspace_id`
- `task_id`
- `entrypoint`
- `step`
- `status`
- `failure_kind`
- `delivery_profile`
- `task_mode`
- `transport_mode`
- `recommended_next_action`
- `user_followed_recommendation`

Recommended change rule:

1. new fields may be added freely if they are clearly optional
2. enum values should be extended carefully and documented in the same change
3. removals or semantic redefinitions should be treated like protocol changes and should require a migration note

## Recommended Base Event Fields

Every telemetry event should try to include these fields when available:

```json
{
  "event": "task_step_finished",
  "timestamp": "2026-04-20T12:00:00Z",
  "project_id": "...",
  "workspace_id": "...",
  "task_id": "T66",
  "entrypoint": "run-single-task-chapter6",
  "step": "6.7",
  "delivery_profile": "fast-ship",
  "status": "ok",
  "duration_sec": 1234,
  "failure_kind": "none",
  "recommended_next_action": "run-6.8",
  "user_followed_recommendation": true
}
```

## Phase A Minimal Instrumentation Order

Phase A should not start with a large analytics system. It should start with the smallest event set that improves hosted workflow decisions.

Recommended implementation order:

1. `bootstrap_checked`
   - records whether the hosted worker is ready before any real task execution
2. `task_started`
   - records the top-level entrypoint, profile, mode, and transport
3. `task_route_decided`
   - records the first repository-native routing outcome such as `run-6.7`, `run-6.8`, `inspect-first`, or stop-loss
4. `task_step_finished`
   - records step durations and step outcomes for the major workflow stages
5. `task_stop_loss_triggered`
   - records the exact stop-loss family that prevented wasted reruns
6. `approval_updated`
   - records `pending`, `approved`, `denied`, `invalid`, and the chosen next action
7. `task_completed`
   - records whether the task converged, was abandoned, or was converted into residual or technical debt

Only after these are stable should Phase A add:

- `artifact_view_opened`
- `project_health_opened`
- `needs_fix_generated`
- `prototype_record_created`
- `prototype_promoted`
- export and release milestone events

The rule is simple: instrument decisions and convergence before instrumenting general product behavior.

## What Is Most Actionable

The most actionable telemetry fields are:

- `entrypoint`
- `step`
- `duration_sec`
- `status`
- `failure_kind`
- `recommended_next_action`
- `user_followed_recommendation`
- `rerun_count`
- `final_outcome`

These fields are enough to improve scripts, defaults, routing, and docs.

## What Not To Prioritize Early

Do not prioritize these categories early unless there is a very strong reason:

- full raw chat transcripts
- full prompt bodies
- full diffs for analytics purposes
- raw code snapshots for telemetry
- detailed cursor or clickstream logging
- generic page-view analytics detached from workflow results

These are expensive in privacy, storage, and interpretation cost, while often adding less value than structured workflow signals.

## Event Producer And Consumer Map

This table maps the recommended telemetry events to repository-native producers and consumers. It is intentionally script-oriented so Phase A can add telemetry without creating a second workflow engine.

| Event | Producer | Consumer | Phase | Notes |
|---|---|---|---|---|
| `bootstrap_checked` | future `workspace-bootstrap-check`, hosted runner bootstrap wrapper | hosted UI, operator setup dashboard, cloud worker readiness checks | Phase A | Should run before real task execution. Capture missing dependency class and readiness status. |
| `task_started` | future `run-hosted-task`, `dev_cli.py run-single-task-chapter6`, `run_single_task_chapter6_lane.py` | hosted run list, task execution page, cost dashboard | Phase A | Capture entrypoint, task id, profile, mode, transport, branch, and workspace id. |
| `task_route_decided` | `dev_cli.py chapter6-route`, `run_single_task_chapter6_lane.py` | hosted recovery page, route replay dataset, task execution page | Phase A | Preserve repository-owned fields such as `preferred_lane`, `chapter6_next_action`, stop-loss reason, and forbidden commands. |
| `task_step_finished` | `run_review_pipeline.py`, `run_single_task_chapter6_lane.py`, `run_single_task_light_lane.py`, `dev_cli.py` wrappers | task timeline, timeout dashboard, workflow bottleneck analysis | Phase A | Major steps only at first. Avoid excessive per-command noise. |
| `task_stop_loss_triggered` | `chapter6-route`, `run_single_task_chapter6_lane.py`, `llm_review_needs_fix_fast.py`, `run_review_pipeline.py` | stop-loss dashboard, recovery page, route tuning review | Phase A | Capture exact family: `planned_only`, `artifact_integrity`, `rerun_guard`, `llm_retry_stop_loss`, `sc_test_retry_stop_loss`, `repo_noise`, `waste_signals`. |
| `approval_updated` | `sc_repair_approval.py`, future hosted approval sync script | browser approval UI, route controller, audit view | Phase A | Capture status, decision, reason, whether next action was fork or resume. |
| `task_completed` | future `run-hosted-task`, `run_single_task_chapter6_lane.py`, `run_review_pipeline.py` | project progress dashboard, retention milestones, convergence analysis | Phase A | Capture `converged | abandoned | residual_recorded | technical_debt_recorded`. |
| `artifact_view_opened` | hosted web API / browser UI | artifact viewer analytics, dashboard layout review | Phase A+ | UI-owned event. Do not make repository scripts depend on it. |
| `project_health_opened` | hosted web API / browser UI, `project-health-scan` wrapper when run from UI | project-health dashboard, remediation analysis | Phase A+ | Useful after project-health page is exposed to users. |
| `needs_fix_generated` | `run_review_pipeline.py`, `llm_review_needs_fix_fast.py`, `agent_to_agent_review.py` | technical debt analytics, reviewer effectiveness dashboard | Phase A+ | Capture severity distribution and producer reviewer, but avoid raw prompt/body by default. |
| `prototype_record_created` | `dev_cli.py` prototype helpers, future hosted prototype entrypoint | prototype funnel dashboard | Phase A+ | Should link to prototype slug, not raw design text unless explicitly needed. |
| `prototype_scene_created` | prototype scene scaffold script / `run-prototype-tdd` helpers | prototype onboarding dashboard | Phase A+ | Captures whether a real Godot scene was created. |
| `prototype_tdd_run_finished` | `dev_cli.py run-prototype-tdd` | prototype TDD dashboard, new-user onboarding review | Phase A+ | Capture stage: `red | green | refactor`, status, duration, and failure kind. |
| `prototype_promoted` | prototype promotion script or formal task creation step | prototype-to-task funnel, retention milestones | Phase A+ | Capture promote/kill/archive decision, not full raw prototype content. |
| `export_finished` | future hosted release/export wrapper, local hard-check release wrapper | release dashboard, export troubleshooting | Later | Add after export flow becomes a real hosted user journey. |

Implementation rule:

- repository scripts should produce workflow telemetry for decisions, runs, sidecars, stop-losses, approvals, and task outcomes
- hosted UI/API should produce interaction telemetry for artifact views, dashboard opens, and user follow-through
- neither side should duplicate the other's decision logic
- if a telemetry event needs repository truth, it should be emitted by or derived from repository-native scripts and sidecars
- if a telemetry event only describes user navigation, it should stay in the hosted UI/API layer

## Privacy And Collection Boundary

Prefer structured summaries over raw user content.

Default rule:

- collect workflow state
- collect step outcomes
- collect durations
- collect recommendation/follow decisions
- avoid storing unnecessary raw content

This is both safer and more actionable.

## Direct Feedback Loop To Repository Evolution

Telemetry is only useful if it feeds concrete repository changes.

Every telemetry review cycle should ask:

1. Which step wastes the most total user time?
2. Which stop-loss family prevents the most wasted reruns?
3. Which stop-loss family is still too weak?
4. Which recommendation is most often ignored?
5. Which recommendation is followed but still fails?
6. Where do new users stall in the prototype flow?
7. Which docs are opened but do not lead to successful continuation?
8. Which scripts should become lighter, stricter, or more top-level?

## Recommended Review Cadence

Once real users exist, review telemetry at three cadences:

- weekly: failures, timeouts, stop-losses, recovery usage
- monthly: retention milestones, prototype promotion patterns, project-shape trends
- release-by-release: parameter defaults, entrypoint changes, workflow and doc rewrites

## Recommended Future Additions

These additions are worth considering later if the hosted product grows:

- route decision replay dataset for improving `chapter6-route`
- prototype funnel dashboard
- reviewer effectiveness dashboard
- task convergence dashboard
- per-profile cost and success-rate comparison
- approval-loop dashboard
- bootstrap-failure dashboard
- project-health remediation dashboard
- doc-to-command conversion dashboard

## One-Sentence Rule

The most valuable cloud data is the structured evidence of how users move through the workflow, where they stall, and which repository-native decisions save or waste their time.
