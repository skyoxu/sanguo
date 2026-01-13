# overlays 编写与维护指南（本项目口径）

本指南面向当前仓库（Windows-only Godot 4.5 + C#）。目标是让 overlays 成为“可执行规范”的载体：能被任务视图引用、能被脚本确定性校验、能与 Contracts/测试证据链对齐，并且避免口径漂移。

## 0. 核心结论（先记住这几条）

1) overlays 不是 PRD 的复制粘贴，也不是 Tasks 的替代；它是“功能纵切（08）”的落点，强调边界、事件、验收与测试证据链。
2) 08 章只写在 overlays：`docs/architecture/overlays/<PRD-ID>/08/`；Base 不写具体模块内容。
3) 合约（Contracts）SSoT 在代码：`Game.Core/Contracts/**`；文档只引用路径与 EventType，不复制字段定义。
4) 任务语义 SSoT 在任务视图：`.taskmaster/tasks/tasks_back.json`、`.taskmaster/tasks/tasks_gameplay.json`；overlays 必须可被这些文件回链引用并通过脚本校验。
5) 阈值/策略（安全、可观测性、质量门禁）以 Base + Accepted ADR 为准；overlays 只引用，不复制。

## 1. overlays 的目录结构（固定）

每个 PRD-ID 一套 overlays（只建议一个 08 目录）：

```
docs/
  architecture/
    overlays/
      <PRD-ID>/
        08/
          _index.md
          ACCEPTANCE_CHECKLIST.md
          08-feature-slice-<topic>.md
          08-tNN-<task-slug>.md
          08-Contracts-*.md
```

命名建议：

- 文件名使用英文（路径稳定、避免 CI/Windows 的编码与差异比较风险）。
- 标题/正文使用中文（便于团队阅读）。
- 按任务拆页时，优先 `08-t50-...md` 这种“按 Task ID 可定位”的命名。

## 2. front matter 约束（哪些必须有）

### 2.1 `_index.md`（建议有）

`_index.md` 用于导航与口径提示，建议包含 front matter（字段不强制，但推荐）：

```md
---
PRD-ID: <PRD-ID>
Title: 08 章功能纵切索引（契约与测试对齐）
Updated: true
Arch-Refs:
  - CH01
  - CH03
---
```

### 2.2 `ACCEPTANCE_CHECKLIST.md`（必须有，且字段必须齐）

该文件会被校验脚本检查（确定性门禁），必须包含 YAML front matter，且至少包含：

- `PRD-ID`
- `Title`
- `Status`
- `ADR-Refs`
- `Test-Refs`

示例：

```md
---
PRD-ID: <PRD-ID>
Title: <你要的标题>
Status: Accepted
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0019
Arch-Refs:
  - CH01
  - CH06
Test-Refs:
  - Game.Core.Tests/...
---
```

注意：

- `ADR-Refs` 必须指向 `docs/adr/ADR-*.md` 实际存在的 ADR。
- Checklist 的正文应只写“检查清单”，不要复制阈值/策略（引用 ADR/CH 即可）。

### 2.3 其他 08 页面（可选但推荐）

其他 08 页面建议包含 front matter，至少标记：

- `PRD-ID`
- `Title`
- `Status`
- `ADR-Refs`（至少 1 条 Accepted ADR）
- `Arch-Refs`（至少 1 个 CH）

可选扩展字段（当前不建议做硬门禁）：

- `Intent`：Index/Checklist/Overview/FeatureSlice/Contracts
- `SSoT`：task_views / contracts / code
- `Tags`：用于搜索过滤（谨慎；一旦变成硬门禁就会引入大量维护成本）

## 3. overlays 08 应该写什么（写作边界）

overlays 的价值是“能落地且可审计”。建议每页只写以下 4 类信息：

1) 范围/非目标：止损边界（避免模块无限膨胀）。
2) 确定性输入：配置路径、seed、选项档位（保证可复现与可测）。
3) 事件口径（ADR-0004）：只列 `EventType` + 触发点，不在文档复制字段定义。
4) 验收条款与证据链：验收条款必须能落到任务视图的 `acceptance[]`，并通过测试文件 `Refs:` 与 `ACC:T<id>.<n>` anchors 证明。

禁止项（高频踩坑）：

- 把 Base/ADR 的阈值/策略复制进 overlays（会漂移）。
- 把 Contracts 的字段定义复制进 overlays（会漂移）。
- 把“实施步骤/命令/个人操作习惯”写成验收条款（应放到 `test_strategy` 或 workflow 文档）。

## 4. Contracts 与事件命名（必须对齐）

### 4.1 事件命名规则

事件命名遵循 ADR-0004（CloudEvents-like `type`）：

- 领域事件：`core.sanguo.*`
- UI 事件：`ui.*`
- Screen/状态切换：`screen.*`

### 4.2 合约落盘位置

Contracts（事件/DTO/接口）只落盘到：

- `Game.Core/Contracts/**`（纯 C#，不依赖 Godot API）

overlays 只做引用：

- 写 `EventType`
- 写触发点
- 写契约文件路径（例如 `Game.Core/Contracts/Sanguo/EconomyEvents.cs`）

### 4.3 契约口径（SSoT 摘要版）

本节把当前仓库中“关于契约文件应该怎么写/怎么用”的规则，收敛成一份可执行的摘要口径（避免多人各写一套）。

**SSoT 与禁止项**

