---
PRD-ID: PRD-SANGUO-T2
Title: 08-功能纵切-T2-治理、发布与质量门禁骨架（T31–T49）
Status: Accepted
ADR-Refs:
  - ADR-0003
  - ADR-0005
  - ADR-0008
  - ADR-0011
  - ADR-0015
  - ADR-0019
Arch-Refs:
  - CH03
  - CH07
  - CH09
  - CH10
---

# 08-功能纵切-T2-治理、发布与质量门禁骨架（T31–T49）

## 8.x 范围与上下文

本页承接 T2 阶段中不直接形成单一玩法 UI、但会落地为脚本、CI、发布工作流、安全护栏与质量门禁的历史任务。
这些任务不应仅由 `_index.md` 或 `ACCEPTANCE_CHECKLIST.md` 充当 owner 页，否则会形成“索引页拥有语义”的假回链。

## 8.x.1 显式 Owner Anchors

### 可观测性、性能与质量门禁

- `T31`：在 `Game.Core` 落地性能追踪入口，并接入 CI 性能门禁与报告汇总。
- `T32`：建立 Observability Autoload 与 Sentry Release Health Gate 的运行时与 CI 闭环。
- `T37`：提供 `Game.Core` 可复用的 observability client 与结构化日志落盘口径。
- `T38`：建立重复率与圈复杂度质量门禁，并把失败结果收敛到统一质量入口。
- `T39`：校验性能 P95 与审计 JSONL 产物，确保软门与硬门结果都可被 CI 消费。
- `T40`：验证 Signal 健康度与安全相关测试门禁，阻止接线回归进入主分支。
- `T41`：将性能报告与历史追踪产物收敛到固定目录结构，支持跨 run 对比。
- `T42`：提供独立性能门禁工作流，使性能回归可以脱离常规流水线单独追踪。
- `T45`：建立架构依赖护栏与依赖图校验骨架，避免 Core、Adapter、UI 反向侵入。
- `T47`：扩展 `quality_gates.py`，统一覆盖率阈值与 GdUnit4 集成门禁。

### 构建、发布与验收工作流

- `T33`：整合 Python 构建驱动脚本与 Windows Release Workflow，作为发布流水线入口。
- `T34`：提供分阶段发布与回滚脚本骨架，覆盖 Canary/Stable 的最小切换路径。
- `T35`：建立项目级功能验收与文档整合骨架，使任务、Overlay、测试与工件对齐。
- `T43`：固化代码签名与安全分发流程，避免未签名构建进入可发布路径。
- `T44`：维护导出预设与多配置支持，确保不同运行配置的导出可重复。
- `T46`：封装 Python 版 headless smoke，并提供 strict 模式开关以提升 CI 稳定性。
- `T49`：增强 strict smoke 的自退出与 marker 真实性，避免假阳性通过。

### 安全适配与运行护栏

- `T48`：增强 Godot 安全适配层，覆盖外链白名单、文件访问与 `OS.execute` 守卫。

## 8.x.2 路由与边界

- 本页负责 `T31`、`T32`、`T33`、`T34`、`T35`、`T37`、`T38`、`T39`、`T40`、`T41`、`T42`、`T43`、`T44`、`T45`、`T46`、`T47`、`T48`、`T49` 的治理类 owner 语义。
- `T36` 仍由 `08-feature-slice-t2-monopoly-loop.md` 持有，因为它直接涉及闭环 runtime 事件命名迁移。
- 本页只定义治理职责与回链口径，不复制 Base 章节里的阈值与策略细节。

## 8.x.3 验收引用

- 质量与 CI 入口：`scripts/python/quality_gates.py`
- Overlay 校验：`scripts/python/validate_task_overlays.py`
- 全量回链校验：`scripts/python/check_tasks_all_refs.py`
- 编排与发布脚本：`scripts/sc/build.py`、`scripts/python/smoke_headless.py`
