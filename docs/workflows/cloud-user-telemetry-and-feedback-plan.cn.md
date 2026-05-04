
# Cloud User Telemetry And Feedback Plan 中文版

本文档描述了：当项目迁移到 cloud，并开始服务真实 user 之后，哪些 usage data 最有价值。

目标不是做 generic analytics。目标是捕获最小且可结构化的 signals，从而直接改善：

- workflow speed
- workflow correctness
- stop-loss quality
- recovery quality
- prototype onboarding
- long-term template evolution

## 核心原则

最有价值的 data 不是 raw chat content，而是关于 workflow 的 structured evidence，例如：

- 用户从哪个入口进来
- 卡在了哪里
- 触发了哪条 stop-loss rule
- 用户是否采纳了 recommendation
- 哪些 path 最终收敛
- 哪些 path 在浪费时间

这个项目应优先采集 workflow telemetry，而不是 broad product analytics。

## 最有价值的 Data Categories

## 1. Workflow Execution Data

这是最有价值的一类，因为它能直接显示 harness 应该在哪些地方被改进。

采集：

- 用户从哪个 top-level entrypoint 启动
- 使用了哪种 task mode：prototype、Chapter 5、Chapter 6、repo scan、recovery
- 跑了哪些 major step
- 跳过了哪些 major step
- step duration
- step outcome：`ok | fail | blocked | skipped`
- failure class：`timeout | deterministic_fail | llm_needs_fix | artifact_integrity | planned_only | approval_pending | repo_noise | unknown`
- 收敛之前重跑了几轮
- 最终是 converged 还是 abandoned

这些 signal 可以直接用于改善：

- 默认 script parameter
- stop-loss rule
- fail-fast placement
- delivery profile default
- documentation order

## 2. Recovery And Resume Data

repository 高度依赖 sidecar-driven recovery，所以 recovery telemetry 是 first-class 类型。

采集：

- 用户是否使用 `resume-task`
- 是否使用 `chapter6-route`
- 是否使用 `inspect-run`
- 返回的 recommendation 是什么
- 用户是否遵循了 recommendation
- 遵循 recommendation 是否降低了 rerun cost
- 哪些 sidecar 被打开得最频繁
- 哪些 recovery recommendation 事后被证明是错的

这些 signal 可以直接用于改善：

- `chapter6-route`
- `resume-task`
- active-task summary
- sidecar prioritization
- artifact viewer 和 dashboard layout

## 3. Time, Cost, And Resource Data

这类 data 决定 user 是否真的会留下来。

采集：

- total task duration
- per-step duration
- deterministic 与 LLM 耗时分拆
- timeout 在哪一 step / reviewer 发生
- user abandon 之前反复等待了多久
- 当 API 与 CLI 同时使用时，`openai-api` vs `codex-cli` 的 cost 与 failure rate
- background task 的 completion rate

这些 signal 可以直接用于改善：

- timeout default
- API vs CLI routing policy
- reviewer selection policy
- prompt trimming
- asynchronous orchestration priority

## 4. Needs-Fix And Technical Debt Data

这类 data 用来解释 workflow 的真实 quality burden。

采集：

- 每个 task 中 `P0/P1/P2/P3/P4` finding 的数量
- 解决 `P0/P1` 花了多久
- `P2/P3/P4` 是否进入 technical debt
- 每个 finding 是哪个 reviewer 产生的
- 哪些 finding 在 task 之间反复出现
- 哪些 finding 事后被证明是 false positive

这些 signal 可以直接用于改善：

- review prompt
- needs-fix-fast strategy
- technical debt register structure
- reviewer weighting
- failure taxonomy

## 5. Prototype Lane Data

如果 prototype onboarding 是未来的 acquisition surface，那么这类 data 会非常重要。

采集：

