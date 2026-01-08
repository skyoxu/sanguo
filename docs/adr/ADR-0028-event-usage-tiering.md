# ADR-0028: 事件用途分级（Gameplay vs UI vs Audit/Observability）

- Status: Accepted
- Context: 当前项目同时使用事件做“玩法骨干（回合/经济/移动）”、UI 意图（按钮/交互）、以及审计/可观测（安全审计、诊断、回放线索）。如果不做用途分级与约束，上层（UI/Glue/测试）会靠猜事件语义，导致：误把 UI 事件当玩法事实、误把审计事件当必需链路、或把玩法关键事件做成 best-effort，造成可玩性与回归不稳定。

## Decision

### 1) 三类事件（必须选其一）

1. **玩法事实事件（Gameplay Domain Events）**
   - 前缀建议：`core.${DOMAIN}.***`
   - 含义：描述“已经发生”的玩法事实（可用于回放、UI 展示、AI 推断）。
   - 约束：
     - 必须在 Core（Game.Core）内定义契约与 EventType 常量（SSoT：`Game.Core/Contracts/**`，见 ADR-0020）。
     - 由 Core 服务层发布（例如 Turn/Economy），发布顺序必须可回归（必要时在 Contracts 中显式定义顺序规则）。
     - **调用方必须 `await PublishAsync`**：玩法链路以确定性为优先，避免“逻辑继续推进但观察者未收到事件”的隐性分叉。
     - 订阅者不得修改 Core 领域状态（只读消费），避免跨线程/跨层副作用（与 ADR-0030 对齐）。

2. **UI 意图事件（UI Intent Events）**
   - 前缀建议：`ui.${DOMAIN}.***` 或 `ui.menu.*` / `ui.hud.*`
   - 含义：描述“用户/界面请求做某事”，不是玩法事实。
   - 约束：
     - UI 事件必须由 Glue 层消费并转换为 Core 调用（或触发 Core 服务），禁止 UI 直接修改 Core 状态。
     - UI 意图事件允许 best-effort（例如使用 `PublishSimple`），但**必须存在至少一条“被 Glue 消费”的可观测证据**（GdUnit4 冒烟即可）。
     - UI 事件不得作为回放/结算依据；回放依据必须来自玩法事实事件。

3. **审计/可观测事件（Audit/Observability Events）**
   - 前缀建议：`runtime.*` / `security.*`（或审计 JSONL 记录）
   - 含义：用于诊断、取证、性能、发布健康；不应改变玩法结果。
   - 约束：
     - 必须是 best-effort：失败不应阻塞玩法闭环。
     - 失败必须可见（日志/错误上报），以便 acceptance_check 与排障回溯（与 ADR-0003/0019/0026 对齐）。
     - 审计落盘遵循 `logs/**` 口径（见 AGENTS.md 6.3）。

### 2) 发布语义与失败边界

- 订阅者异常隔离、发布失败可见：沿用 ADR-0026。
- 玩法事实事件：发布失败视为“本次操作失败”，上层必须以“不中断进程但不中断语义”处理（例如拒绝继续推进/回到可恢复状态）。
- 审计/可观测事件：发布失败仅影响取证，不影响玩法结果。

## Consequences

- 正向：减少“UI/玩法/审计”混用导致的语义漂移；提高回归稳定性；更容易为 llm_review/acceptance_check 提供结构化证据链。
- 代价：需要在任务验收与代码评审中明确标注事件类别；新增事件需先选类别再落地契约与测试。

## References

- ADR-0004: 事件总线与契约
- ADR-0020: 契约落盘位置标准化
- ADR-0026: 事件发布失败策略
- ADR-0030: Core 线程模型与跨线程边界

