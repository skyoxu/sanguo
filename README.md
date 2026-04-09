[![Windows Export Slim](https://github.com/skyoxu/sanguo/actions/workflows/windows-export-slim.yml/badge.svg)](https://github.com/skyoxu/sanguo/actions/workflows/windows-export-slim.yml) [![Windows Release](https://github.com/skyoxu/sanguo/actions/workflows/windows-release.yml/badge.svg)](https://github.com/skyoxu/sanguo/actions/workflows/windows-release.yml) [![Windows Quality Gate](https://github.com/skyoxu/sanguo/actions/workflows/windows-quality-gate.yml/badge.svg)](https://github.com/skyoxu/sanguo/actions/workflows/windows-quality-gate.yml)

# Sanguo (Godot 4.5 + C#)

`skyoxu/sanguo` 是一个 Windows-only 的 Godot 4.5 + C# 游戏仓库。它继承上游 `godotgame` 模板的脚本、质量门禁和协作工具链，同时承载当前“三国”主题玩法与 PRD/Taskmaster/Overlay 演进。

## About This Repository

### Why This Repo Exists
- **Upstream template lineage**: 继承 `godotgame` 的 Windows-only Godot + C# 基础设施，但当前仓库身份、任务编排和文档入口以 `sanguo` 为准。
- **Business-repo posture**: 这不是一个空白模板仓；它已经包含当前 PRD、任务分解、Overlay 文档和游戏实现。
- **Target**: 单机策略/经营/棋盘驱动游戏，强调可测试架构、交付节奏控制和 AI 协作闭环。

### Key Features
- **Delivery-profile driven**: `playable-ea` / `fast-ship` / `standard` 统一控制测试、验收、review、security 默认姿态。
- **Persistent harness**: local hard checks、review pipeline、inspect/replay sidecar、execution plans、decision logs。
- **Closed-loop testing**: `sc-test`、`acceptance_check`、`tdd`、GdUnit/xUnit、C# test conventions。
- **Overlay authoring workflow**: 支持 PRD -> Overlay 08 的 batch dry-run / simulate / repair / apply。

**Full technical details**: See `AGENTS.md`, `DELIVERY_PROFILE.md`, and `docs/agents/00-index.md`

---

## 3-Minute From Zero to Run

1. 安装 Godot .NET（mono）并设置环境：
   - `setx GODOT_BIN C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe`
2. 恢复并编译：
   - `dotnet build .\GodotGame.csproj -c Debug`
3. 本地最小硬门禁：
   - `py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "%GODOT_BIN%"`
4. 启动 Godot：
   - Editor: `Godot_v4.5.1-stable_mono_win64.exe`
   - Console: `"%GODOT_BIN%" --path .`

## Delivery Profiles

- `playable-ea`
  - 目标：最快验证可玩性
  - 特征：弱化重治理和重文档约束，默认安全姿态 `host-safe`
- `fast-ship`
  - 目标：当前本仓默认开发档位
  - 特征：保留基本主机安全、核心测试、必要验收和 review 止损
- `standard`
  - 目标：收口档位
  - 特征：更严格的 ADR / acceptance / semantic / evidence 要求，默认安全姿态 `strict`

优先级：
- CLI `--delivery-profile`
- 环境变量 `DELIVERY_PROFILE`
- `scripts/sc/config/delivery_profiles.json` 的 `default_profile`

## Quick Links

- 当前阶段说明：`CURRENT_STAGE_FOR_BMAD.md`
- 当前主 PRD：`prd_v3.md`
- 规则冻结：`PRD_V3_RULES_FREEZE.md`
- 规则映射：`PRD_V3_TRACEABILITY_MATRIX.md`
- 验收断言：`PRD_V3_ACCEPTANCE_ASSERTIONS.md`
- Delivery Profile：`DELIVERY_PROFILE.md`
- 文档索引：`docs/PROJECT_DOCUMENTATION_INDEX.md`
- 能力状态：`docs/PROJECT_CAPABILITIES_STATUS.md`
- Agent 知识索引：`docs/agents/00-index.md`
- Run Protocol：`docs/workflows/run-protocol.md`
- Local Hard Checks：`docs/workflows/local-hard-checks.md`
- Overlay Quickstart：`docs/workflows/overlay-generation-quickstart.md`
- Overlay SOP：`docs/workflows/overlay-generation-sop.md`
- Overlay Authoring Guide：`docs/workflows/overlays-authoring-guide.md`
- Testing Framework：`docs/testing-framework.md`
- Technical Debt Register：`docs/technical-debt.md`
- Session Recovery：`docs/agents/01-session-recovery.md`

- Project Health Dashboard: `docs/workflows/project-health-dashboard.md`
- Stable Public Entrypoints: `docs/workflows/stable-public-entrypoints.md`
- Script Entrypoints Index: `docs/workflows/script-entrypoints-index.md`
- Template Upgrade Protocol: `docs/workflows/template-upgrade-protocol.md`
- Business Repo Upgrade Guide: `docs/workflows/business-repo-upgrade-guide.md`
- Prototype Lane: `docs/workflows/prototype-lane.md`
- Directory Responsibilities: `docs/agents/16-directory-responsibilities.md`

## Recovery First

当会话重置或跨设备恢复任务时，先走恢复入口，不要先做全量重跑：

1. 阅读 `docs/agents/01-session-recovery.md`
2. 运行 `py -3 scripts/python/dev_cli.py resume-task --task-id <task-id>`
3. 仍不足时，再运行 `py -3 scripts/python/inspect_run.py --kind pipeline --task-id <task-id>`

在决定是否重开完整 `6.7` 前，先看这些字段：

- `Latest reason`
- `Latest run type`
- `Latest reuse mode`
- `Latest artifact integrity`
- `Chapter6 blocked by`
- `Chapter6 stop-loss note`
- `recommended_action_why`

恢复止损规则：

- `run_type = planned-only` 或 `reason = planned_only_incomplete`：该包仅作证据，不直接进入 `6.7`/`6.8`
- `Chapter6 blocked by = artifact_integrity`：先回退到上一个真实产物包，再决定是否重跑
- `rerun_guard`：已判定不应重复支付 deterministic 成本
- `llm_retry_stop_loss`：优先走窄路径 LLM 收口，不直接重开全量
- `sc_test_retry_stop_loss`：同轮 unit 重试已证明浪费，先修 root cause
- `waste_signals`：已出现单测失败后仍执行高成本 lane 的浪费信号
- `recommended_action = needs-fix-fast`：优先 targeted closure，不先开全量重跑
## Main Entrypoints

### Repo-Scoped Hard Checks

```powershell
py -3 scripts/python/dev_cli.py run-local-hard-checks --godot-bin "$env:GODOT_BIN"
py -3 scripts/python/inspect_run.py --kind local-hard-checks
```

### Task-Scoped Review Pipeline

```powershell
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --godot-bin "$env:GODOT_BIN" --delivery-profile fast-ship --skip-llm-review
py -3 scripts/python/inspect_run.py --kind pipeline --task-id <id>
```


### Task Recovery

```powershell
py -3 scripts/python/dev_cli.py resume-task --task-id <id>
py -3 scripts/sc/run_review_pipeline.py --task-id <id> --resume
```
### Acceptance Test Generation / TDD

```powershell
py -3 scripts/sc/llm_generate_tests_from_acceptance_refs.py --task-id <id> --tdd-stage red-first --verify auto --godot-bin "$env:GODOT_BIN"
py -3 scripts/sc/build.py tdd --task-id <id> --stage green
py -3 scripts/python/check_csharp_test_conventions.py --task-id <id>
```

### Overlay Generation

```powershell
py -3 scripts/sc/llm_generate_overlays_batch.py --prd prd_v3.md --prd-id PRD-SANGUO-V3 --prd-docs PRD_V3_TRACEABILITY_MATRIX.md,PRD_V3_RULES_FREEZE.md,PRD_V3_ACCEPTANCE_ASSERTIONS.md --page-family core --page-mode scaffold --timeout-sec 1200 --dry-run --batch-suffix local-smoke
```

## Task / ADR / PRD Tooling

- `scripts/python/task_links_validate.py`
  - 校验 Taskmaster triplet 与 ADR / chapter / overlay 回链
- `scripts/python/sync_task_overlay_refs.py`
  - 统一同步 triplet 的 overlay refs
- `scripts/python/validate_overlay_execution.py`
  - 校验 overlay execution 文档结构和引用
- `scripts/python/validate_recovery_docs.py`
  - 校验 `execution-plans/` 与 `decision-logs/`
- `scripts/python/validate_docs_utf8_no_bom.py`
  - 对 `docs/.github/.taskmaster/AGENTS.md` 做 UTF-8 无 BOM 门禁

## Naming And Identity

- GitHub 仓库名：`skyoxu/sanguo`
- 内部 Godot .NET 主工程：`GodotGame.csproj` / `GodotGame.sln`
- 领域与测试工程：`Game.Core`、`Game.Godot`、`Game.Core.Tests`、`Game.Godot.Tests`
- 当文档提到 `godotgame` 时，默认表示上游通用模板，不表示当前仓库身份
- 当前任务与 PRD 演进、运行时实现、日志与工件路径均以 `C:\buildgame\sanguo` 为准

## Notes

- DB 后端：默认插件优先；`GODOT_DB_BACKEND=plugin|managed` 可控
- 示例 UI/测试：默认关闭；设置 `TEMPLATE_DEMO=1` 启用（Examples/**）
- 所有安全/网络/文件/权限审计与测试输出统一落到 `logs/`

## Feature Flags

- Autoload：`/root/FeatureFlags`（文件：`Game.Godot/Scripts/Config/FeatureFlags.cs`）
- 环境变量优先生效：
  - 单项：`setx FEATURE_demo_screens 1`
  - 多项：`setx GAME_FEATURES "demo_screens,perf_overlay"`
- 文件配置：`user://config/features.json`
- 代码示例：`if (FeatureFlags.IsEnabled("demo_screens")) { /* ... */ }`

## Release

- 创建标签：`git tag v0.1.1 -m "v0.1.1 release"`
- 推送标签：`git push origin v0.1.1`
- 工作流：`Windows Release (Tag)` 自动导出并附加 `build/Game.exe`
- 手动导出：运行 `Windows Release (Manual)` 或 `Windows Export Slim`
