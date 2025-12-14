# Phase-23: sanguo 模板说明与差异备忘

> 目的：在不改变既有 Phase 1-22 迁移体系的前提下，用一页文档讲清楚 `sanguo` 与上游模板（godotgame/newguild）的关系，以及当前已经对齐的 CI/workflow/脚本与未来需要按“三国玩法”定制的部分。

---

## 1. 背景与定位

- 上游通用模板：`godotgame` —— 从 vitegame 迁移而来的 Windows-only Godot 4.5 + C# 模板，沉淀了完整的 ADR 体系、迁移 Phase 文档、CI/质量门禁与脚本工具链。  
- 兄弟模板：`skyoxu/newguild` —— 在 godotgame 基础上增加“公会管理”玩法的示例与文档，对 CI/workflows 进行了首次完整跑通与验证。  
- 本仓库：`skyoxu/sanguo` —— 在 `C:\buildgame\godotgame` 基础上复制并派生，用于承载“三国”题材的策略/经营类玩法；技术栈、质量门禁与迁移 Phase 结构保持与 godotgame/newguild 一致，只在领域模型、场景结构与测试用例上逐步三国化。  
- 谱系口径：vitegame → godotgame（通用 Godot 模板）→ newguild / sanguo（兄弟模板），具体命名与职责界定见 `docs/adr/ADR-0024-sanguo-template-lineage.md`。

---

## 2. 已对齐 newguild 的 CI / Workflow / 脚本

本节仅列出与 day‑to‑day 开发最相关的部分，其它工具与 newguild 一致时不再重复。

- GitHub Actions 工作流（仓库名已从 newguild 改为 `skyoxu/sanguo`，步骤逻辑与 newguild 等价）：  
  - `.github/workflows/ci-windows.yml` —— 汇总 Windows 下的类型检查、单测与基础质量门禁。  
  - `.github/workflows/windows-quality-gate.yml` —— 调用 `scripts/python/quality_gates.py` 与相关 PowerShell 脚本，执行 dotnet 单测、GdUnit4 场景测试、安全与性能烟测等。  
  - `.github/workflows/windows-export-slim.yml` —— 使用 `scripts/ci/export_windows.ps1` 导出精简版 Windows 可执行文件，并通过 `smoke_exe.ps1` 做最小运行验证。  
  - `.github/workflows/windows-release.yml` / `windows-release-tag.yml` —— 复用 newguild 的发布流水线，只是仓库名与产物命名调整为 sanguo。  
  - `.github/workflows/windows-smoke-dry-run.yml` —— 作为本地开发/调试时的“干跑”入口，对脚本可用性做快速验证。  

- Python 脚本（路径与职责与 newguild 对齐）：  
  - `scripts/python/ci_pipeline.py` —— 将 dotnet 测试、GdUnit4、编码检查等步骤串成统一 CI 管道。  
  - `scripts/python/quality_gates.py` —— 根据 ADR-0005/ADR-0015 的质量门禁口径，组合执行类型检查、单测、场景测试、安全与性能烟测。  
  - `scripts/python/run_dotnet.py` —— 封装 `dotnet test` 与 coverlet 覆盖率采集逻辑。  
  - `scripts/python/run_gdunit.py` —— 封装 GdUnit4 运行方式与日志落盘规则。  
  - `scripts/python/smoke_headless.py` —— 使用 Godot headless 运行主场景，完成最小启动与退出验证（已在本地环境验证通过，日志见 `logs/ci/<日期>/smoke/`）。  

- PowerShell / 其他脚本（保持 newguild 结构）：  
  - `scripts/ci/run_dotnet_tests.ps1` / `run_dotnet_coverage.ps1` —— Windows 下 dotnet 单测与覆盖率脚本。  
  - `scripts/ci/run_gdunit_tests.ps1` —— Headless 场景测试执行入口。  
  - `scripts/ci/smoke_headless.ps1` / `smoke_exe.ps1` —— Godot headless 冒烟与导出后 EXE 冒烟。  
  - `scripts/ci/quality_gate.ps1` —— 将上述脚本组合为一键质量门禁入口，供本地与 CI 复用。  
  - `scripts/windows/run_dotnet.ps1` / `run_godot_selfcheck.ps1` —— Windows 开发机上的快捷入口，与 newguild 版本在逻辑上等价。  

