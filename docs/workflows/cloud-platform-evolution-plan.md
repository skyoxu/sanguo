# Cloud Platform Evolution Plan

This document records the recommended evolution path for moving the current template workflow to the cloud while keeping the repository-native Codex orchestration model.

Related follow-up: `docs/workflows/cloud-user-telemetry-and-feedback-plan.md` records which hosted usage data is most valuable for feeding repository self-improvement.

## Goal

Keep the current repository workflow as the execution kernel:

- `workflow.md`
- `AGENTS.md`
- `scripts/python/dev_cli.py`
- `scripts/sc/run_review_pipeline.py`
- `scripts/sc/llm_review_needs_fix_fast.py`
- task sidecars under `logs/ci/**`
- durable docs under `execution-plans/**` and `decision-logs/**`

Do not rewrite the workflow into a new platform-specific state machine. The cloud layer should host, index, and recover the existing workflow instead of replacing it.

## Core Principle

Separate three layers:

1. Git source of truth
2. Cloud workspace as the execution source of truth
3. Browser as the access surface

Git stores code and durable docs. The cloud workspace stores runtime state, sidecars, and evidence. The browser only triggers runs, reads artifacts, and handles approvals.

## What Stays In Git

Keep these in the Git repository:

- source code
- docs under `docs/**`
- workflow docs such as `workflow.md`
- scripts under `scripts/**`
- durable intent under `execution-plans/**`
- durable decisions under `decision-logs/**`

## What Stays In Cloud Workspaces

Keep these in the cloud execution workspace, not as the primary local user copy:

- `logs/**`
- `logs/ci/active-tasks/**`
- task run sidecars such as `latest.json`, `summary.json`, `execution-context.json`
- repair artifacts such as `repair-guide.json`, `repair-guide.md`
- agent review artifacts such as `agent-review.json`, `agent-review.md`
- event streams such as `run-events.jsonl`
- local task/runtime caches

These files are the recovery substrate for:

- `resume-task`
- `chapter6-route`
- `inspect-run`
- `project-health-scan`

## Why The Workspace Must Be Cloud-Resident

The repository already relies on sidecar-driven recovery. A pure local-user workspace would break long-running execution, recovery after disconnect, and consistent environment control.

Cloud-resident workspaces provide:

- stable dependency versions
- durable recovery artifacts
- long-running task execution
- browser-only access for end users
- better session continuity across devices and days

## Recommended MVP Architecture

Build a minimal platform around the current workflow with six components.

### 1. Git Source

Responsibilities:

- clone/fetch/checkout
- branch selection
- source history

Do not run tasks here.

### 2. Workspace Manager

Responsibilities:

- allocate one workspace per tenant/project/workspace-id
- restore an existing workspace
- sync repository state into the workspace
- clean up expired workspaces

Recommended path layout:

```text
/workspaces/<tenant>/<project>/<workspace-id>/
```

### 3. Runner

Responsibilities:

- run only top-level repository entrypoints
- never reimplement workflow logic

Recommended commands:

```powershell
py -3 scripts/python/dev_cli.py resume-task --task-id <id> --recommendation-only
py -3 scripts/python/dev_cli.py chapter6-route --task-id <id> --recommendation-only
py -3 scripts/python/dev_cli.py run-single-task-chapter6 --task-id <id> --godot-bin "<...>" --delivery-profile fast-ship
py -3 scripts/python/dev_cli.py project-health-scan
```

### 4. Artifact Indexer

Responsibilities:

- discover the latest task/run artifacts
- expose compact summaries to the web layer
- point the UI at authoritative files instead of copying logic into the frontend

First-class indexed artifacts should include:

- `logs/ci/project-health/latest.html`
- `logs/ci/active-tasks/task-<id>.active.md`
- task-scoped `latest.json`
- `summary.json`
- `repair-guide.md`
- `agent-review.md`
- `execution-plans/**`
- `decision-logs/**`

### 5. Web API

Responsibilities:

- start runs
- resume runs
- read artifacts
- expose approvals
- expose run status

Do not compute workflow decisions here when the repository scripts already do.

### 6. Browser UI

Responsibilities:

- project list
- workspace list
- task start/recovery page
- project health view
- artifact viewing
- approval actions

Do not make the browser a second workflow engine.

## Workspace Layout

A practical first layout is:

```text
/workspaces/<tenant>/<project>/<workspace-id>/
  /repo
  /runtime
    /stdout
    /stderr
    /commands
  /meta
    workspace.json
    latest-run.json
    approvals.json
```

Notes:

- `repo/` contains the checked-out project and all existing repository-native logs/sidecars.
- `runtime/` stores platform-level execution logs.
- `meta/` stores platform metadata, not workflow truth.

## Minimal Platform Database

A single SQLite database is enough for the first version.

### projects

- `id`
- `name`
- `repo_url`
- `default_branch`
- `created_at`

### workspaces

- `id`
- `project_id`
- `tenant`
- `branch`
- `path`
- `status`
- `last_synced_at`

### runs

- `id`
- `workspace_id`
- `task_id`
- `run_type`
- `command`
- `status`
- `started_at`
- `finished_at`
- `run_dir`
- `stdout_path`
- `stderr_path`

### approvals

- `id`
- `workspace_id`
- `task_id`
- `status`
- `decision`
- `reason`
- `updated_at`

## Minimal API Surface

Recommended first endpoints:

### Projects

- `POST /projects`
- `GET /projects`
- `GET /projects/:id`

### Workspaces

- `POST /projects/:id/workspaces`
- `GET /projects/:id/workspaces`
- `GET /workspaces/:id`
- `POST /workspaces/:id/sync`

### Runs

- `POST /workspaces/:id/run/resume-task`
- `POST /workspaces/:id/run/chapter6-route`
- `POST /workspaces/:id/run/chapter6`
- `POST /workspaces/:id/run/project-health`
- `GET /runs/:run_id`
- `GET /runs/:run_id/logs`
- `POST /runs/:run_id/cancel`

### Artifacts

- `GET /workspaces/:id/artifacts/active-task?task_id=...`
- `GET /workspaces/:id/artifacts/latest?task_id=...`
- `GET /workspaces/:id/artifacts/repair-guide?task_id=...`
- `GET /workspaces/:id/artifacts/agent-review?task_id=...`
- `GET /workspaces/:id/artifacts/project-health`
- `GET /workspaces/:id/artifacts/execution-plans`
- `GET /workspaces/:id/artifacts/decision-logs`

## Minimal UI Pages

A minimal usable browser UI only needs:

1. Project list
2. Workspace list
3. Task execution page
4. Recovery/active-task page
5. Artifact viewer page
6. Project health page

The task execution page should first call recovery commands before offering a full Chapter 6 run.

## Execution Contract

The platform should treat repository scripts as the decision authority.

The browser/API/runner should not reinterpret:

- `preferred_lane`
- `Recommended command`
- `Forbidden commands`
- stop-loss families
- approval state transitions

Those should remain owned by repository-native commands:

- `resume-task`
- `chapter6-route`
- `inspect-run`
- `run-single-task-chapter6`

## Dependency Model

### End User Device

The end user should normally need only:

- browser
- network access
- login credential

The end user should not need local installation of:

- `git`
- `python`
- `node.js`
- `codex`
- `.NET SDK`
- `Godot .NET`

### Cloud Worker

The cloud worker should carry the real execution dependencies:

- Windows environment
- `git`
- `python`
- `node.js`
- `codex`
- `.NET SDK 8`
- `Godot .NET`
- project-specific runtime dependencies
- `OPENAI_API_KEY` when `openai-api` transport is enabled

## What To Borrow From A Multi-Tenant Agent Platform

The right lessons are runtime and hosting lessons, not a language rewrite:

