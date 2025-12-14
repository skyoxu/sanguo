# CLAUDE.md

> Single source of truth for how AI tools work **together** in this repo. Keep this file short, prescriptive, and executable.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
- **_直言不讳+止损机制_**用中文进行沟通和回答，每次都用审视的目光，仔细看我输入的潜在问题，你要指出我的问题，并给出明显在我思考框架之外的建议。
- **操作系统限定**：默认环境为 **Windows**。所有脚本/命令/依赖安装步骤必须提供 Windows 兼容指引（如py/python 选择等）
- **UTF-8编码写中文**不允许使用其他编码格式处理中文
- **禁止Emoji字符**任何情况下都不允许使用Emoji字符
- 编写md文档时，正文也要用中文，但是**文件名**，**名词解释**可以使用英文，但在**代码和脚本和测试等**工作文件中全部使用**英文**，包括**注释和打印测试**
- **日志与取证**：所有安全/网络/文件/权限审计与测试输出统一写入 logs/（规范见“6.3 日志与工件（SSoT）”），便于排障与归档
- **安全合规**：仅防御安全；拒绝进攻性/潜在滥用代码请求
- **代码与改动**：遵循项目现有约定；先看周边文件/依赖
- **任务管理**：强制频繁使用 TodoWrite 规划/跟踪；逐项标记进行/完成，不要堆到最后

## 设计原则：

- 本项目是 Windows only 的 Godot + C# 游戏项目。
- AI 优先 + arc42/C4 思维：按 不可回退 → 跨切面 → 运行时骨干 → 功能纵切 顺序
- 删除无用代码，修改功能不保留旧的兼容性代码
- **完整实现**，禁止MVP/占位/TODO，必须完整可运行

## 0 Scope & Intent

- **Base 文档**：`docs/architecture/base/**` —— 跨切面与系统骨干（01–07、09、10 章），**无 PRD 痕迹**（以占位 `${DOMAIN_*}` `${PRODUCT_*}` 表达）。
- **ADR**：Architecture Decision Record；**Accepted** 的 ADR 代表当前有效口径。
- **SSoT**：Single Source of Truth；01/02/03 章统一口径（NFR/SLO、安全、可观测性）。
- **Upstream**: BMAD v6 produces PRD + Architecture (arc42 overlays; CH01/CH03 at minimum; ADR-0001…0005 adopted, more as needed).
- **Planning**: Taskmaster converts **PRD → Tasks** with back-links to ADR/CH/Overlay.
- **Implementation & Quality**: Claude Code is primary; **SuperClaude** automates commits/changelogs/reviews; **Serena** handles symbol-level refactors and cross-file test-driven edits.
- **Acceptance**: Official **Subagents** perform checklists/reviews; **Zen MCP** augments analysis with multi‑model reasoning.

## 0.1 New Session Quick Reference

**Starting a fresh session? Read these in order:**

1. **This file** (`CLAUDE.md`) - You're already here ✓
2. **Project indexes** - Context entry points:
   - `architecture_base.index` - Architecture docs (CH01-CH12 + ADRs)
   - `prd_chunks.index` - PRD fragments index
   - `shards/flattened-adr.xml` - All ADRs in single XML
   - `shards/flattened-prd.xml` - All PRD in single XML
3. **Test framework** - `docs/testing-framework.md` (critical for TDD)

**File locations quick reference:**
- PRD input: `.taskmaster/docs/prd.txt` (auto-generated from prd_chunks)
- ADRs: `docs/adr/ADR-*.md` (21 files)
- Architecture: `docs/architecture/base/*.md` (CH01-CH12)
- Tasks: `tasks/tasks.json` (Taskmaster output)
- Logs: `logs/**` (Security/E2E/Unit/Perf audit trails)

**Typical workflow:**
- **Taskmaster**: `npx task-master parse-prd .taskmaster/docs/prd.txt -n 30`
- **Validate**: `py -3 scripts/python/validate_task_links.py`
- **SuperClaude**: `superclaude commit` (after implementation)

---

## Project Background

This is a **production-ready Godot 4.5.1 project template** designed for rapid game development with enterprise-grade tooling. It serves as a reusable, out-of-the-box foundation for Windows desktop games.

### Template Purpose
- **Quick Start**: Clone and start building immediately without setup overhead
- **Best Practices**: Pre-configured tech stack following Godot and C# conventions
- **AI-Friendly**: Optimized for AI-assisted development workflows (BMAD, SuperClaude, Claude Code CLI)
- **Quality Gates**: Built-in static analysis and error tracking infrastructure
- **Scalable Architecture**: Modular scene system supporting complex game logic

### Target Use Cases
- Windows desktop games (simulation, management, strategy genres)
- Single-player experiences with complex game state
- Projects requiring database persistence and heavy computation
- AI-assisted development with automated quality checks

## Getting Started

### Opening the Project
- Run `Godot_v4.5.1-stable_win64.exe` to open the Godot editor
- Run `Godot_v4.5.1-stable_win64_console.exe` for console output/debugging
- The project will automatically load from `project.godot`

