---
PRD-ID: PRD-SANGUO-T2
Title: T2 功能纵切实现验收清单
Status: Accepted
ADR-Refs:
  - ADR-0004
  - ADR-0005
  - ADR-0015
  - ADR-0018
  - ADR-0019
  - ADR-0020
  - ADR-0021
  - ADR-0024
  - ADR-0025
Test-Refs:
  - Game.Core.Tests/Domain/CityTests.cs
  - Game.Core.Tests/Domain/SanguoPlayerTests.cs
  - Game.Core.Tests/Domain/SanguoContractsTests.cs
  - Game.Core.Tests/Services/EventBusTests.cs
---

# PRD-SANGUO-T2 功能纵切实现验收清单

## 项目基本信息

- PRD ID: PRD-SANGUO-T2
- 目标: T2 最小可玩闭环（掷骰→移动→买地/付费→时间推进→轮到谁）
- 平台: Windows only（Godot 4.5.x + C#）
- 核心约束: 领域逻辑在 `Game.Core/`，不依赖 Godot API，可用 xUnit 单测快速验证

## 一、文档完整性验收

- [ ] Overlay 索引存在且链接可点击: `docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md`
- [ ] 玩法闭环文档存在: `docs/architecture/overlays/PRD-SANGUO-T2/08/08-功能纵切-T2-三国大富翁闭环.md`
- [ ] 城池所有权模型文档存在: `docs/architecture/overlays/PRD-SANGUO-T2/08/08-t2-city-ownership-model.md`
- [ ] 本验收清单存在并被索引引用: `docs/architecture/overlays/PRD-SANGUO-T2/08/ACCEPTANCE_CHECKLIST.md`

## 二、架构设计验收

### 2.1 架构追溯验收（Tasks ↔ ADR/CH/Overlay）

- [ ] 每个会落地为代码/测试的任务均满足:
  - [ ] `adrRefs` 至少 1 个 Accepted ADR
  - [ ] `archRefs` 至少 1 个 Base 章节引用（CH01/CH03/CH04/CH05/CH06/CH07/CH09/CH10 等）
  - [ ] `overlay` 或 `overlay_refs` 指向 `docs/architecture/overlays/PRD-SANGUO-T2/08/` 下文件
- [ ] 校验脚本通过（Windows）:
  - `py -3 scripts/python/task_links_validate.py`
  - `py -3 scripts/python/validate_task_overlays.py`

### 2.2 契约与事件口径（引用型）

- [ ] 事件命名遵循 ADR-0004（示例: `core.sanguo.game.*` / `core.sanguo.city.*`），禁止魔法字符串散落
- [ ] 现有契约文件可覆盖 T2 闭环所需的“掷骰/移动/买地/付费/回合推进”等事件类型:
  - `Game.Core/Contracts/Sanguo/GameEvents.cs`
  - `Game.Core/Contracts/Sanguo/BoardEvents.cs`
  - `Game.Core/Contracts/Sanguo/EconomyEvents.cs`
- [ ] 契约巡检脚本通过:
  - `py -3 scripts/python/check_sanguo_gameloop_contracts.py`
  - `py -3 scripts/python/validate_contracts.py`

## 三、代码实现验收

### 3.1 领域不变式验收（城池所有权与出局）

以下规则必须由 xUnit 钉死，且实现与文档一致（见 `08-t2-city-ownership-model.md`）:

- [ ] 所有权 SSoT: `City` 不持有 Owner；所有权由 `SanguoPlayer.OwnedCityIds` 表示
- [ ] 过路费支付资金不足:
  - [ ] 剩余资金全额转给债权人
  - [ ] 支付方资金归零
  - [ ] 支付方出局并锁定（不可再交易）
  - [ ] 支付方释放全部城池为无人占领（清空 OwnedCityIds）
- [ ] 已出局玩家不可再进行买地/付费等交易行为

建议的最小测试引用（必须覆盖上述不变式）:

- `Game.Core.Tests/Domain/SanguoPlayerTests.cs`
- `Game.Core.Tests/Domain/CityTests.cs`

### 3.2 契约与分层（不新增契约前提下）

- [ ] Contracts 仅位于 `Game.Core/Contracts/**`，且不依赖 Godot API
- [ ] 事件类型常量来自 Contracts（例如 `Sanguo*.EventType`），禁止魔法字符串散落到领域实现/测试中

## 四、测试框架验收

- [ ] 编译门禁（禁止警告）:
  - `dotnet build GodotGame.csproj -warnaserror`
- [ ] 单元测试与覆盖率门禁（口径引用 ADR-0005）:
  - `dotnet test --collect:"XPlat Code Coverage"`
  - 或: `py -3 scripts/python/run_dotnet.py --solution Game.sln --configuration Debug`
- [ ] 文档编码巡检（UTF-8、无语义乱码、无 Emoji，fixture 除外）:
  - `py -3 scripts/ci/check_encoding_issues.py`
- [ ] 所有关键输出落盘到 `logs/`（详见 AGENTS.md 6.3）

## Test-Refs

- `Game.Core.Tests/Domain/SanguoPlayerTests.cs`
- `Game.Core.Tests/Domain/CityTests.cs`

## References（引用，不复制阈值/策略）

- ADR: ADR-0004、ADR-0005、ADR-0015、ADR-0018、ADR-0019、ADR-0020、ADR-0021、ADR-0024、ADR-0025
- CH: CH01、CH04、CH05、CH06、CH07、CH09、CH10