- 用户是否从 prototype lane 起步
- 是否创建 prototype record
- 是否创建 prototype scene scaffold
- 是否使用 prototype TDD
- prototype 最终是 `discard | archive | promote`
- 从 prototype start 到 promote 的 average time
- prototype flow 最常卡在哪一天

这些 signal 可以直接用于改善：

- prototype 文档
- Day 2 scene scaffold
- prototype template
- promotion criteria
- new-user onboarding

## 6. Retention And User Journey Data

这类 data 对 product viability 很重要，但它的优先级仍低于 workflow telemetry。

采集：

- first successful run
- first playable scene created
- first prototype promoted
- first Chapter 6 task completed
- second-day return
- second project created
- first export completed

对这个项目来说，最好的 early retention metric 不是 page view，而是 workflow milestone。

## 7. Documentation And Help Usage Data

这类 data 不只用于改文档，也用于改代码。

采集：

- 哪些 docs 在 failure 前或 failure 后被打开
- 用户是否从 docs 里复制 commands 并执行成功
- 哪一章 workflow 被打开得最多
- 哪些 failure 会把用户引向 recovery docs
- 哪些 docs 被打开但没能帮助用户继续

这些 signal 可以直接用于改善：README structure、AGENTS routing、workflow chapter ordering、project-health dashboard link、error message remediation hint。

## 8. Project Shape And Template Adaptation Data

这类 data 用于决定 template 哪部分应该保持 generic，哪部分应该变成 optional preset。

采集：

- project genre 或 project type
- 是否仍然是 Windows-only
- 是 prototype-heavy 还是 Chapter-6-heavy
- clone 后用户移除了哪些 module
- 哪些 module 反复被加回来
- 哪些 top-level capability 从来没被使用

这些 signal 可以直接用于改善：template default、preset strategy、optional module、game-specific prototype scaffold。

## 9. Approval Workflow Data

这类 data 很重要，因为 cloud product 最终会在 browser 中暴露 approval，而 approval friction 很可能会在不知不觉中变成最大的 workflow delay 之一。

采集：

- approval 需要触发多少次
- approval status distribution：`pending | approved | denied | invalid | mismatched`
- 从 approval request 到 approval decision 花了多久
- `approved -> fork` 是否真的 converged
- `denied -> resume` 是否真的 converged
- 用户是否在没有 new evidence 的情况下反复掉入同一 approval loop
- `Forbidden commands` 是否才是真正的 blocker

这些 signal 可以直接用于改善：approval-sidecar structure、browser approval UX、fork vs resume policy、approval stop-loss rule、chapter routing stability。

## 10. Project-Health And Artifact Viewer Data

一旦 browser surface 出现，就很重要去知道：人们是否真的在使用 repository-native recovery substrate，还是仍然在盲目寻找路径。

采集：

- 用户在 task failure 之前或之后打开 project-health 的行为
- 哪些 project-health panel 被打开得最多
- 打开 `latest.html` 是否能引导 successful remediation
- 哪些 artifact view 被打开得最多：`active-task`、`latest.json`、`summary.json`、`repair-guide`、`agent-review`
- 用户是否从 artifact-linked next step 继续，还是直接放弃 task
- dashboard view 是否减少了重复 `inspect-run` 的使用

这些 signal 可以直接用于改善：dashboard information density、artifact index priority、recovery entrypoint ordering、latest.html layout、active-task summary design。

## 11. Bootstrap And Environment Failure Data

这类 data 在 Phase A 尤其重要，因为 hosted usability 取决于 worker 能否在不需 operator guesswork 的前提下准备好。

采集：

- first workspace bootstrap success/failure
- missing dependency class：`git | python | node | codex | dotnet | godot | env-var | auth`
- bootstrap check duration
- 每个 workspace 的 repeated bootstrap failure
- failure 是通过 documentation、automation 还是 operator intervention 解决的
- 用户是否在 first successful run 之前就 abandoned

这些 signal 可以直接用于改善：`workspace-bootstrap-check`、dependency layering、operator setup docs、hosted-worker image quality、first-run experience。

