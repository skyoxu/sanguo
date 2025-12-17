# ADR-0024: sanguo 模板谱系与命名口径说明

- Status: Accepted  
- Context:  
  - 原项目 LegacyProject 采用 LegacyDesktopShell + LegacyUIFramework + Legacy2DEngine + TypeScript 技术栈，之后抽象出通用 Godot 4.5 + C# 模板仓库 godotgame，用于承载 Windows-only Godot + .NET 项目的基础能力。  
  - 本仓库 `skyoxu/sanguo` 是在 `C:\buildgame\godotgame` 模板基础上复制并派生的“三国”主题 Godot 4.5 + C# 游戏模板；代码与文档中仍然保留了部分对 godotgame/newguild 的引用，容易造成“仓库名 / 工程名 / 模板族系”混淆。  
  - 现有 ADR（特别是 ADR-0018-godot-csharp-tech-stack、ADR-0011-windows-only-platform-and-ci、ADR-0006-data-storage）已经确定了 Godot + C# 技术栈与 Windows-only 平台口径，但尚未显式声明 “godotgame → sanguo” 的谱系关系与命名约定。  
  - 为后续在同一台机器（如 `C:\buildgame\*`）并行维护多个 Godot 模板仓库（godotgame/newguild/sanguo…）时避免路径与叫法混乱，需要一条专门 ADR 固化 sanguo 的定位与命名规则。  
- Decision:  
  1. 模板谱系与仓库定位  
     - 上游模板：`godotgame` 代表通用 Godot 4.5 + C# Windows-only 模板仓库，负责沉淀与 LegacyProject 技术栈迁移相关的“无玩法绑定”的基础能力（CI、ADR、Phase 文档、脚本工具等）。  
     - 专用模板：`skyoxu/sanguo` 代表以“三国”玩法为主题的 Godot 4.5 + C# 模板仓库，在技术栈与质量门禁层面复用 godotgame/newguild 的决策与脚本，只在玩法、领域模型与场景结构上进行定制。  
     - 其他派生仓库（如 newguild）视为与 sanguo 同一代的“兄弟模板”，共享一套 ADR/Phase 体系，但面向不同玩法与产品形态。  
  2. 仓库名 / 工程名 / 项目名映射  
     - GitHub 仓库名：`skyoxu/sanguo` —— 所有对外链接、Actions badge、Issue/PR 模板、Release Notes 等，对本仓库一律使用该仓库名，不再使用 godotgame/newguild 作为仓库级别别名。  
     - Godot 主工程名：`GodotGame.sln` / `GodotGame.csproj` —— 在 sanguo 中继续沿用该名称，表示“本仓库内的 Godot .NET 主工程”，不是一个独立仓库。CI 与脚本中出现 `GodotGame` 时，统一理解为 sanguo 内部工程入口。  
     - C# 领域与适配层工程：`Game.Core`、`Game.Godot`、`Game.Core.Tests`、`Game.Godot.Tests` 等命名保持与 godotgame/newguild 相同，表示同一套三层架构与测试金字塔约定在 sanguo 中的复用实现。  
  3. 文档与脚本中的名称口径  
     - 当 docs/adr 与 docs/migration 中出现“本模板”时，在本仓库上下文中统一解释为 `skyoxu/sanguo` 仓库，而不是 godotgame 或 newguild。  
     - 当迁移文档或脚本示例中出现 `C:\buildgame\godotgame` / `C:\buildgame\newguild` 时，在 sanguo 仓库中视为“历史或兄弟模板示例路径”；当前仓库的落地路径以 `C:\buildgame\sanguo` 为准，除非文档明确标注为其他仓库。  
     - 新增文档、示例脚本与 ADR 时，如需引用上游模板，推荐使用“godotgame（上游通用模板）”与“sanguo（三国主题模板）”这样的显式表达，避免只写“GodotGame 项目”导致工程名与仓库名混淆。  
- Consequences:  
  - 对开发者：在同一开发机上同时打开 `godotgame`、`newguild`、`sanguo` 项目时，可以通过仓库名快速区分不同模板，而不必依赖 Godot 工程名或局部路径猜测来源。  
  - 对文档与 ADR：后续涉及 Godot 模板族的架构/流程更新时，可以将 godotgame 视为“通用基底”，sanguo 视为“主题化变体”；本 ADR 为后续新增“三国玩法专属 ADR”（如战斗系统、武将与势力建模）提供命名参照，而不改变现有技术栈与质量门禁口径。  
  - 对 CI/脚本：现有 `.github/workflows/*.yml` 与 `scripts/**` 在逻辑上继续复用 godotgame/newguild 的实现，仅将仓库名与路径替换为 `skyoxu/sanguo` / `C:\buildgame\sanguo`；如需新增“三国玩法专属”脚本，应在命名与文档中明确标注为 sanguo 专用。  
- Supersedes: 无（作为新增 ADR，与既有技术栈 ADR 并行生效）  
- References:  
  - ADR-0018-godot-csharp-tech-stack  
  - ADR-0011-windows-only-platform-and-ci  
  - ADR-0006-data-storage  
  - docs/migration/MIGRATION_INDEX.md  
  - docs/migration/MIGRATION_FEASIBILITY_SUMMARY.md