- SSoT：契约的单一事实来源是 `Game.Core/Contracts/**`；文档与任务视图只引用，不复制字段定义。
- 禁止：在 overlays/PRD 中复制粘贴契约字段（会漂移）；在业务代码/测试里散落魔法字符串 `type`（会漂移）。
- contractRefs 的定位：任务视图里的 `contractRefs[]` 只记录本任务关心的 **领域事件 EventType**（不列 DTO 字段，不列实现细节）。

**事件命名与最小字段**

- 事件 `type` 是稳定标识（CloudEvents-like），必须来自契约常量 `EventType`（参考 ADR-0004 与 `08-Contracts-CloudEvents-Core.md`）。
- `DomainEvent` 的最小字段集合遵循“CloudEvents 1.0 最小子集思想”，并要求 `time` 语义一致（同 `source` 的一致性约束）。
- 当需要新增字段时：优先在契约记录类型（record/class）上加显式字段；避免 `object/dynamic` 等弱类型。

**分层与依赖**

- Contracts 不得依赖 `Godot.*` 命名空间，保持纯 .NET 可单测；与 Godot 交互只发生在 Adapter/Scene 层。
- UI 相关事件（`ui.*`、`screen.*`）不进入领域 Contracts 的 “core.*” 范畴；领域事件只用 `core.sanguo.*`。

**验收与证据链**

- 任何新增/变更契约，必须同步更新：
  - overlays：列出 `EventType` + 触发点 + 契约文件路径
  - 任务视图：更新相关任务的 `contractRefs[]` 与 `Refs:`/`test_refs[]`
  - 测试：在对应测试方法旁落 `ACC:T<id>.<n>` anchors，保证条款可审计

### 4.4 相关文档与脚本入口（建议顺序）

用于“理解口径（先）→ 校验回链（后）”：

1) 口径文档（引用型）：
   - `docs/adr/ADR-0004-event-bus-and-contracts.md`
   - `docs/architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-CloudEvent.md`
   - `docs/architecture/overlays/PRD-SANGUO-T2/08/08-Contracts-CloudEvents-Core.md`
2) 契约目录（脚本生成，用于开工前对齐，非 SSoT）：
   - `docs/workflows/contracts-catalog-prd-sanguo-t2.md`
   - 生成脚本：`py -3 scripts/python/generate_contracts_catalog_prd_sanguo_t2.py`
3) 确定性校验（防漂移）：
   - `py -3 scripts/python/validate_contracts.py`
   - `py -3 scripts/python/task_links_validate.py`
   - `py -3 scripts/python/validate_task_overlays.py`

## 5. 任务视图如何引用 overlays（强制绑定规则）

任务视图文件：

- `.taskmaster/tasks/tasks_back.json`（全量视图）
- `.taskmaster/tasks/tasks_gameplay.json`（玩法视图）

每个任务建议固定包含：

- `overlay_refs` 至少包含：
  - `docs/architecture/overlays/<PRD-ID>/08/_index.md`
  - `docs/architecture/overlays/<PRD-ID>/08/ACCEPTANCE_CHECKLIST.md`
  - 该任务对应的纵切页（例如 `08-t50-...md`）
- `contractRefs`：本任务关心的领域事件 `EventType`（只列 type，不列字段）。
- `acceptance[]`：每条验收条款以 `Refs: <repo-relative-test-path>` 结尾。
- `test_refs[]`：包含 acceptance 中所有 `Refs:` 的并集。

## 6. 如何创建一套新的 overlays（一步步）

以新 PRD-ID（示例：`PRD-XXX`）为例：

1) 建目录：
   - `docs/architecture/overlays/PRD-XXX/08/`
2) 写索引：
   - `docs/architecture/overlays/PRD-XXX/08/_index.md`
3) 写验收清单：
   - `docs/architecture/overlays/PRD-XXX/08/ACCEPTANCE_CHECKLIST.md`（front matter 必填）
4) 写纵切页：
   - 玩法闭环：`08-feature-slice-...md`
   - 按任务拆页：`08-tNN-...md`
5) 回填任务视图（最关键）：
   - 把每个 Task 的 `overlay_refs` 指到 `_index.md`、`ACCEPTANCE_CHECKLIST.md`、以及该任务对应页。
6) 跑确定性校验（见下一节），确保回链不漂移。

## 7. 推荐的确定性校验（Windows）

执行顺序建议：

1) overlays 回链与 checklist schema：
   - `py -3 scripts/python/validate_task_overlays.py`
2) 任务回链与引用完整性：
   - `py -3 scripts/python/task_links_validate.py`
   - `py -3 scripts/python/audit_task_ref_integrity.py`
3) 文档编码与疑似乱码扫描（取证 + 防 PR 乱码）：
   - `py -3 scripts/ci/check_encoding_issues.py`

取证要求：

- 所有输出统一落到 `logs/ci/<YYYY-MM-DD>/`（详见 `AGENTS.md` 6.3）。

## 8. 常见问题（止损建议）

### 8.1 要不要给每个 overlay 页面强插“用途边界/变更影响面”？

当前建议：不要全量回写历史页（收益不够、diff 太大、冲突风险高）。更稳的做法是：

- 在 `_index.md` 与 `ACCEPTANCE_CHECKLIST.md` 写清楚边界与影响面；
- 新增页面按模板写（自带边界/影响面段落），不要强制重排旧页面。

### 8.2 overlays 单页还是多页？

优先多页（按 Task ID 拆页），好处：

- 回链稳定：任务视图能指向“唯一页”，避免多人同时改同一个大页导致冲突。
- 搜索与审计更清晰：每页聚焦 1 个任务或 1 个模块边界。