- separate workspace/runtime concerns from workflow concerns
- keep session state rebuildable from disk artifacts
- store hot state in cache, rebuild cold state from durable files
- isolate users/projects/workspaces at the filesystem boundary
- let the frontend observe and trigger, not decide

## What Not To Do First

Do not start with:

- rewriting the workflow into a new orchestration engine
- building a new Rust claw runtime
- a full skills marketplace
- distributed session infrastructure
- object storage as a hard requirement
- complex multi-agent collaboration UX

Those are later-stage concerns.

## Suggested Evolution Phases

### Phase A: Single-Node Cloud Runner

Goal:

- one Windows cloud machine
- one web service
- one runner process
- one SQLite metadata DB
- durable workspaces on local disk
- one low-friction tool surface that exposes the existing repository entrypoints to browser/API/CLI callers without rewriting workflow logic

Success criteria:

- can run existing top-level commands remotely
- can recover tasks from browser
- can browse project-health and task artifacts
- can expose the repository kernel through a stable tool layer instead of forcing users to learn raw internal script topology

Phase A should already include the first productization layer for cloud use:

- workspace bootstrap and dependency verification for the hosted Windows worker
- automatic wiring of the runner to stable repository entrypoints
- a small, intentional tool surface for top-level actions such as resume, route, chapter6, project-health, and artifact readback
- support for multiple access surfaces reusing the same kernel, typically browser + web API + runner, without duplicating workflow decisions
- low-friction setup for operators so the cloud deployment feels like one hosted product, not a bag of scripts

Phase A should treat new hosted entrypoints as script-first capabilities, not skill-first capabilities. The stable execution surface should be implemented as repository scripts that can be called by CLI, browser, web API, and cloud runners. Skills may be added later as thin guidance layers for agents, but they should not be the primary execution contract.

Typical Phase A script-level entrypoints may include:

- `workspace-bootstrap-check` for hosted worker dependency verification and environment readiness
- `list-task-tools` or `describe-task-tools` for exposing the repository tool surface as machine-readable data
- `run-artifact-index-refresh` for refreshing task/latest/repair-guide/agent-review/project-health summaries
- `run-hosted-resume` for a single hosted recovery entry that delegates to repository-native recovery commands
- `run-hosted-task` for a stable cloud execution entrypoint that still calls repository-native top-level workflow commands
- `export-active-task-summary` for lightweight frontend-facing recovery/readback summaries
- `read-approval-state` or `run-approval-sync` for approval-sidecar readback and sync

Skills in Phase A should remain thin operator guidance, for example:

- telling an agent when to call resume/route/inspect
- explaining which hosted script should be preferred for a given task state
- guiding recovery order and approval handling

Phase A may also introduce lightweight resolver behavior for skills. The skill explains how to operate; the resolver decides when that skill should be activated and which supporting resources should be loaded.

A practical Phase A resolver should stay simple and rule-based, for example:

- if a task enters Chapter 6 execution or recovery, load the Chapter 6 operator skill
- if a task is still exploratory and not yet in formal Taskmaster flow, load prototype-lane guidance
- if approval sidecars are present, load approval-handling guidance
- if complexity heuristics say Serena/context gathering is worth paying for, load the Serena guidance layer

The resolver in Phase A should not become a second orchestration engine. It should only decide which thin guidance layer to load around existing script-owned entrypoints.

The rule is: execution authority belongs to scripts; usage guidance may live in skills; lightweight resolvers may decide when to activate those skills.

A practical Phase A layering model is:

| Layer | Main responsibility | Typical examples in this repository | Should own execution truth? |
|---|---|---|---|
| `script` | Execute real work, write sidecars, enforce stop-loss and quality gates, expose stable machine-callable contracts | `resume-task`, `chapter6-route`, `inspect-run`, `run-single-task-chapter6`, `project-health-scan`, future hosted entrypoints such as `run-hosted-resume` | Yes |
| `skill` | Explain how to use existing entrypoints, guide operator behavior, describe preferred recovery order and task-mode choices | Chapter 6 operator guidance, prototype-lane guidance, approval-handling guidance, Serena usage guidance | No |
| `resolver` | Decide which skills/resources should be activated for the current task state, while leaving all workflow decisions to scripts | rule-based loading for Chapter 6, prototype, approval, or Serena guidance | No |