### Template Structure
- `project.godot` - Main project configuration (Godot 4.5, Forward Plus renderer)
- `icon.svg` - Default project icon (replace with your game icon)
- `.godot/` - Generated editor files and cache (gitignored)
- `CLAUDE.md` - This guidance file for AI-assisted development
- `docs/testing-framework.md` - 测试框架完整指南（TDD、xUnit、GdUnit4）
- `docs/adr/` - ADR文件目录
- `docs/architecture/base/` - 综合技术文档清洁版本
- `docs/architecture/overlays/<PRD-ID>/` - 综合技术文档对应<PRD-ID>版本
- `docs/prd/prd_chunks/ + prd_chunks.index`- prd分片及索引
- `architecture_base.index` - 综合技术文档清洁版本的索引

### Base / Overlay 目录约定

```
docs/
  architecture/
    base/                 # SSoT：跨切面与系统骨干（01–07、09、10）
      01-introduction-and-goals-v2.md
      02-security-baseline-electron-v2.md
      03-observability-sentry-logging-v2.md
      04-system-context-c4-event-flows-v2.md
      05-data-models-and-storage-ports-v2.md
      06-runtime-view-loops-state-machines-error-paths-v2.md
      07-dev-build-and-gates-v2.md
      08-crosscutting-and-feature-slices.base.md            # 仅模板/约束/占位示例
      09-performance-and-capacity-v2.md
      10-i18n-ops-release-v2.md
      11-risks-and-technical-debt-v2.md
      12-glossary-v2.md
    overlays/
      PRD-<PRODUCT>/
        08/
          08-功能纵切-<模块A>.md
          08-功能纵切-<模块B>.md
          _index.md
```

### 默认 ADR 映射（可扩展）

- **ADR-0001-tech-stack**：技术栈选型
- **ADR-0002-electron-security**：安全基线
- **ADR-0003-observability-release-health**：可观测性和发布健康 (Sentry, 崩溃率阈值, 结构化日志)
- **ADR-0004-event-bus-and-contracts**：事件总线和契约 (CloudEvents, 类型定义, 端口适配)
- **ADR-0005-quality-gates**：质量门禁 (覆盖率, ESLint, 性能阈值, Bundle大小)
- **ADR-0006-data-storage**：数据存储 (SQLite, 数据模型, 备份策略)
- **ADR-0007-ports-adapters**：端口适配器 (架构模式, 依赖注入, 接口设计)
- **ADR-0008-deployment-release**：部署发布 (CI/CD, 分阶段发布, 回滚策略)
- **ADR-0009-cross-platform**：跨平台 (Windows/macOS/Linux 支持, 原生集成)
- **ADR-0010-internationalization**：国际化 (多语言支持, 本地化流程, 文本资源管理)
- **ADR-0011-windows-only-platform-and-ci**：确立Windows-only平台策略
- **ADR-0015-performance-budgets-and-gates**：定义性能预算与门禁统一标准，包括P95阈值、Bundle大小限制和首屏优化策略

> 任何章节/Story 若改变上述口径，**必须**新增或 Supersede 对应 ADR。

---

### Claude 写作前自检（内置检查清单）

- 目标文件属于 **base** 还是 **overlay**？（base 禁 PRD-ID，overlay 必带 PRD-ID 与 ADRs）
- 是否涉及 **安全、事件契约、质量门禁、Release Health**？若是，请**引用** ADR‑0002/0004/0005/0003。
- 08 章是否只**引用** 01/02/03 的口径（不复制阈值）？
- 是否附带 **契约片段** 与 **就地验收**？
- PRD Front‑Matter 的 `Test-Refs` 是否已更新到新用例或占位用例？

---

### PR 模板要求（最少需要在 `.github/PULL_REQUEST_TEMPLATE.md` 勾选）

- [ ] 更新/新增 `src/shared/contracts/**` 的接口/类型/事件
- [ ] 更新/新增 `tests/unit/**`与 `tests/e2e/**`
- [ ] 涉及 PRD：Front‑Matter 的 `Test-Refs` 指向相应用例。
- [ ] 变更口径/阈值/契约：已新增或 _Supersede_ 对应 ADR 并在 PR 描述中引用。
- [ ] 附上 **E2E 可玩度冒烟** 的运行链接/截图
- [ ] 附上 **Sonar Quality Gate** 结果链接（新代码绿灯）
- [ ] 附上 **Sentry Release** 链接（用于回溯本次崩溃/错误）

---

### 违例处理

- 缺失 `ADRs`、复制阈值进 08 章、Base 出现 PRD-ID、遗漏 `Test-Refs` 等：Claude/BMAD 应**拒绝写入**并返回“拒绝原因 + 自动修复建议 + 需要引用/新增的 ADR 清单”。
- 需要新增 ADR 时，自动生成 `docs/adr/ADR-xxxx-<slug>.md` 的 _Proposed_ 草案并提示审阅。