## 12. Export And Release Milestone Data

这一类不是最先要 instrument 的部分，但一旦 user 开始尝试 ship，而不只是 prototype，它就会变得有价值。

采集：

- first successful export
- export failure class
- first release-candidate task completion
- local hard checks 是否在 release 前通过
- release failure 是 deterministic、content-related 还是 review-related
- 用户多久会退回手动 release step

这些 signal 可以直接用于改善：release docs、release hard gate、export troubleshooting guidance、pre-release closure 的 profile default。

## 13. Profile, Mode, And Transport Segmentation

当 telemetry 按实际运行方式分段后，它的可操作性会大幅提高。

采集：

- `delivery_profile`：`playable-ea | fast-ship | standard`
- `task_mode`：`prototype | chapter5 | chapter6 | repo-health | recovery`
- transport mode：`codex-cli | openai-api | mixed`
- 这轮 run 使用的是 narrow closure 还是 full rerun
- 这轮 run 使用的是 recommendation-only 还是 execution mode

这些 signal 可以直接用于改善：profile default、API vs CLI routing policy、task-mode docs、按 mode 分段的 timeout 和 retry policy。

## 推荐的 Priority Order

如果 telemetry 必须分步实现，推荐的顺序是：

1. workflow execution data
2. recovery and resume data
3. time, cost, and resource data
4. needs-fix and technical-debt data
5. approval workflow data
6. bootstrap and environment failure data
7. prototype lane data
8. project-health and artifact-viewer data
9. retention milestone data
10. documentation usage data
11. project-shape data
12. export and release milestone data
13. profile, mode, and transport segmentation

## 最小 Event Set

如果一开始只能实现很小的 telemetry surface，请先采集这 10 个 event：

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

telemetry 只有在 event name 与 key field 足够稳定时，才真正有用。

请使用以下规则：

- event name 应以 verb 为主，并保持 repository-native，例如 `task_step_finished`，而不是 generic UI analytics name
- 一旦 dashboard 或 replay tool 依赖了某个 high-value event，就不要轻易 rename
- 不要让同一个 field 在不同 workflow mode 中承担多个含义
- 优先 additive evolution：添加新 field，而不是改变旧 field 的含义
- `status`、`failure_kind`、`delivery_profile`、`task_mode`、`transport_mode` 这类 field 应保持 enum-style，专门用于 machine decision
- 如果 field 只是 best-effort，应标记 optional，不要默默把 missing 当成 false
- 如果 field 会影响 dashboard、routing 或 future replay dataset，在修改前先文档化

最对 stability 敏感的 field 是：

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

推荐的 change rule：

1. 新 field 可以自由增加，只要它们显然是 optional
2. enum value 扩展要很谨慎，并在同一次 change 里文档化
3. removal 或 semantic redefinition 应被当成 protocol change，并需要 migration note

## 推荐的 Base Event Fields

只要现场可用，每个 telemetry event 都应尽量带上这些 field：

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

## Phase A 最小 Instrumentation Order

Phase A 不应以大而全的 analytics system 起步，而应以最小 event set 起步，只采集那些能改善 hosted workflow decision 的 event。

推荐的 implementation order：

1. `bootstrap_checked`
   - 记录在任何真实 task execution 之前，hosted worker 是否 ready
2. `task_started`
   - 记录 top-level entrypoint、profile、mode 和 transport
3. `task_route_decided`
   - 记录第一个 repository-native routing outcome，例如 `run-6.7`、`run-6.8`、`inspect-first` 或 stop-loss
4. `task_step_finished`
   - 记录各 major workflow stage 的 step duration 与 step outcome
5. `task_stop_loss_triggered`
   - 记录防止无谓 rerun 的准确 stop-loss family
6. `approval_updated`
   - 记录 `pending`、`approved`、`denied`、`invalid`，以及选择的 next action
