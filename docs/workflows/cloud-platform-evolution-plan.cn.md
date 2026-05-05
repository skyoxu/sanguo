
# Cloud Platform Evolution Plan 中文版

本文档记录将当前 template workflow 迁移到云端的推荐演进路径，同时保持 repository-native 的 Codex orchestration model 不变。

相关后续文档：`docs/workflows/cloud-user-telemetry-and-feedback-plan.md` 用于记录 hosted usage data 及其对 repository 自我演进的价值。

## 目标

保留当前 repository workflow 作为 execution kernel：

- `workflow.md`
- `AGENTS.md`
- `scripts/python/dev_cli.py`
- `scripts/sc/run_review_pipeline.py`
- `scripts/sc/llm_review_needs_fix_fast.py`
- `logs/ci/**` 下的 task sidecar
- `execution-plans/**` 和 `decision-logs/**` 下的 durable docs

不要把 workflow 重写成 platform-specific state machine。cloud layer 的职责是 host、index、recover 现有 workflow，而不是替代它。

## 核心原则

拆分为三层：

1. Git source of truth
2. cloud workspace 作为 execution source of truth
3. browser 作为 access surface

Git 保存 code 和 durable docs。cloud workspace 保存 runtime state、sidecar 和 evidence。browser 只负责触发 runs、读取 artifacts、处理 approvals。

## 哪些内容保留在 Git

- source code
- `docs/**` 下的 docs
- `workflow.md` 这类 workflow docs
- `scripts/**` 下的 scripts
- `execution-plans/**` 下的 durable intent
- `decision-logs/**` 下的 durable decisions

## 哪些内容保留在 Cloud Workspaces

- `logs/**`
- `logs/ci/active-tasks/**`
- task run sidecar，例如 `latest.json`、`summary.json`、`execution-context.json`
- repair artifacts，例如 `repair-guide.json`、`repair-guide.md`
- agent review artifacts，例如 `agent-review.json`、`agent-review.md`
- event streams，例如 `run-events.jsonl`
- local task/runtime caches

这些文件是 `resume-task`、`chapter6-route`、`inspect-run`、`project-health-scan` 的 recovery substrate。

## 为什么 Workspace 必须在 Cloud

repository 已依赖 sidecar-driven recovery。如果 workspace 只在用户本地，就会破坏 long-running execution、断线后 recovery 和一致的 environment control。

cloud-resident workspace 能带来：

- 稳定的 dependency versions
- durable recovery artifacts
- long-running task execution
- 端用户只需 browser 即可访问
- 跨设备、跨日期的 session continuity

## 推荐的 MVP Architecture

围绕当前 workflow 构建一个最小 platform，包含六个 components。

### 1. Git Source

职责：clone/fetch/checkout、branch selection、source history。不要在这里运行 tasks。

### 2. Workspace Manager

职责：

- 为每个 tenant/project/workspace-id 分配 workspace
- 恢复已存在 workspace
- 把 repository state 同步进 workspace
- 清理过期 workspace

推荐路径：

```text
/workspaces/<tenant>/<project>/<workspace-id>/
```

### 3. Runner

职责：只运行 top-level repository entrypoint，永远不重写 workflow logic。

推荐命令：

```powershell
py -3 scripts/python/dev_cli.py resume-task --task-id <id> --recommendation-only
py -3 scripts/python/dev_cli.py chapter6-route --task-id <id> --recommendation-only
py -3 scripts/python/dev_cli.py run-single-task-chapter6 --task-id <id> --godot-bin "<...>" --delivery-profile fast-ship
py -3 scripts/python/dev_cli.py project-health-scan
```

### 4. Artifact Indexer

职责：发现最新 task/run artifacts、向 web layer 暴露 compact summary、让 UI 直接指向 authoritative files。

首批应 index 的 artifacts 包括：

- `logs/ci/project-health/latest.html`
- `logs/ci/active-tasks/task-<id>.active.md`
- task-scoped `latest.json`
- `summary.json`
- `repair-guide.md`
- `agent-review.md`
- `execution-plans/**`
- `decision-logs/**`

### 5. Web API

职责：启动 runs、恢复 runs、读取 artifacts、暴露 approvals、暴露 run status。如果 repository scripts 已能给出 workflow decision，不要在这一层重复计算。

### 6. Browser UI

职责：project list、workspace list、task start/recovery page、project health view、artifact viewing、approval actions。不要把 browser 变成第二个 workflow engine。

## Workspace Layout

一个实用的第一版布局可以是：

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