> **备注**：本 Rulebook 与项目中的脚本/模板、Base/Overlay 结构**强关联**。请保持这些文件存在且更新：  
> `scripts/scan_electron_safety.mjs` · `scripts/quality_gates.mjs` · `scripts/verify_base_clean.mjs` · `.github/PULL_REQUEST_TEMPLATE.md` · `docs/architecture/base/08-功能纵切-template.md`。

---

### 附录：最小 ADR 模板（Accepted）

```md
# ADR-000X: <title>

- Status: Accepted
- Context: <背景与动机；关联的 PRD-ID/章/Issue>
- Decision: <你做了什么决定；口径与阈值；适用范围>
- Consequences: <权衡与影响；与既有口径的关系；迁移注意>
- Supersedes: <可选：被替代的 ADR 列表>
- References: <链接/规范/实验数据>
```

### Development Workflow
- Create new scenes as `.tscn` files for modular components
- Write game logic in C# (`.cs` files) as primary language
- Use GDScript (`.gd` files) for rapid prototyping when needed
- Attach scripts to scene nodes via the Godot editor
- Press F5 to run the project, F6 to run current scene
- Use the Godot debugger and output console for troubleshooting

## Technology Stack

This template comes pre-configured with the following technology stack:

| Layer | Technology | Purpose |
| --- | --- | --- |
| Game Engine | **Godot 4.5** | Scene tree, node system, 2D/3D rendering, physics |
| UI System | **Godot Control** | HUD, menus, dialogs, in-game interfaces |
| Styling | **Godot Theme/Skin** | Unified UI visual appearance |
| Primary Language | **C#** | Main game logic with strong typing for AI generation and static analysis |
| Unit Testing | **xUnit + FluentAssertions + NSubstitute** | Fast TDD red-green-refactor cycles for core logic |
| Scene Testing | **GdUnit4** | Godot integration tests with headless support |
| Coverage | **coverlet** | Code coverage collection（coverage gate，口径见 6.2） |
| Database | **godot-sqlite** | Local SQLite database for game data and save files |
| Configuration | **ConfigFile / user://** | Player settings and progress persistence |
| Communication | **Signals + Autoload** | Event system and global state management |
| Multithreading | **WorkerThreadPool / Thread** | Background tasks for AI computation and simulation |
| Build & Export | **Godot Export Templates** | Windows executable packaging |
| Static Analysis | **SonarQube** | C# code quality gates |
| Error Tracking | **Sentry (Godot SDK)** | Crash monitoring and runtime error collection |

### Stack Rationale
- **C# over GDScript**: Strong typing enables better AI code generation and static analysis
- **xUnit for TDD**: Fast red-green-refactor cycles with pure C# logic, no Godot engine startup required
- **GdUnit4 for integration**: Headless-compatible scene testing for CI/CD pipelines
- **godot-sqlite**: Native database support for complex game state without external dependencies
- **SonarQube + Sentry**: Enterprise-grade quality gates and observability from day one
- **WorkerThreadPool**: Built-in support for performance-critical background computation
**除非计划中特别指明，否则不要引入其他库**

## 核心行为规则

1. 你会在对话输出完毕后选择适当的时机向用户提出询问，例如是否需要添加后端能力，是否打开预览，是否需要部署等
2. 交互式反馈规则：在需求不明确时主动与用户对话澄清，优先使用自动化工具 interactiveDialog 完成配置。执行高风险操作前必须使用 interactiveDialog 获得用户确认。保持消息简洁并用ASCII标记状态。
3. **Test-driven development must** - Never disable tests, fix them

## 1 Context Discipline (RAG Rules)

1. **凡会落地为代码/测试的改动，必须引用 ≥ 1 条 _Accepted_ ADR。**  
   若改动改变阈值/契约/安全口径：**新增 ADR** 或 **以 `Superseded(ADR-xxxx)` 替代旧 ADR**。

- Local sessions: prefer `claude --add-dir shards` to reference `@shards/*` paths directly.

2. **08 章（功能纵切）只放在 overlays**：
   - base 仅保留 `08-功能纵切-template.md` 模板与写作约束；**禁止**在 base 写任何具体模块内容。
   - 08 章**引用** 01/02/03 的口径，**禁止复制阈值/策略**到 08 章正文。事件命名规则：
     `\${DOMAIN_PREFIX}.<entity>.<action>`；接口/DTO 统一落盘到 `src/shared/contracts/**`。
3. Use **only**: `@architecture_base.index`, `@prd_chunks.index`, `@shards/flattened-prd.xml`, `@shards/flattened-adr.xml` for overlay‑related work. Do **not** rescan `docs/` or rebuild flattened XML.
4. Overlays: write to `docs/architecture/overlays/<PRD-ID>/08/`. 08章只写**功能纵切**（实体/事件/SLI/门禁/验收/测试占位）；跨切面规则仍在 Base/ADR。

---

## 2 Tool Roles & Allowed Usage

### 2.1 Claude Code (primary)

- Use project **slash commands** in `.claude/commands/**` when available (`/architect`, `/taskmaster`, etc.).
- Keep edits minimal, test-driven, and tied to ADR/CH.
- Never broad‑read entire repo; always cite exact files with `@path`.