7. `task_completed`
   - 记录 task 是 converged、abandoned，还是被转成 residual 或 technical debt

只有在这些 event 稳定之后，Phase A 才需要再添加：

- `artifact_view_opened`
- `project_health_opened`
- `needs_fix_generated`
- `prototype_record_created`
- `prototype_promoted`
- export 和 release milestone event

规则很简单：先 instrument decision 和 convergence，再 instrument 一般产品行为。

## 哪些内容最可操作

最 actionable 的 telemetry field 是：

- `entrypoint`
- `step`
- `duration_sec`
- `status`
- `failure_kind`
- `recommended_next_action`
- `user_followed_recommendation`
- `rerun_count`
- `final_outcome`

这些 field 已经足够用于改 scripts、defaults、routing 和 docs。

## 不要优先做的事

如果没有非常充分的理由，不要过早优先采集：

- full raw chat transcript
- full prompt body
- 专门用于 analytics 的 full diff
- telemetry 目的下的 raw code snapshot
- 细粒度 cursor 或 clickstream logging
- 与 workflow result 脱节的 generic page-view analytics

这些在 privacy、storage、interpretation 成本上都很高，但往往不如 structured workflow signal 有价值。

## Event Producer And Consumer Map

下表把推荐 telemetry event 映射到 repository-native 的 producer 与 consumer。它故意保持 script-oriented，这样 Phase A 可以在不创造第二个 workflow engine 的前提下加入 telemetry。

| Event | Producer | Consumer | Phase | Notes |
|---|---|---|---|---|
| `bootstrap_checked` | future `workspace-bootstrap-check`, hosted runner bootstrap wrapper | hosted UI, operator setup dashboard, cloud worker readiness checks | Phase A | 应在真实 task execution 前运行，捕获 missing dependency class 与 readiness status。 |
| `task_started` | future `run-hosted-task`, `dev_cli.py run-single-task-chapter6`, `run_single_task_chapter6_lane.py` | hosted run list, task execution page, cost dashboard | Phase A | 捕获 entrypoint、task id、profile、mode、transport、branch、workspace id。 |
| `task_route_decided` | `dev_cli.py chapter6-route`, `run_single_task_chapter6_lane.py` | hosted recovery page, route replay dataset, task execution page | Phase A | 保留 `preferred_lane`、`chapter6_next_action`、stop-loss reason、forbidden commands 等 repository-owned field。 |
| `task_step_finished` | `run_review_pipeline.py`, `run_single_task_chapter6_lane.py`, `run_single_task_light_lane.py`, `dev_cli.py` wrapper | task timeline, timeout dashboard, workflow bottleneck analysis | Phase A | 一开始只记 major step，避免过度 per-command noise。 |
| `task_stop_loss_triggered` | `chapter6-route`, `run_single_task_chapter6_lane.py`, `llm_review_needs_fix_fast.py`, `run_review_pipeline.py` | stop-loss dashboard, recovery page, route tuning review | Phase A | 记录准确 family：`planned_only`、`artifact_integrity`、`rerun_guard`、`llm_retry_stop_loss`、`sc_test_retry_stop_loss`、`repo_noise`、`waste_signals`。 |
| `approval_updated` | `sc_repair_approval.py`, future hosted approval sync script | browser approval UI, route controller, audit view | Phase A | 记录 status、decision、reason，以及 next action 是 fork 还是 resume。 |
| `task_completed` | future `run-hosted-task`, `run_single_task_chapter6_lane.py`, `run_review_pipeline.py` | project progress dashboard, retention milestone, convergence analysis | Phase A | 记录 `converged | abandoned | residual_recorded | technical_debt_recorded`。 |
| `artifact_view_opened` | hosted web API / browser UI | artifact viewer analytics, dashboard layout review | Phase A+ | UI-owned event，不要让 repository script 依赖它。 |
| `project_health_opened` | hosted web API / browser UI, `project-health-scan` wrapper when run from UI | project-health dashboard, remediation analysis | Phase A+ | 当 project-health page 对 user 可见后，这个 event 才有意义。 |
| `needs_fix_generated` | `run_review_pipeline.py`, `llm_review_needs_fix_fast.py`, `agent_to_agent_review.py` | technical debt analytics, reviewer effectiveness dashboard | Phase A+ | 记录 severity distribution 和 producer reviewer，默认避免 raw prompt/body。 |
| `prototype_record_created` | `dev_cli.py` prototype helper, future hosted prototype entrypoint | prototype funnel dashboard | Phase A+ | 应挂到 prototype slug，而不是 raw design text。 |
| `prototype_scene_created` | prototype scene scaffold script / `run-prototype-tdd` helper | prototype onboarding dashboard | Phase A+ | 记录是否真的创建了 Godot scene。 |
| `prototype_tdd_run_finished` | `dev_cli.py run-prototype-tdd` | prototype TDD dashboard, new-user onboarding review | Phase A+ | 记录 stage：`red | green | refactor`、status、duration、failure kind。 |
| `prototype_promoted` | prototype promotion script 或 formal task creation step | prototype-to-task funnel, retention milestone | Phase A+ | 记录 promote/kill/archive decision，而不是 full raw prototype content。 |
| `export_finished` | future hosted release/export wrapper, local hard-check release wrapper | release dashboard, export troubleshooting | Later | 当 export flow 成为真实 hosted user journey 之后再加。 |