整体原则：在没有特殊三国玩法需求前，sanguo 完整复用 newguild 的 CI/脚本设计，只调整仓库名、路径与少量文本描述；任何脚本行为差异必须在本 Phase 文档中注明。

---

## 3. 未来需要按“三国玩法”定制的部分（规划向）

以下内容为规划向差异说明，落地时应同步新增或更新对应 ADR/Phase 文档，并在 PR 描述中引用本 Phase。

- 领域模型与 Contracts：  
  - 现状：仓库中已存在 `Game.Core/Contracts/Guild/GuildMemberJoined.cs` 等示例契约，更多是 newguild 玩法示例遗留。  
  - 规划：为“三国”玩法引入新的领域契约命名空间（如 `Game.Core.Contracts.Battle`、`Game.Core.Contracts.Officer`、`Game.Core.Contracts.Faction` 等），并按 AGENTS.md 中的 Contracts 规范（域事件命名、XML 注释、xUnit 测试）补齐对应的测试与文档映射。  
  - 要求：每次新增玩法相关 Contracts 时，应引用 ADR-0018（技术栈）、ADR-0004（事件总线与契约）以及本 ADR-0024（模板谱系），确保不会与 newguild 的公会玩法契约混淆。  

- 场景结构与 GdUnit4 测试：  
  - 现状：Phase-11/Phase-12 文档与示例重点围绕通用模板/公会玩法构建；sanguo 仍在沿用这些场景与测试结构。  
  - 规划：  
    - 为“三国战役/城市/势力管理”等核心场景设计专用 `.tscn` 与 Autoload 结构，并将对应的 GdUnit4 测试纳入 `godot-e2e` / `windows-quality-gate` 检查集合。  
    - 根据战斗规模与 AI 复杂度，视情况扩展 headless 冒烟与性能烟测脚本（例如增加特定战役场景入口参数），但保持脚本接口与 newguild 兼容。  

- 性能与日志口径：  
  - 现状：性能预算与日志收集规则由 ADR-0015 与 Phase-15/16 文档定义，未针对“三国大规模战斗/经济模拟”做专项说明。  
  - 规划：在确认具体玩法与目标设备后，为 sanguo 增补性能预算与日志字段约定（例如兵力规模、回合耗时等），并在 `logs/perf/**` 与 `logs/ci/**` 中增加相应字段；这些改动需要新增或补充相关 ADR，而非在脚本中写死魔法常量。  

- 文档与 Release Notes：  
  - 现状：Phase-22 文档仍以 vitegame → newguild 迁移为主线。  
  - 规划：当 sanguo 达到首个可玩的“三国”垂直切片时，应新增一份专门的 Release Notes 模板（可复制 newguild 的结构），在其中明确 “godotgame → sanguo（三国玩法模板）” 的差异点，并引用本 Phase 与 ADR-0024。  

---

## 4. 使用建议与后续约束

- 当你基于本仓库开发实际的三国游戏项目时：  
  - 若只是“换皮 + 轻玩法修改”，可以直接在 sanguo 上继续迭代，并将新增 ADR/Phase 文档视为 sanguo 模板自身的一部分。  
  - 若需要形成另一个独立模板（例如“科幻版三国”或“完全不同题材”），建议 fork sanguo 并为新仓库新增一条类似 ADR-0024 的谱系说明，以及对应的 `Phase-XX-<NewTemplate>-Notes.md`。  
- 任意对 CI/workflow/脚本行为的修改（特别是质量门禁阈值、安全策略、日志格式）都应：  
  - 先评估与 newguild/godotgame 的差异是否只针对 sanguo；  
  - 如是，则在本 Phase 文档中记录，并视情况新增或 Supersede 相关 ADR；  
  - 确保 `.github/workflows/*` 的注释或 README 中能追溯到对应的 ADR/Phase。