### 2.2 Taskmaster — PRD → Tasks

- Input: single‑file PRD at `.taskmaster/docs/prd.txt` (merged from `docs/prd_chunks/*`, FM removed).
- Generate initial tasks: `npx task-master parse-prd .taskmaster/docs/prd.txt -n 30` (tune `-n`).
- Persist to `tasks/tasks.json` with required fields:
  - `adrRefs: ["ADR-0002", …]` (≥1), `archRefs: ["CH01","CH03", …]` (≥1), optional `overlay: "docs/architecture/overlays/<PRD-ID>/08/..."`.
- Run Python task/ADR links validator（e.g. `py -3 scripts/python/validate_task_links.py`）to enforce ADR/CH back‑links & file existence（工具：Python JSONSchema）。Failing PRs cannot merge.

### 2.3 SuperClaude — Git automation

- Use for: **commit messages**, **changelogs**, **automated code reviews**.
- Commands (examples; adapt to local scripts):
  - `superclaude commit` → generate conventional commit w/ ADR/CH refs.
  - `superclaude changelog` → update `CHANGELOG.md` from history.
  - `superclaude review --staged` → summarize diffs + risks; produce review notes.
- Guardrails: never auto‑commit failing builds; never bypass hooks (`--no-verify` forbidden).

### 2.4 Serena — symbol‑level refactors & TDD edits

- Use when you need **semantic (LSP‑aware)** changes: cross‑file rename, API migration, test‑driven fixes in large repos.
- Typical prompts:
  - “Rename `GuildService` → `GuildManagerService` across repo, update imports/usages/tests; keep changes atomic.”
  - “Change interface contract `GuildId` → `GuildUID` and update affected DTOs + TS types; regenerate failing tests.”
- Guardrails: propose a diff; run unit/E2E locally; large refactors go through PR with full review & CI.

### 2.5 Official Subagents — acceptance & audits

- Use to run **acceptance checklists** and doc‑out final overlays:  
  _“Use the acceptance subagent to verify Overlay CH01/CH03/SLOs, security baseline, and CloudEvents builder; report failures with file+line links.”_
- Subagents run with a **separate context**; keep them **read‑mostly** unless an edit is explicitly approved.

### 2.6 Zen MCP — multi‑model validation

- Use for: cross‑model code analysis, property‑based test suggestions, tricky bug triage, standards checks.
- Keep it **stateless** for safety; paste back results as comments or PR reviews. Do not grant destructive tools by default.

---

## 3 Engineering Workstyle

- Small, green steps; learn from existing code; pragmatic choices; clarity over cleverness.
- TDD‑leaning flow: Understand → Test (red) → Implement (green) → Refactor → Commit (explain **why**, link ADR/CH/Issue/Task).
- When stuck (max 3 attempts): log failures; list 2–3 alternatives; question abstraction/scope; try the simpler path.
- 单个脚本文件不得超过400行，如果实在无法进行功能切割，需要说明理由并征得同意后，再继续创建脚本

---

## 4 Technical Standards

### Architecture

- Composition over inheritance (DI), interfaces over singletons, explicit over implicit.

### Code Quality

- Every commit compiles, passes tests, and follows format/lint; new code adds tests; no `--no-verify`.

### Error Handling

- Fail fast with context; handle at the right layer; no silent catches.

---

## 5 Security & Privacy Baseline (Godot 4.5 + C#)
- 资源与文件系统
    - 只允许 res://（只读）与 user://（读写）；拒绝绝对路径与越权访问（路径规范化 + 扩展名/大小白名单）；失败统一审计（路径规范见 6.3 日志与工件）。
    - 外链与网络
        - 仅 HTTPS；主机白名单 ALLOWED_EXTERNAL_HOSTS；GD_OFFLINE_MODE=1 时拒绝所有出网并审计。
        - 若使用 WebView（可选插件），限制 scheme=HTTPS、禁用 JS 桥/任意文件加载，不得引用 file:///data:/javascript:。
    - 代码与插件
        - 禁止运行期动态加载外部程序集/脚本；插件白名单（导出/发布剔除 dev-only 插件）；禁用远程调试与编辑器残留。
    - OS.execute 与权限
        - 默认禁用 OS.execute（或仅开发态开启并严审计）；CI/headless 下摄像头/麦克风/文件选择默认拒绝。
    - 遥测与隐私
        - 在最早 Autoload 初始化 Sentry Godot SDK；开启 Releases + Sessions 统计 Crash‑Free；敏感字段 SDK 端脱敏；结构化日志采样。
    - 配置开关
        - GD_SECURE_MODE=1、ALLOWED_EXTERNAL_HOSTS=<csv>、GD_OFFLINE_MODE=0/1、SECURITY_TEST_MODE=1。
    - 安全烟测（CI 最小集）
        - 外链 allow/deny/invalid 三态 + 审计文件存在；网络白名单验证；user:// 写入成功、绝对/越权写入拒绝；权限在 headless 下默认拒绝。