implementation rule：

- repository script 生产 workflow telemetry，记 decision、run、sidecar、stop-loss、approval 和 task outcome
- hosted UI/API 生产 interaction telemetry，记 artifact view、dashboard open、user 是否跟进
- 两边都不要重复对方的 decision logic
- 如果 event 需要 repository truth，就应该由 repository-native script 或 sidecar 产生或推导
- 如果 event 只是描述 user navigation，就应保留在 hosted UI/API 层

## Privacy And Collection Boundary

优先 structured summary，而不是 raw user content。

默认规则：

- 采集 workflow state
- 采集 step outcome
- 采集 duration
- 采集 recommendation/follow decision
- 避免存储不必要的 raw content

这样做更安全，也更 actionable。

## 直接反哺 Repository Evolution 的闭环

telemetry 只有在能反哺具体 repository change 时才有用。

每一次 telemetry review cycle 都应该问：

1. 哪一个 step 浪费了最多 user 总时间？
2. 哪一类 stop-loss 防止了最多无谓 rerun？
3. 哪一类 stop-loss 仍然太弱？
4. 哪一条 recommendation 最常被忽略？
5. 哪一条 recommendation 被采纳了，但仍然失败？
6. 新 user 在 prototype flow 的哪一阶段最容易卡住？
7. 哪些 docs 被打开，但没能帮助用户成功继续？
8. 哪些 script 应该更轻、更严、或更 top-level？

## 推荐的 Review Cadence

一旦有了真实 user，推荐以三个 cadence 回看 telemetry：

- weekly：failure、timeout、stop-loss、recovery usage
- monthly：retention milestone、prototype promotion pattern、project-shape trend
- release-by-release：parameter default、entrypoint change、workflow 与 doc rewrite

## 推荐的 Future Additions

如果 hosted product 继续增长，可以后续考虑这些新增项：

- 用于改进 `chapter6-route` 的 route decision replay dataset
- prototype funnel dashboard
- reviewer effectiveness dashboard
- task convergence dashboard
- per-profile cost 与 success-rate comparison
- approval-loop dashboard
- bootstrap-failure dashboard
- project-health remediation dashboard
- doc-to-command conversion dashboard

## 一句话规则

最有价值的 cloud data，是结构化证据：它用来说明 user 是如何在 workflow 中移动的、卡在了哪里、以及哪些 repository-native decision 在省时间，哪些在浪费时间。
