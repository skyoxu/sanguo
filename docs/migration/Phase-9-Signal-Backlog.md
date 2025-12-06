# Phase 9 Backlog — Signal System（事件总线与信号系统）

> 状态：Backlog（非当前模板 DoD，供后续项目按需选择）
> 目的：承接 Phase-9-Signal-System.md 中暂未在当前模板落地的增强项，避免“文档要求”和“实际实现”脱节，同时为后续项目提供可选优化列表。
> 相关 ADR：ADR-0004（事件总线与契约）、ADR-0006（数据存储）、ADR-0023（Settings SSoT）
> 代码范围：Game.Core（事件总线）、Game.Godot/Adapters、Game.Godot/Scripts、Tests.Godot

---

## B1：事件命名统一迁移（`game.*` → `core.*.*`）

- 现状：
  - 测试中仍存在早期事件命名，仅作为示例与兼容：
    - `game.started`  （Game.Core.Tests/Engine/GameEngineCoreEventTests.cs:58）
    - `score.changed` （Game.Core.Tests/Engine/GameEngineCoreEventTests.cs:74）
    - `player.health.changed`（Game.Core.Tests/Engine/GameEngineCoreEventTests.cs:90）
  - Main.gd 等运行时代码已采用新规范事件（例如 `core.score.updated`），旧事件只出现在测试中。
- 目标：
  - 将上述旧事件类型统一迁移为新规范：
    - `game.started`          → `core.game.started`
    - `score.changed`         → `core.score.updated`
    - `player.health.changed` → `core.player.health.updated`
  - 对于确有需要的示例/兼容场景，保留清晰注释，避免误用旧命名作为 SSoT。
- 影响范围（示例）：
  - Game.Core.Tests/Engine/GameEngineCoreEventTests.cs
  - 相关 GdUnit4 用例，如 HUD/Main 等，如有依赖旧事件名需一并迁移。
- 优先级：P1（建议在正式引入更多领域事件前完成，避免后续项目复制旧命名）。

---

## B2：Signal XML 文档注释补全

- 现状：
  - 规范要求：对外暴露的关键 Signal（尤其是适配层与 UI/Glue 层）应具备 XML 文档注释，至少包含 `<summary>` 和 `<param>` 描述。
  - 当前示例（存在缺失）：
    - Game.Godot/Adapters/EventBusAdapter.cs：公开 DomainEventEmitted Signal，缺少 XML 注释。
    - Game.Godot/Adapters/Security/SecurityHttpClient.cs：与安全相关的 Signal 缺少 XML 注释。
    - Game.Godot/Scripts/UI/Modal.cs：UI 模态框相关 Signal 缺少 XML 注释。
- 目标：
  - 为模板中“对外可见”的 Signal 补齐 XML 文档注释，解释用途、参数含义与典型使用方式。
  - 先覆盖 EventBusAdapter 与核心 UI/Glue 信号，避免一次性要求所有内部信号全部补齐。
- 优先级：P1–P2（提升可读性与模板教学价值，但不阻塞当前 DoD）。

---

## B3：Signal 性能基准测试（Signal Performance Benchmark）

- 现状：
  - Phase-9 文档中给出了信号性能基准示例与目标阈值，例如：
    - 单订阅者 100k 次发射 < 50ms
    - 10 个订阅者 100k 次发射 < 200ms
  - 仓库当前尚未实现对应的性能测试脚本/用例：
    - 未发现 SignalPerformanceTest.cs 或类似测试。
- 目标：
  - 在 Godot+C# 环境下给出一份“可运行的参考性能测试”，用于说明信号系统在典型负载下的表现；
  - 该测试作为文档示例和手动对比基准，不强制进入 CI 硬门禁。
- 建议实现方式：
  - 在 Game.Godot.Tests 或 Tests.Godot 下新增：
    - Performance/SignalPerformanceTest.cs 或等价测试；
  - 通过 Godot 场景或纯 C# 测试点触发大量信号发射并统计耗时，结果写入 logs/perf（参考 Phase 7 标准）。
- 优先级：P2（适合作为后续性能优化与演示用例，不阻塞模板当前使用）。

---

## B4：CI Signal 合规检查工作流（Signal Compliance Workflow）

- 现状：
  - Phase-9 文档中展示了 `.github/workflows/signal-compliance.yml` 的概念示例，但当前仓库尚未真正启用该工作流：
    - 未发现专门的 Signal 命名约定检查 Job；
    - 未启用针对 [Signal] 命名和 XML 文档注释的自动检查脚本。
- 目标：
  - 为需要更严格治理的后续项目提供一套可复用的 CI 工作流：
    - 检查 Signal 命名是否符合约定（如 Handler 后缀、前缀分类等）；
    - 检查公共信号是否具备 `<summary>` XML 注释。
- 建议实现方式：
  - 基于 Phase-9 文档中的 YAML 示例，抽象为可配置的 GitHub Actions 工作流；
  - 初期作为 Quality Gate 的“提示项”（失败只告警、不阻断），待成熟后再视项目需要收紧为硬门禁；
  - 与现有 Windows CI / Windows Quality Gate 工作流保持风格统一（Windows-only + Python 驱动）。
- 优先级：P2（适合在模板稳定后再逐步接入）。

---

## B5：GDScript 订阅生命周期管理

- 现状：
  - C# 层通过 `Subscribe()` 返回 IDisposable 以便显式取消订阅；
  - GDScript 层通过 `connect()` / `disconnect()` 管理信号；
  - 当前部分 Glue 节点（例如 Main.gd）在 `_ready()` 中连接 `/root/EventBus` 的 `DomainEventEmitted`，
    之前主要依赖 Godot 节点销毁时的自动清理机制，未显式在 `_exit_tree()` 中调用 `disconnect()`。
- 当前模板状态：
  - Main.gd 已新增 `_exit_tree()` 中的显式断订阅逻辑：
    - 在节点退出场景树时获取 `/root/EventBus`；
    - 检查是否已连接 `DomainEventEmitted`；
    - 若已连接则调用 `disconnect()` 断开。
  - 该实现作为“模板级示例”，为后续 Glue 节点提供参考。
- 后续可选工作：
  - 根据需要，将同样的模式推广到其他订阅 `/root/EventBus` 的 GDScript 节点；
  - 在 Phase-9 文档中增加“订阅生命周期示例”片段，用于指导新场景编写。
- 优先级：P3（当前示例已覆盖典型场景，进一步推广可视项目复杂度而定）。

---

## 使用说明

- 对于基于本模板创建的新项目：
  - 建议在正式引入复杂业务前，优先评估并完成 B1（事件命名统一迁移），避免继续复制旧事件命名；
  - B2–B4 可根据团队对文档、性能和 CI 管控的需求逐步启用；
  - B5 可作为“代码整洁度优化项”，在重构 Glue 层时一并处理。

- 对于模板本身：
  - 当前 Phase 9 已通过 ADR-0004 与 Phase-9-Signal-System.md 完成 P0 基线，
    本 Backlog 文件仅记录可选增强项，避免形成隐性技术债。