### 发布健康门禁（Crash‑Free SSoT）
- 启用 Sentry Releases + Sessions 以计算 Crash‑Free Sessions/Users。
- 门禁阈值（默认）：24h Crash‑Free Sessions ≥ 99.5% 方可扩大/发布（可用环境变量覆盖，如 `RELEASE_CRASHFREE_THRESHOLD=99.5`）。
- 校验位置：CI 作业“release-health”（读取 Sentry 历史窗口，比较阈值）。
- 产出：见 6.3 日志与工件（release-health.json）。

---

## 6 输出格式与附带物（让规范可执行）
- 任何"可执行规范"（章节/Story/task）必须附带以下产物（Godot 4.5 + C# 口径）：
  1. 接口/类型/事件的 C# 片段（Contracts）
     - 放置：**Game.Core/Contracts/**（仅此处为 SSoT，其他文档/代码引用不复制）
     - 要求：强类型、XML 注释（summary/param/returns），公共事件命名遵循 ${DOMAIN_PREFIX}.<entity>.<action>
  2. 就地验收测试
     - 领域层（不依赖引擎）：xUnit 单测（覆盖核心算法/状态机/DTO 映射）
     - 场景/节点（依赖引擎）：GdUnit4 或自建 TestRunner（headless），覆盖 Signals 连通、关键节点可见性与资源路径
     - 如涉及外链/网络/文件/权限，必须包含安全烟测（allow/deny/invalid+审计校验）
- 08 章文档产出必须同步/创建 Test-Refs（指向新增/更新的 xUnit/GdUnit4 测试文件；初期可放占位并标注 TODO）
- 契约统一：事件/端口/DTO 仅落盘 **Game.Core/Contracts/**，各章节/用例引用路径，不得复制粘贴以免口径漂移
- 技术债占位规范：如必须引入动态执行/非白名单 DllImport/临时放宽安全策略，需同步添加 TODO（owner | due | Issue 链接 | 回迁计划），并在 PR 中说明

### 6.0 目录与命名（SSoT）
- Contracts：**Game.Core/Contracts/**（领域 SSoT，纯 .NET 项目，不依赖 Godot）
- 领域实现：**Game.Core/**（仅 .NET 标准库依赖）
- 端口定义：**Game.Core/Ports/**（接口层，隔离 Core 与 Adapters）
- 适配层：**Game.Godot/Adapters/**（封装 Godot API，通过接口注入至 Core）
- 场景与资源：Scenes/**、Assets/**
- 审计与日志：见 6.3 日志与工件（SSoT）

### 6.1 契约模板（Contracts Template，C#）
- 放置：**Game.Core/Contracts/<Module>/**
- 要求：不可引用 Godot API（保持可单测）、命名清晰、不可暴露实现细节
  示例（C#）

  namespace Game.Core.Contracts.Guild;

  /// <summary>
  /// Domain event: ${DOMAIN_PREFIX}.guild.member.joined
  /// 说明：用户加入公会
  /// </summary>
  public sealed record GuildMemberJoined(
      string UserId,
      string GuildId,
      DateTimeOffset JoinedAt,
      string Role // member | admin
  )
  {
      public const string EventType = "core.guild.member.joined";
  }

### 6.2 测试与验收（xUnit + GdUnit4）
- 领域层（xUnit，必需）
  - 覆盖率门禁：lines ≥90%，branches ≥85%（coverlet 出报告）
  - 断言建议：FluentAssertions；Mock：NSubstitute
- 场景/节点（GdUnit4/Runner，按需）
  - 覆盖关键节点可见性、Signals 连通、资源路径正确性
  - headless 运行，产出 JUnit/XML 与 JSON 摘要（路径规范见 6.3 日志与工件）
- 安全烟测（如涉及）
  - 外链：Security.OpenExternalUrl(url) 仅 https + 白名单；验证 allow/deny/invalid 并检查审计文件
  - 网络：NetworkClient 仅对白名单主机放行；GD_OFFLINE_MODE=1 下拒绝所有出网
  - 文件：仅 user:// 写；拒绝绝对/越权路径
  - 权限：CI/headless 默认拒绝摄像头/麦克风/文件选择
  示例（xUnit）

  using FluentAssertions;
  using Game.Core.Contracts.Guild;
  using Xunit;

  public class GuildContractsTests
  {
      [Fact]
      public void Joined_event_has_expected_defaults()
      {
          var evt = new GuildMemberJoined("u1","g1",DateTimeOffset.UtcNow,"member");
          GuildMemberJoined.EventType.Should().Be("core.guild.member.joined");
          evt.Role.Should().Be("member");
      }
  }

  示例（GdUnit4，片段）

  # Tests/Scenes/test_guild_hud.gd
  extends "res://addons/gdUnit4/src/core/GdUnitTestSuite.gd"

  func test_hud_visible_and_signal_emitted() -> void:
      var scene = preload("res://Scenes/Guild/GuildHud.tscn").instantiate()
      add_child_autofree(scene)
      assert_bool(scene.visible).is_true()
      # 断言信号发布
      var emitted := false
      scene.member_joined.connect(func(_u, _g): emitted = true)
      scene.simulate_join("u1", "g1") # 你的模拟方法
      assert_bool(emitted).is_true()

### 6.3 日志与工件（SSoT）

- 目录结构（按日期/模块分子目录）：
  - 单元测试：`logs/unit/<YYYY-MM-DD>/`（xUnit 报告、coverage.json、JUnit/XML 摘要）
  - 引擎冒烟：`logs/e2e/<YYYY-MM-DD>/`（GdUnit4/JUnit/XML；截图或额外 JSON 摘要）
  - 性能烟测：`logs/perf/<YYYY-MM-DD>/`（P95/均值/样本数 summary.json 与截图/trace 可选）
  - CI 工件：`logs/ci/<YYYY-MM-DD>/`（typecheck.log、lint.log、security-audit.jsonl、task-links.json、release-health.json、export.log 等）

- 命名规范（建议）：
  - 用例派生名：`<project>--<suite>--<case>.{png,json}`
  - 审计日志：`security-audit.jsonl`（逐行 JSON；字段至少含 {ts, action, reason, target, caller}）
  - 性能摘要：`summary.json`（{p95, p50, samples, scene, gate: soft|hard}）

- 收敛规则：
  - 文档/示例中涉及 logs 路径，统一引用本节，不再在其他章节重复枚举目录与文件名。

### 6.4 质量门禁绑定（与产出强关联）
- 每个规范/Story 的 PR，需满足：
  - 附带 C# Contracts 与相应 xUnit 测试用例；如涉及场景/Signals，附 GdUnit4/Runner 用例
  - 覆盖率阈值通过（见 6.2 覆盖率门禁口径）；重复度 ≤ 2–3%
  - 安全相关改动附安全烟测与审计条目（路径规范见 6.3）
  - 日志与工件产出遵循 6.3（测试报告、审计与性能报告）

### 6.5 Test-Refs（文档-测试对齐）
- 08 章文档页脚维护 Test-Refs 清单（相对路径）：
  - Core 测试：Tests/Core/<Module>/<Name>Tests.cs
  - 场景测试：Tests/Scenes/<Module>/<Name>.gd（或 Runner 输出）
  - 安全/性能：见 6.3 日志与工件（SSoT）

### 6.6 运行与命令（Windows + Python）
- 单元测试：dotnet test --collect:"XPlat Code Coverage"
- 场景/冒烟（headless）：py -3 scripts/python/godot_tests.py --headless --suite smoke
- 安全专用：py -3 scripts/python/godot_tests.py --headless --suite security
- 一键门禁：py -3 scripts/python/quality_gates.py --typecheck --lint --unit --dup --scene --security --perf

### 6.7 注意事项
- Contracts 不得依赖 Godot 类型；与引擎交互只出现在 Adapters/Scenes
- 事件命名维持 ${DOMAIN_PREFIX}.<entity>.<action>；禁用魔法字符串，统一常量化
- 任何“临时放行/动态执行/DllImport”需附 TODO（owner|due|Issue 链接|回迁计划）并在 PR 中说明

---

## 7 Quality Gates (CI/CD)
> 最小门禁以脚本方式固化，均可在本地与 CI 运行；阈值可通过环境变量覆盖。
- **脚本**（建议存在）：
  - `scripts/python/scan_godot_security.py` —— 扫描不安全 API、路径越界、HTTP（非 HTTPS）用法，输出 logs/ci/security-*.jsonl
  - `scripts/python/run_dotnet.py` ——  dotnet test + coverlet 覆盖率汇总到 logs/unit
  - `scripts/python/run_gut.py` ——  Godot Headless + GUT 集成冒烟到 logs/e2e
  - `scripts/python/perf_smoke.py` —— 轻量 P95 采样（软门）到 logs/perf
- **统一入口**（CI 可调用 Python 脚本）
  - 单元测试（.NET）：py -3 scripts/python/run_dotnet.py --project tests/dotnet --coverage（产出见 6.3）
  - 引擎冒烟（GUT）：py -3 scripts/python/run_gut.py --godot "%GODOT_BIN%" --project "%GODOT_PROJECT%" --tests tests/gut（产出见 6.3）
  - 性能烟测：py -3 scripts/python/perf_smoke.py --scene res://scenes/Main.tscn --samples 30 --threshold 200（产出见 6.3）
- **质量阈值与门禁**
  - 复杂度：roslyn analyzers + dotnet-format（圈复杂度平均 ≤ 5，单文件 ≤ 10）
  - 依赖守卫：循环依赖脚本化扫描（可选 NDepend 报告；CI 只做 fail/ok 判定）
- **运行环境（Windows）**
    - 要求 .NET 8 SDK、Godot 4.x（建议 .NET 版本），Python（py -3）
    - 环境变量：GODOT_BIN、GODOT_PROJECT、PERF_GATE_MODE、PERF_P95_THRESHOLD_MS、CI
- Required checks（分支保护）
  - godot-e2e（Smoke/Security/Perf，headless）
  - dotnet-unit（Core contracts & units with coverage gate）
- task-links-validate（ADR/CH/Overlay 回链校验，Python JSONSchema）
  - release-health（Sentry Crash‑Free 门禁）
  -（可选）superclaude-review（AI review notes 存在）
- Pipeline（顺序）
  - typecheck → lint → unit → e2e → task link validation → release‑health → package
- 合并准则
  - 仅当以上 Required checks 全绿方可合并
  - 受保护分支需启用 “Require status checks”

**作业分解（Jobs）**
- dotnet-typecheck-lint（Windows）
  - 恢复依赖与分析器：dotnet restore
  - 类型检查/编译门禁：dotnet build -warnaserror
    -（可选）格式与分析器：dotnet format analyzers --verify-no-changes
  - 产出：见 6.3 日志与工件（typecheck.log、lint.log）
- dotnet-unit（Windows）
  - 覆盖率门禁：dotnet test --collect:"XPlat Code Coverage"（阈值口径见 6.2）
  - 产出：见 6.3（unit/**、junit/xml、coverage.json）
- godot-e2e（Windows，headless）
  - 环境：GD_SECURE_MODE=1、SECURITY_TEST_MODE=1、ALLOWED_EXTERNAL_HOSTS=<csv>
  - 冒烟/安全/性能（软门）：py -3 scripts/python/godot_tests.py --headless --suite smoke,security,perf
  - 产出：见 6.3（e2e/**、security-audit.jsonl、JUnit/XML）
  - 通过标准：
    - Smoke：启动→主场景可见→关键 Signals→退出
    - Security：外链/网络/文件/权限 allow/deny/invalid 与审计一致
    - Perf：启动 ≤3s、P95 逻辑帧耗时 ≤16.6ms（软门，可在性能分支设硬门）
- task-links-validate（Windows，Python JSONSchema）
  - 校验 ADR/CH/Overlay 回链与 Front‑Matter：py -3 scripts/python/task_links_validate.py
  - 产出：见 6.3（task-links.json）
- release-health（Windows）
  - 读取 Sentry Releases + Sessions（门禁阈值与判定口径见“5 发布健康门禁”）
  - 命令：py -3 scripts/python/release_health_gate.py --project <sentry_project> --env <env>
  - 需要机密：SENTRY_AUTH_TOKEN、SENTRY_ORG、SENTRY_PROJECT
  - 产出：见 6.3（release-health.json）
- package（Windows 导出）
  - 准备 export templates 缓存（Godot 4.5）
  - 导出发布：godot.exe --headless --export-release "Windows Desktop" build/Game.exe
  - 产出：build/Game.exe、build/Game.pck；导出日志见 6.3（export.log）
  - 仅在前置门禁全绿时运行
- dotnet：actions/setup-dotnet（.NET 8）
- 缓存建议：
  - NuGet：~\.nuget\packages
  - Godot export templates：~\AppData\Roaming\Godot\export_templates\4.5.*

**命令清单（Windows 友好，Python 驱动）**
- 单元：dotnet test --collect:"XPlat Code Coverage"
- E2E（headless）：py -3 scripts/python/godot_tests.py --headless --suite smoke,security,perf
- 任务/回链：py -3 scripts/python/task_links_validate.py
- 发布健康：py -3 scripts/python/release_health_gate.py --project <sentry_project> --env <env>
- 导出：godot.exe --headless --export-release "Windows Desktop" build/Game.exe

**分支保护与开关**
- 受保护分支启用 Required checks：godot-e2e、dotnet-unit、task-links-validate、release-health（可加 superclaude-review）
- 可配置开关：
  - GD_SECURE_MODE=1、ALLOWED_EXTERNAL_HOSTS=<csv>、GD_OFFLINE_MODE=0/1
  - GD_ENABLE_PLAYABLE=0/1（竖切 E2E）、SECURITY_TEST_MODE=1
  - Sentry：SENTRY_AUTH_TOKEN、SENTRY_ORG、SENTRY_PROJECT、SENTRY_ENV

---

## 8 Definition of Done (DoD)

- [ ] Unit/E2E tests written and passing
- [ ] Code follows conventions; no lint/format warnings
- [ ] Commit messages clear; link ADR/CH/Issue/Task
- [ ] Matches Overlay acceptance checklist
- [ ] No stray TODOs (or reference issues)



## Architecture Guidelines

These guidelines define the recommended patterns for projects built from this template.

### Testable Architecture (Critical)

**Three-Layer Separation for TDD**

```
┌─────────────────────────────────────┐
│  Scenes/ (Godot .tscn)              │  ← Minimal logic: assembly, signal routing, UI glue
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  Adapters/ (C# + Godot API)         │  ← Only layer touching Godot APIs
│  - ITime, IInput, IResourceLoader   │  ← Interface-based isolation
│  - Contract tests (xUnit + Mock)    │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  Game.Core/ (Pure C#)               │  ← 80% of core game logic
│  - Zero Godot dependencies          │  ← Fast TDD red-green-refactor
│  - xUnit tests with coverage gate（see 6.2） │
└─────────────────────────────────────┘
```

**Why This Matters:**
- Pure C# logic tests run in milliseconds without starting Godot engine
- Interface injection enables deterministic testing (mock time, input, randomness)
- AI-generated code can be validated rapidly through automated tests
- Godot scene changes don't break core business logic tests

### Scene Organization
- Structure features as modular scenes (`.tscn`) - one scene per component or feature
- Nest and instance scenes for code reuse and composition
- Design scenes to map cleanly to development tasks for AI-assisted workflows

### Scripting Conventions
- **C# for Core Logic**: Use C# for main game systems to leverage strong typing, static analysis, and SonarQube integration
- **GDScript for Prototyping**: Use GDScript for quick iterations and simple UI behaviors
- Follow object-oriented design with nodes as fundamental building blocks
- Use signals for decoupled event-driven communication between nodes

### State Management
- Configure Autoload singletons in `project.godot` for global game state
- Use signals for publish-subscribe patterns in local state changes
- Store persistent player settings via ConfigFile API in the `user://` directory

### Data Persistence
- Use godot-sqlite GDExtension for structured game data (save files, game state)
- Use ConfigFile for lightweight player preferences and progress tracking
- Use Godot Resources (`.tres`/`.res`) for asset configurations and static data

### Performance Optimization
- Offload heavy computations (AI, economic simulation) to WorkerThreadPool
- Keep performance-critical logic off the main thread to maintain frame rate
- Leverage Godot's scene instancing system for efficient memory management

## Customizing This Template

### First Steps After Cloning
1. Update `project.godot` - change project name and configuration
2. Replace `icon.svg` with your game's icon
3. Initialize C# test projects:
   ```bash
   dotnet new sln -n YourGame
   dotnet new classlib -n Game.Core
   dotnet new xunit -n Game.Core.Tests
   dotnet sln add Game.Core Game.Core.Tests
   dotnet add Game.Core.Tests reference Game.Core
   dotnet add Game.Core.Tests package FluentAssertions
   dotnet add Game.Core.Tests package NSubstitute
   dotnet add Game.Core.Tests package coverlet.collector
   ```
4. Install GdUnit4 via Godot AssetLib
5. Set up godot-sqlite GDExtension
6. Configure SonarQube and Sentry credentials for your project

### Directory Structure Recommendations
```
project_root/
├── Game.Core/              # Pure C# class library (zero Godot dependencies)
│   ├── Domain/             # Game entities and business rules
│   ├── Services/           # Business logic and state machines
│   └── Interfaces/         # Contracts for Godot adapters
├── Game.Core.Tests/        # xUnit unit tests (coverage gate, see 6.2)
├── Adapters/               # Godot API integration layer
│   ├── TimeAdapter.cs      # ITime → Godot Time API
│   ├── InputAdapter.cs     # IInput → Godot Input API
│   └── ResourceAdapter.cs  # IResourceLoader → Godot ResourceLoader
├── scenes/                 # Game scenes organized by feature
├── scripts/                # Godot-attached scripts (minimal logic)
├── assets/                 # Art, audio, fonts
├── resources/              # .tres/.res configuration files
├── addons/                 # Third-party plugins (godot-sqlite, GdUnit4)
└── tests/                  # GdUnit4 scene integration tests
```

### AI-Assisted Development Integration
This template is optimized for AI development workflows:
- **Modular scenes** enable task-based AI delegation
- **C# strong typing** improves AI code generation accuracy
- **Three-layer architecture** isolates AI-generated logic from Godot dependencies
- **Fast unit tests** validate AI-generated code in milliseconds
- **SonarQube integration** catches AI-generated code issues automatically
- **Sentry monitoring** tracks issues in AI-generated releases

## Testing Framework

本模板采用**三层测试金字塔**策略，优化 TDD 和 AI 辅助开发工作流：

- **Unit Tests (80%)**: xUnit + FluentAssertions + NSubstitute - 纯 C# 逻辑，毫秒级红绿灯
- **Scene Tests (15%)**: GdUnit4 - Godot 集成测试，headless CI/CD 支持
- **E2E Tests (5%)**: 关键路径冒烟测试

### 快速启动

```bash
# 单元测试
dotnet test                                    # 运行所有测试
dotnet test --collect:"XPlat Code Coverage"    # 带覆盖率

# 场景测试
godot --headless --path . --gdunit-run         # CI/CD 模式
```

**完整指南**: 详见 [`docs/testing-framework.md`](docs/testing-framework.md)
- TDD 工作流和示例代码
- GdUnit4 场景测试模式
- CI/CD 质量门禁配置
- 确定性测试最佳实践
- 常见问题和工具推荐

## Task Master AI Instructions
**Import Task Master's development workflow commands and guidelines, treat as if import is in the main CLAUDE.md file.**
@./.taskmaster/CLAUDE.md