For Phase A, use this table as a placement rule:

- if the capability must be callable by browser, web API, CLI, or cloud runner, make it a script
- if the capability mainly teaches the agent how to use existing scripts, make it a skill
- if the capability only decides when a skill should be activated, make it a lightweight resolver rule
- if a proposed resolver starts deciding stop-loss, approval transitions, route outcomes, or quality-gate outcomes, it is too heavy and should stay in scripts instead

A minimal Phase A implementation should start with this backlog:

Script entrypoints first:

1. `workspace-bootstrap-check`: verify hosted Windows worker dependencies and print machine-readable readiness output.
2. `describe-task-tools`: list stable repository-native task tools, inputs, outputs, sidecars, and intended callers.
3. `run-artifact-index-refresh`: refresh compact summaries for active task, latest pipeline run, repair guide, agent review, execution plans, decision logs, and project health.
4. `run-hosted-resume`: provide one hosted recovery entry that calls resume-task, chapter6-route, and inspect-run in the repository-approved order.
5. `run-hosted-task`: provide one hosted task execution entry that delegates to `run-single-task-chapter6` or other stable top-level workflow commands.

Thin skills second:

1. Chapter 6 operator skill: explain when to resume, route, inspect, run 6.7, run 6.8, or stop.
2. Prototype-lane operator skill: explain when to stay in prototype flow and when to promote into formal workflow.
3. Approval-handling skill: explain pending, approved, denied, invalid, forbidden-command, and fork behavior.
4. Serena/context-gathering skill: explain when context gathering is worth the extra cost.

Resolver rules third:

1. Task has a task id and Chapter 6 artifacts or commands are requested -> activate Chapter 6 operator skill.
2. Task has no formal task id or is explicitly exploratory -> activate prototype-lane operator skill.
3. Approval sidecars or approval-related route fields exist -> activate approval-handling skill.
4. Complexity heuristics indicate cross-module or architecture-sensitive work -> activate Serena/context-gathering skill.

This sequencing keeps Phase A useful quickly: scripts expose stable hosted capabilities first, skills make agent behavior easier to steer second, and resolver rules only automate which guidance layer is loaded.

This also means the repository harness should be slim in the right place. Do not move repository truth, sidecar production, stop-loss enforcement, approval state transitions, route decisions, or quality gates into skills. Those remain script-owned harness responsibilities.

What may move into skills is the operator-guidance layer, for example:

- when to call resume vs route vs inspect
- when a task should stay in prototype flow vs Chapter 5/6
- when Serena/context gathering is worth paying for
- how an agent should interpret existing entrypoints for a given task situation

So the goal is not to make the harness thin by deleting script capabilities. The goal is to keep the execution kernel script-first while moving some usage guidance out of long repository docs and into thin skills.

Phase A is also the right place to add a small amount of game-specific operator guidance, but only as a thin layer above the existing workflow kernel.

Recommended game-specific Phase A additions:

1. Prototype-lane `solo mode` guidance
   - Keep the existing prototype lane, promotion boundary, and repository-native TDD flow.
   - Add a lighter independent-developer guidance layer that helps answer:
     - what is the core player fantasy
     - what is the minimum playable loop for this prototype
     - what proves the prototype should be promoted, iterated, or killed
   - This belongs in skills/docs, not in a new execution engine.

2. Reusable repair protocol layer above repeated failure families
   - The repository should keep treating repeated repair experience as a first-class asset instead of re-solving the same failure pattern with fresh prompt work every time.
   - When the same classes of breakage recur, Phase A should prefer script-owned or sidecar-owned protocolization for:
     - stable failure-family naming
     - reusable stop-loss and next-action rules
     - repair checklists or guided narrow-lane reruns
     - compact recovery summaries that survive context reset
   - The point is not to remove LLM review. The point is to convert proven repair experience into reusable protocol so later runs become cheaper, faster, and less drift-prone.
   - Good candidates are repeated `artifact_integrity`, rerun-stop-loss, reviewer-timeout, acceptance-extract, or task-scoped test-fallback families.