其中：`repo/` 存 checked-out project 和 repository-native logs/sidecars；`runtime/` 存 platform-level execution logs；`meta/` 只存 platform metadata，不是 workflow truth。

## 最小 Platform Database

第一版用一个 SQLite database 就够了。

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

## 最小 API Surface

推荐首批 endpoints：

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

## 最小 UI Pages

最小可用 browser UI 只需要：

1. Project list
2. Workspace list
3. Task execution page
4. Recovery/active-task page
5. Artifact viewer page
6. Project health page

Task execution page 应先调用 recovery commands，再决定是否提供完整 Chapter 6 run 入口。

## Execution Contract

platform 应把 repository scripts 视为 decision authority。browser/API/runner 不应重新解释：

- `preferred_lane`
- `Recommended command`
- `Forbidden commands`
- stop-loss families
- approval state transitions

这些解释权应继续由 repository-native commands 持有：`resume-task`、`chapter6-route`、`inspect-run`、`run-single-task-chapter6`。

## Dependency Model

### End User Device

end user 通常只需要：

- browser
- network access
- login credential

end user 不应需要本地安装：

- `git`
- `python`
- `node.js`
- `codex`
- `.NET SDK`
- `Godot .NET`

### Cloud Worker

cloud worker 应承载真实 execution dependencies：

- Windows environment
- `git`
- `python`
- `node.js`
- `codex`
- `.NET SDK 8`
- `Godot .NET`
- project-specific runtime dependencies
- 启用 `openai-api` transport 时需要 `OPENAI_API_KEY`

## 可以从 Multi-Tenant Agent Platform 借鉴什么

真正值得借鉴的是 runtime 与 hosting 层面的经验，而不是语言重写：

- 把 workspace/runtime concerns 与 workflow concerns 分开
- 让 session state 可以从 disk artifacts 重建
- hot state 放在 cache，cold state 从 durable files 重建
- 在 filesystem boundary 上隔离 users/projects/workspaces
- 让 frontend 负责 observe 和 trigger，而不是 decide

## 一开始不要做什么

不要从以下事情开始：

- 把 workflow 重写成一个新 orchestration engine
- 构建新的 Rust claw runtime
- 搭建完整 skills marketplace
- 上 distributed session infrastructure
- 把 object storage 做成硬前置依赖
- 先做复杂的 multi-agent collaboration UX

这些都是后期问题。

## 推荐的 Evolution Phases

### Phase A: Single-Node Cloud Runner

目标：

- 一台 Windows cloud machine
- 一个 web service
- 一个 runner process
- 一个 SQLite metadata DB
- local disk 上的 durable workspace
- 一个低摩擦 tool surface，把 repository entrypoint 暴露给 browser/API/CLI 调用方，同时不重写 workflow logic

成功标准：

- 能远程运行现有 top-level commands
- 能从 browser 恢复 tasks
- 能浏览 project-health 和 task artifacts
- 能通过稳定 tool layer 暴露 repository kernel，而不是强迫用户学习 internal script topology

### Phase B: Multi-Tenant Workspace Hosting

目标：

- user login
- project/workspace catalog
- browser 中的 approval handling
- 多个 persistent workspaces
- 稳定的 runner queueing

成功标准：

- 一个 platform 能安全承载多个 user/project/workspace，且不会 workspace collision
- sidecar 保持隔离且 durable

### Phase C: Storage Abstraction And Scale-Out

目标：

- 为 artifact 与 durable docs 抽象 file storage
- 后续支持 remote/object-backed storage
- 支持 node affinity 与 worker expansion

成功标准：

- workspace restoration 不再永久绑定某一台机器
- platform 能在不重写 repository workflow logic 的前提下扩展规模

## 推荐的 First Build Order

1. workspace manager
2. top-level command runner
3. artifact indexer
4. web API
5. browser UI
6. approval handling

这个顺序能保住 repository kernel，并且尽早交付价值。

## 实用的 Phase Boundary

如果问题是：`automatic wiring`、`hosted tool surfaces`、`MCP-style entry aggregation`、`low-friction natural-language control` 应该从什么时候开始纳入？

答案是：它们属于 Phase A，而不是更后面的 platform scale 阶段。前提是它们仍然调用 repository-native entrypoint，不在 browser 或 API 里建立第二个 workflow engine，也不重解释 repository scripts 已持有的 sidecar decision。

当问题从“如何让一个 hosted workspace 像产品一样可用”转移为“如何安全且持久地托管很多 user/project/workspace”时，就进入 Phase B。

## 一句话规则

platform 的职责是 host 当前 workflow，而不是 replace 它。