3. Dynamic playability validation before static code correctness expansion
   - For prototype-facing and early game-facing work, the repository should prefer proving that the thing is playable, understandable, and worth keeping before paying for wider static closure.
   - Static correctness still matters, but it should follow evidence that the playable loop is real enough to deserve heavier closure.
   - In practice this means Phase A should expose lightweight runtime evidence surfaces such as:
     - can the player complete the minimum loop
     - is the interaction understandable without explanation
     - do runtime logs, screenshots, clips, or tiny playtest notes confirm the intended feel
     - does the prototype deserve promotion, iteration, or discard
   - This fits the current repository shape well because it strengthens prototype lane and game-QA guidance without weakening Chapter 6 deterministic and review gates.

4. Scrum-style sprint summary layer above structured task data
   - Keep `tasks.json`, `tasks_back.json`, `tasks_gameplay.json`, overlays, and sidecars as the machine-readable execution substrate.
   - Do not replace that substrate with a role-style scrum agent.
   - Instead, add a thin summary layer that makes the current slice easier to read:
     - current sprint goal
     - this round only
     - explicitly out of scope this round
     - what must be true before entering Chapter 6
   - This should remain a summary/productivity layer, not a second planner.

Placement rule for these game-specific additions:

Additional absorption rule for Phase A and Prototype work:

- if a lesson comes from repeated repair work, prefer turning it into a named protocol, sidecar field, retry policy, or narrow-lane rule before solving it again with free-form prompting
- if a decision is still about "is this actually playable / understandable / worth keeping", prefer dynamic playable evidence first and postpone heavier static closure until promotion is justified

- if it changes execution authority, stop-loss, quality gates, or recovery routing, it stays in scripts
- if it helps a game-focused agent use existing scripts better, it belongs in skills/docs
- if it summarizes structured task state for readability, it belongs in thin summaries/templates
- if it starts competing with task triplets, overlays, or route scripts, it is too heavy for Phase A

In other words, the right Phase A mindset is not only "remote execution" but also "hosted tool-layer productization". Ideas similar to auto-wiring, multi-entry reuse, and low-setup natural-language control belong here as long as they do not replace repository-native decision authority.

### Phase B: Multi-Tenant Workspace Hosting

Goal:

- user login
- project/workspace catalog
- approval handling in the browser
- multiple persistent workspaces
- stable runner queueing

Success criteria:

- one platform can host multiple users/projects without workspace collisions
- sidecars remain isolated and durable

### Phase C: Storage Abstraction And Scale-Out

Goal:

- abstract file storage for artifacts and durable docs
- support remote/object-backed storage later
- support node affinity and worker expansion

Success criteria:

- workspace restoration is not tied to one machine forever
- platform can scale without rewriting repository workflow logic

## Suggested First Build Order

1. workspace manager
2. runner for top-level commands
3. artifact indexer
4. web API
5. browser UI
6. approval handling

This order preserves the existing repository kernel and delivers value early.

## Practical Phase Boundary

If the question is "when do ideas like automatic wiring, hosted tool surfaces, MCP-style entry aggregation, or low-friction natural-language control start to belong?" the answer is: they are Phase A concerns, not later-stage platform scale concerns.

They should be treated as part of the first hosted execution product, provided they:

- call stable repository-native entrypoints
- do not create a second workflow engine in the browser or API
- do not reinterpret sidecar decisions that repository scripts already own

Phase B begins when the problem shifts from "make one hosted workspace feel like a usable product" to "host many users/projects/workspaces safely and durably".

## One-Sentence Rule

The platform should host the current workflow, not replace it.
