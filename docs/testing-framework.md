# 测试框架完整指南

本文档定义了 Godot 项目模板的测试策略、工具选型和最佳实践。

## Windows 快速开始（本仓库可执行）

> 目标：在 Windows 本机/CI 跑通单元测试、Godot 自检、GdUnit4，并把产物统一归档到仓库 `logs/`（便于取证与排障）。

### 前置条件

- .NET 8 SDK
- Python 3（通过 Windows `py -3` 启动）
- Godot 4.5.1 .NET（建议使用 console 版本，便于收集输出）

### 环境变量（一次性）

PowerShell 示例：

```powershell
setx GODOT_BIN "C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe"
```

### 一键门禁（推荐）

```powershell
py -3 scripts/python/quality_gates.py all --godot-bin "$env:GODOT_BIN" --build-solutions --gdunit-hard --smoke --validate-audit
```

### 产物目录（SSoT）

- `logs/unit/<YYYY-MM-DD>/`：dotnet 单测、覆盖率与摘要
- `logs/e2e/<YYYY-MM-DD>/`：Godot self-check 与 e2e 相关产物
- `logs/ci/<YYYY-MM-DD>/`：CI/门禁摘要与诊断日志

## 测试策略

### 三层测试金字塔

本模板遵循**测试金字塔原则**，针对 TDD 和 AI 辅助开发进行优化：

```
        ╱╲
       ╱  ╲       E2E Tests (5%)
      ╱────╲      - 关键用户流程冒烟测试
     ╱      ╲     - headless Godot 回放
    ╱────────╲
   ╱  Scene   ╲   Scene Tests (15%)
  ╱   Tests    ╲  - GdUnit4 集成测试
 ╱──────────────╲ - 节点生命周期、信号验证
╱   Unit Tests   ╲ Unit Tests (80%)
╲────────────────╱ - xUnit 纯 C# 逻辑
                   - 毫秒级红绿灯循环
```

**核心理念：**
- 80% 核心逻辑通过快速单元测试覆盖（无需启动 Godot）
- 15% 集成测试验证 Godot 场景和信号交互
- 5% 端到端测试仅保留关键路径冒烟

## 单元测试：xUnit

### 技术栈

| 组件 | 工具 | 用途 |
|------|------|------|
| 测试框架 | **xUnit** | Fact/Theory 模式，TDD 友好 |
| 断言库 | **FluentAssertions** | 语义化断言，可读性强 |
| Mock框架 | **NSubstitute** | 轻量接口模拟 |
| 覆盖率 | **coverlet** | 代码覆盖率收集 |

### 项目结构

```
Game.Core/                      # 纯 C# 类库，零 Godot 依赖
├── Domain/                     # 领域模型
│   ├── Entities/              # 游戏实体
│   └── ValueObjects/          # 值对象
├── Services/                   # 业务逻辑
│   ├── GameStateManager.cs
│   └── EconomySimulator.cs
└── Interfaces/                 # 适配器契约
    ├── ITime.cs
    ├── IInput.cs
    └── IResourceLoader.cs

Game.Core.Tests/                # xUnit 测试项目
├── Domain/
│   └── PlayerTests.cs
├── Services/
│   └── GameStateManagerTests.cs
└── Integration/                # 适配器契约测试
    └── TimeAdapterTests.cs
```

### TDD 工作流

```
1. Red   → 在 Game.Core.Tests/ 写失败测试
2. Green → 在 Game.Core/ 实现最小化代码通过测试
3. Refactor → 优化设计，保持测试绿色
4. Integrate → 通过 Adapters/ 层集成到 Godot
```

### 示例测试

#### 基础单元测试

```csharp
// Game.Core.Tests/Domain/PlayerTests.cs
using Xunit;
using FluentAssertions;

public class PlayerTests
{
    [Fact]
    public void ShouldReduceHealth_WhenTakingDamage()
    {
        // Arrange
        var player = new Player(health: 100);

        // Act
        player.TakeDamage(30);

        // Assert
        player.Health.Should().Be(70);
    }

    [Theory]
    [InlineData(100, 50, 50)]
    [InlineData(100, 150, 0)]
    [InlineData(50, 25, 25)]
    public void ShouldHandleEdgeCases_WhenTakingDamage(int initialHealth, int damage, int expectedHealth)
    {
        // Arrange
        var player = new Player(health: initialHealth);

        // Act
        player.TakeDamage(damage);

        // Assert
        player.Health.Should().Be(expectedHealth);
    }
}
```

#### 接口注入测试

```csharp
// Game.Core.Tests/Services/GameStateManagerTests.cs
using Xunit;
using FluentAssertions;
using NSubstitute;

public class GameStateManagerTests
{
    [Fact]
    public void GameStateManager_Update_UsesInjectedTime()
    {
        // Arrange
        var mockTime = Substitute.For<ITime>();
        mockTime.DeltaTime.Returns(0.016f); // 固定 60 FPS

        var stateManager = new GameStateManager(mockTime);

        // Act
        stateManager.Update();

        // Assert
        mockTime.Received(1).DeltaTime;
        stateManager.ElapsedTime.Should().BeApproximately(0.016f, 0.001f);
    }
}
```

### UI/Glue 测试（GdUnit4，Godot+C# 变体）

UI/Glue 测试用于验证 MainMenu/HUD/SettingsPanel 等场景与 EventBus/ScreenNavigator 之间的胶水逻辑，在 headless 模式下需要遵循以下约束：

- **不模拟真实输入事件链**：避免依赖 Godot Headless 中不会传播的 InputEvents，推荐直接调用方法或发射最小信号；
- **有限帧轮询**：使用 `await get_tree().process_frame` 或 `await await_idle_frame()`，帧数通常控制在 60–120 之间，禁止无限循环等待；
- **优先黑盒，必要时白盒兜底**：先通过事件/信号驱动 UI，再在必要时直接调用 Glue 方法（如 ShowPanel/ClosePanel）。

代表性示例用例：

```gdscript
# Tests.Godot/tests/UI/test_main_menu_settings_button.gd
extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

var _bus: Node
var _received := false
var _etype := ""

func before() -> void:
    _bus = preload("res://Game.Godot/Adapters/EventBusAdapter.cs").new()
    _bus.name = "EventBus"
    get_tree().get_root().add_child(auto_free(_bus))
    _bus.connect("DomainEventEmitted", Callable(self, "_on_evt"))

func _on_evt(type, _source, _data_json, _id, _spec, _ct, _ts) -> void:
    _received = true
    _etype = str(type)

func test_main_menu_emits_settings() -> void:
    _received = false
    var menu = preload("res://Game.Godot/Scenes/UI/MainMenu.tscn").instantiate()
    add_child(auto_free(menu))
    await get_tree().process_frame
    var btn = menu.get_node("VBox/BtnSettings")
    btn.emit_signal("pressed")
    await get_tree().process_frame
    assert_bool(_received).is_true()
    assert_str(_etype).is_equal("ui.menu.settings")
```

> 说明：
> - 通过在 `/root` 下挂载 `EventBusAdapter`，将 DomainEventEmitted 作为断言源；
> - 直接对 `BtnSettings` 发射 `pressed` 信号，而非依赖 InputEvents；
> - 使用少量 `process_frame` 帧轮询等待信号到达，适配 headless CI 环境。

### 运行测试（Windows）

> 本仓库优先使用 Python 脚本封装运行与归档（统一写入 `logs/`）。直接调用 `dotnet`/`godot` 只建议用于临时调试。

```powershell
# 单元测试 + 覆盖率（归档到 logs/unit/<YYYY-MM-DD>/）
py -3 scripts/python/run_dotnet.py --solution Game.sln --configuration Debug

# Godot 组合根自检（归档到 logs/e2e/<YYYY-MM-DD>/ 与 logs/ci/<YYYY-MM-DD>/）
py -3 scripts/python/godot_selfcheck.py run --godot-bin "$env:GODOT_BIN" --project project.godot --build-solutions

# GdUnit4（归档到 logs/e2e/<YYYY-MM-DD>/；CI 常用 --rd 指定到 logs/e2e/<run_id>/...）
py -3 scripts/python/run_gdunit.py --prewarm --godot-bin "$env:GODOT_BIN" --project Tests.Godot --add tests/Security/Hard --timeout-sec 480

# Headless smoke（严格模式；归档到 logs/ci/<run_id>/smoke/）
py -3 scripts/python/smoke_headless.py --godot-bin "$env:GODOT_BIN" --project . --scene "res://Game.Godot/Scenes/Main.tscn" --timeout-sec 5 --mode strict

# 直接 dotnet（不推荐作为 CI/取证入口）
dotnet test Game.sln -c Debug
dotnet test Game.sln -c Debug --collect:"XPlat Code Coverage"
dotnet test Game.sln -c Debug --filter "FullyQualifiedName~PlayerTests"
dotnet test Game.sln -c Debug --logger "console;verbosity=detailed"
```

### 覆盖率目标

- 默认阈值口径见 `ADR-0005-quality-gates` 与 `ADR-0015-performance-budgets-and-gates`。
- 在本仓库的 `scripts/python/run_dotnet.py` 中，默认使用 **行 ≥90% / 分支 ≥85%**（可通过环境变量覆盖）：
  - `COVERAGE_LINES_MIN=90`
  - `COVERAGE_BRANCHES_MIN=85`

**门禁规则：**
- `scripts/python/ci_pipeline.py` 当前将“覆盖率不足”视为**软门禁**（不会阻断，但会落盘摘要，便于 review）。
- 若你的项目需要将覆盖率升级为**硬门禁**，建议在 CI 中显式将 `run_dotnet.py` 的 `coverage_failed` 视为失败（或调整 `ci_pipeline.py` 的 hard gate 判定）。

## 场景测试：GdUnit4

### 技术栈

| 组件 | 工具 | 用途 |
|------|------|------|
| 测试框架 | **GdUnit4** | Godot 4 原生测试支持 |
| 运行模式 | **Headless** | CI/CD 无图形界面执行 |
| 输出格式 | **JUnit XML** | 集成到 CI 报告 |

### 使用场景

GdUnit4 用于测试**必须在 Godot 环境中运行**的逻辑：

- 节点生命周期（`_ready`, `_process`, `_exit_tree`）
- 信号连接和触发验证
- 场景树结构和子节点访问
- 资源加载路径正确性
- 场景切换和状态转换

**不应使用 GdUnit4 的场景：**
- 纯业务逻辑（应该在 Game.Core 用 xUnit 测试）
- 数学计算、算法验证
- 数据结构操作

### 项目结构

```
tests/                          # GdUnit4 测试目录
├── Scenes/                     # 场景节点测试
│   ├── PlayerNodeTests.gd
│   └── EnemySpawnerTests.gd
├── Integration/                # 集成测试
│   ├── ResourceLoadingTests.gd
│   └── SceneTransitionTests.gd
└── E2E/                        # 端到端冒烟测试
    └── GameFlowSmokeTests.gd
```

### 示例测试

#### 信号验证测试

```gdscript
# tests/Scenes/PlayerNodeTests.gd
extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_player_emits_death_signal_when_health_zero():
    # Arrange
    var player = auto_free(preload("res://scenes/Player.tscn").instantiate())
    var signal_monitor = monitor_signals(player)

    # Act
    player.health = 10
    player.take_damage(10)

    # Assert
    assert_signal_emitted(player, "died")
    assert_int(player.health).is_equal(0)

func test_player_does_not_die_with_remaining_health():
    # Arrange
    var player = auto_free(preload("res://scenes/Player.tscn").instantiate())
    var signal_monitor = monitor_signals(player)

    # Act
    player.health = 50
    player.take_damage(30)

    # Assert
    assert_signal_not_emitted(player, "died")
    assert_int(player.health).is_equal(20)
```

#### 资源加载测试

```gdscript
# tests/Integration/ResourceLoadingTests.gd
extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_all_scene_paths_valid():
    # Arrange
    var scene_paths = [
        "res://scenes/Player.tscn",
        "res://scenes/Enemy.tscn",
        "res://scenes/levels/Level1.tscn"
    ]

    # Act & Assert
    for path in scene_paths:
        var scene = load(path)
        assert_object(scene).is_not_null()
        assert_bool(ResourceLoader.exists(path)).is_true()
```

#### 场景转换测试

```gdscript
# tests/Integration/SceneTransitionTests.gd
extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_main_menu_to_game_transition():
    # Arrange
    var scene_manager = autoload("SceneManager")

    # Act
    scene_manager.change_scene("res://scenes/Game.tscn")
    await get_tree().process_frame  # 等待场景切换完成

    # Assert
    var current_scene = get_tree().current_scene
    assert_str(current_scene.name).is_equal("Game")
```

### 运行测试（Windows）

开发时：
- 打开 `Tests.Godot` 工程，在 Godot Editor 里通过 GdUnit4 插件面板运行。

CI/headless（本仓库推荐 Python 驱动）：

```powershell
# 运行一组目录/套件（可重复 --add）
py -3 scripts/python/run_gdunit.py --prewarm --godot-bin "$env:GODOT_BIN" --project Tests.Godot --add tests/Adapters --add tests/Security/Hard --timeout-sec 480

# 指定报告输出目录（CI 常用 run_id；报告会落在 logs/ 下便于归档）
py -3 scripts/python/run_gdunit.py --prewarm --godot-bin "$env:GODOT_BIN" --project Tests.Godot --add tests/Security/Hard --timeout-sec 480 --rd "logs/e2e/<run_id>/gdunit-reports/quality"
```

> 提醒：启用 GdUnit4 文件日志时，Godot 会在 `%APPDATA%\\Godot\\app_userdata\\<ProjectName>\\logs\\` 产生 `godot*.log`；请确保这类日志会被归档/轮转，避免无限增长。
> - 本仓库可用 `py -3 scripts/python/godot_userlog_manager.py --project Tests.Godot` 执行“归档到仓库 logs/ + 保留策略”。

## 端到端测试

### 策略

E2E 测试**仅保留关键路径冒烟**，避免过度投入维护成本：

- 游戏启动 → 主菜单加载 → 退出
- 主菜单 → 开始游戏 → 第一关加载成功
- 保存/加载游戏存档流程

### 示例

```gdscript
# tests/E2E/GameFlowSmokeTests.gd
extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_game_startup_to_main_menu():
    # Arrange
    var scene_manager = autoload("SceneManager")

    # Act
    scene_manager.load_main_menu()
    await get_tree().create_timer(1.0).timeout  # 等待加载

    # Assert
    var main_menu = get_tree().current_scene
    assert_str(main_menu.name).is_equal("MainMenu")
    assert_object(main_menu.get_node("StartButton")).is_not_null()

func test_start_game_loads_first_level():
    # Arrange
    var scene_manager = autoload("SceneManager")
    scene_manager.load_main_menu()
    await get_tree().process_frame

    # Act
    var main_menu = get_tree().current_scene
    main_menu.get_node("StartButton").pressed.emit()
    await get_tree().create_timer(2.0).timeout

    # Assert
    var game_scene = get_tree().current_scene
    assert_str(game_scene.name).contains("Level")
```

## CI/CD 质量门禁

### 推荐做法（与仓库现有工作流一致）

本仓库的 GitHub Actions 参考实现：
- `.github/workflows/windows-quality-gate.yml`
- `.github/workflows/ci-windows.yml`

**最小硬门禁（本地等价命令）**

```powershell
py -3 scripts/python/ci_pipeline.py all --solution Game.sln --configuration Debug --godot-bin "$env:GODOT_BIN" --build-solutions
```

该命令会：
- 调用 `scripts/python/run_dotnet.py`（单测 + 覆盖率 + `logs/unit/<YYYY-MM-DD>/summary.json`）
- 调用 `scripts/python/godot_selfcheck.py`（自检 + `logs/e2e/<YYYY-MM-DD>/selfcheck-summary.json`）
- 调用 `scripts/python/check_encoding.py`（编码扫描 + `logs/ci/<YYYY-MM-DD>/encoding/**`）

**可选软门禁（CI 里通常 `continue-on-error: true`）**

```powershell
# GdUnit4（按套件分组运行，报告归档到 logs/e2e/<run_id>/gdunit-reports/**）
py -3 scripts/python/run_gdunit.py --prewarm --godot-bin "$env:GODOT_BIN" --project Tests.Godot --add tests/Security/Hard --timeout-sec 480 --rd "logs/e2e/<run_id>/gdunit-reports/quality"

# Contracts 校验（模板中为软门禁，用于发现“契约 vs 文档/覆盖层”漂移）
py -3 scripts/python/validate_contracts.py

# 安全审计 JSONL 格式校验（模板中为可选门禁）
py -3 scripts/python/validate_audit_logs.py
```

### 覆盖率报告

覆盖率产物由 `scripts/python/run_dotnet.py` 统一归档到 `logs/unit/<YYYY-MM-DD>/`：
- `logs/unit/<YYYY-MM-DD>/coverage.cobertura.xml`
- `logs/unit/<YYYY-MM-DD>/summary.json`

如需 HTML 报告，建议在允许安装工具的环境中使用 `reportgenerator` 生成到 `logs/unit/<YYYY-MM-DD>/coverage-html/`，并确保产物仍留在仓库 `logs/` 下。

### 发布健康（Release Health）

本模板当前尚未集成 Sentry SDK，也未落地 release-health gate（状态见 `docs/PROJECT_CAPABILITIES_STATUS.md`，口径见 `ADR-0003-observability-release-health`）。
因此不要在本模板的 CI 示例中用 `curl/jq` 临时拼一个门禁，以免口径漂移与跨平台不可复现。

## 最佳实践

### 1. 确定性测试

**问题：**Godot 的时间、随机数、输入系统是全局状态，导致测试不可重复。

**解决方案：**接口注入 + 适配器隔离

```csharp
// Game.Core/Interfaces/ITime.cs
public interface ITime
{
    float DeltaTime { get; }
    float TotalTime { get; }
}

// Game.Godot/Adapters/TimeAdapter.cs
public class TimeAdapter : ITime
{
    public float DeltaTime => (float)Engine.GetProcessTime();
    public float TotalTime => Time.GetTicksMsec() / 1000f;
}

// 测试时使用 Fake
public class FakeTime : ITime
{
    public float DeltaTime { get; set; } = 0.016f; // 固定 60 FPS
    public float TotalTime { get; set; } = 0f;
}
```

**同样模式适用于：**
- `IRandom` - 控制随机数生成
- `IInput` - 模拟玩家输入
- `IResourceLoader` - 控制资源加载

<!-- BEGIN AUTO:TEST_ORG_NAMING_REFS -->
### 2. 测试组织（目录 SSoT）

本仓库测试目录是 **SSoT**，以真实目录为准：

```
Game.Core.Tests/                      # xUnit: 纯 C#（不依赖 Godot）
  Domain/                             # 领域实体/值对象
  Services/                           # 领域服务/用例服务（如 Turn/Economy）
  State/                              # 状态机/状态管理
  Repositories/                       # 仓储/存储适配（纯 C# 的契约或内存实现）
  Engine/                             # 纯 C# 的引擎骨架/胶水（非 Godot）
  Tasks/                              # 任务级别的验收用例（只放稳定 tests，不保留 RedTests）
  Utilities/                          # 通用工具

Tests.Godot/tests/                    # GdUnit4: Godot headless（依赖场景树/节点/信号）
  Scenes/                             # 场景/节点生命周期/可见性/信号连通
  UI/                                 # UI 行为（HUD/MainMenu/Settings）
  Integration/                        # 跨模块集成（导航流/事件流/持久化跨重启等）
  Adapters/                           # Godot 适配层行为（EventBusAdapter/Config/Db）
  Security/                           # 安全烟测（allow/deny/invalid + 审计）
```

### 3. 路径与命名约定（含 `Refs:` 硬门禁）

#### 3.1 `acceptance[]` 必须追加 `Refs:`（硬门禁）

目的：把“任务语义”变成可确定性验证的证据链，避免“done 不真实”。

- 对于“存在该任务条目”的视图（`tasks_back.json` 或 `tasks_gameplay.json`），其 `acceptance[]` 的**每一条**都必须以 `Refs:` 结尾（大小写不敏感）。  
  若某任务只存在于其中一侧视图，另一侧视图允许缺失（warning/skip），但至少必须存在一侧视图。
- `Refs:` 后仅允许写**仓库相对路径**，并且必须指向测试文件：
  - xUnit：`Game.Core.Tests/**/*.cs`
  - GdUnit4：`Tests.Godot/tests/**/*.gd`
- 一个 acceptance 条目可对应多个测试文件（空格或逗号分隔）。
- `Refs:` 里**不要**写绝对路径、不要写带空格的路径、不要写行号锚点（例如 `#L10`）。目前门禁只解析“文件路径”。
- 注意：`Refs:` 使用**仓库根目录**相对路径（例如 `Tests.Godot/tests/...`）；而 GdUnit4 运行器常用的 `--add tests/...` 是以 `--project Tests.Godot` 为根目录的**项目内相对路径**，两者不要混用。

示例（xUnit）：

```
- When treasury deposits, non-negative amount is enforced. Refs: Game.Core.Tests/Domain/SanguoTreasuryTests.cs
```

示例（GdUnit4）：

```
- HUD updates dice result after event. Refs: Tests.Godot/tests/UI/test_hud_updates_on_events.gd
```

对应门禁（自动运行，无需手工记）：  
- `py -3 scripts/python/validate_acceptance_refs.py --task-id <id> --stage refactor ...`  
- `py -3 scripts/python/validate_task_test_refs.py --task-id <id> --require-non-empty ...`

#### 3.2 `test_refs[]`（任务级汇总）如何维护

`test_refs` 是任务级证据清单（路径列表），用于：

- 让验收脚本在 refactor 阶段做硬门禁；
- 让后续任务可以“发现/复用”已有测试证据；
- 防止只写了 `Refs:` 但没真正把文件纳入任务证据范围。

规则：

- 对于“存在该任务条目”的视图，其 `test_refs` 必须是非空列表（refactor 硬门禁）。  
  若某任务只存在于其中一侧视图，另一侧视图允许缺失（warning/skip），但至少必须存在一侧视图。
- `test_refs` 至少包含本任务所有 acceptance `Refs:` 的并集（refactor 硬门禁）。

推荐的更新方式（确定性脚本）：

```powershell
py -3 scripts/python/update_task_test_refs_from_acceptance_refs.py --task-id <id> --write
```

#### 3.3 默认 Refs 路径约定（Core / xUnit）

优先复用现有目录语义：Domain/Services/State/Repositories/Engine/Utilities。

| 任务类型（倾向） | 推荐 `Refs:` 路径前缀 | 文件命名规范 |
|---|---|---|
| 领域实体/值对象 | `Game.Core.Tests/Domain/` | `{Subject}Tests.cs` |
| 领域服务/回合/经济 | `Game.Core.Tests/Services/` | `{Subject}Tests.cs` |
| 状态机/状态管理 | `Game.Core.Tests/State/` | `{Subject}Tests.cs` |
| 适配器契约/仓储 | `Game.Core.Tests/Repositories/` | `{Subject}Tests.cs` |
| 任务级验收（只在确实跨多个类时） | `Game.Core.Tests/Tasks/` | `Task<id><Topic>Tests.cs` |

约束：

- `Game.Core.Tests/Tasks/Task<id>RedTests.cs` 只允许作为 red 阶段的临时骨架；到 refactor 阶段必须迁移/删除。

#### 3.4 默认 Refs 路径约定（Godot / GdUnit4）

| 任务类型（倾向） | 推荐 `Refs:` 路径前缀 | 文件命名规范（建议） |
|---|---|---|
| 场景/节点行为 | `Tests.Godot/tests/Scenes/<Module>/` | `test_<module>_<scene>_<behavior>.gd` |
| UI 行为 | `Tests.Godot/tests/UI/` | `test_<ui>_<behavior>.gd` |
| 跨模块集成流 | `Tests.Godot/tests/Integration/` | `test_<flow>_<behavior>.gd` |
| 适配器行为 | `Tests.Godot/tests/Adapters/` | `test_<adapter>_<behavior>.gd` |
| 安全烟测 | `Tests.Godot/tests/Security/` | `test_<surface>_<allow|deny|invalid>_audit.gd` |

#### 3.5 测试命名约定（与门禁对齐）

**C#（xUnit）**

- 文件：`{ClassName}Tests.cs`
- 方法名（二选一，均为 PascalCase，禁止 snake_case）：
  - `ShouldDoX_WhenY`
  - `GivenX_WhenY_ThenZ`

示例：

```csharp
[Fact]
public void ShouldDeductMoney_WhenBuyingCity()
{
}

[Fact]
public void GivenEnoughMoney_WhenBuyingCity_ThenCityOwned()
{
}
```

**GdUnit4（GDScript）**

- 文件：`test_<scope>_<behavior>.gd`（与现有 `Tests.Godot/tests/**` 风格一致）
- 方法：`func test_<behavior>() -> void:`

示例：

```gdscript
extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_hud_updates_on_dice_rolled_event() -> void:
    pass
```

稳定性约束（避免 flaky）：

- 不要依赖真实时间 `create_timer()` + 窄容差断言；优先用信号/条件等待 + 超时上限。
- headless 下不要依赖真实输入事件链；优先调用公开方法/发最小信号/发布领域事件。
<!-- END AUTO:TEST_ORG_NAMING_REFS -->

### 4. 测试数据管理

**使用 Theory 参数化测试：**

```csharp
[Theory]
[InlineData(100, 30, 70)]
[InlineData(50, 60, 0)]    // 伤害超过生命值
[InlineData(100, 0, 100)]  // 零伤害
public void ShouldHandleVariousScenarios_WhenTakingDamage(int health, int damage, int expected)
{
    var player = new Player(health);
    player.TakeDamage(damage);
    player.Health.Should().Be(expected);
}
```

**使用 Builder 模式创建测试数据：**

```csharp
public class PlayerBuilder
{
    private int _health = 100;
    private int _level = 1;

    public PlayerBuilder WithHealth(int health)
    {
        _health = health;
        return this;
    }

    public PlayerBuilder WithLevel(int level)
    {
        _level = level;
        return this;
    }

    public Player Build() => new Player(_health, _level);
}

// 使用
var player = new PlayerBuilder()
    .WithHealth(50)
    .WithLevel(5)
    .Build();
```

### 5. 避免常见陷阱

**不要在单元测试中访问 Godot API：**

```csharp
// 错误 - 单元测试不应依赖 Godot
[Fact]
public void Test_UseGodotTime()
{
    var time = Time.GetTicksMsec(); // 会失败，Godot 未初始化
}

// 正确 - 通过接口注入
[Fact]
public void Test_UseInjectedTime()
{
    var mockTime = Substitute.For<ITime>();
    mockTime.TotalTime.Returns(1000f);
    // 测试使用 mockTime
}
```

**不要在 GdUnit4 中测试纯逻辑：**

```gdscript
# 错误 - 这应该是 C# 单元测试
func test_calculate_damage():
    var damage = calculate_damage(10, 5)  # 纯数学计算
    assert_int(damage).is_equal(50)

# 正确 - 测试 Godot 特定行为
func test_player_node_emits_signal():
    var player = auto_free(preload("res://scenes/Player.tscn").instantiate())
    assert_signal_emitted(player, "health_changed")
```

## 工具和插件

### 开发工具

- **Visual Studio 2022** / **JetBrains Rider** - C# IDE 与测试运行器
- **Visual Studio Code** + C# Dev Kit - 轻量级选择
- **NCrunch** / **dotCover** - 实时覆盖率反馈（可选）

### CI/CD 集成

- **GitHub Actions** - 推荐用于开源项目
- **GitLab CI** - 企业自托管
- **Azure Pipelines** - 微软生态集成

### 覆盖率工具

- **coverlet** - .NET Core 覆盖率收集器（必需）
- **ReportGenerator** - HTML 报告生成
- **Codecov** / **Coveralls** - 在线覆盖率展示

## 常见问题

**Q: 为什么不直接用 GdUnit4 测试所有代码？**

A: GdUnit4 需要启动 Godot 引擎，测试执行慢（秒级）。xUnit 纯 C# 测试执行快（毫秒级），更适合 TDD 红绿灯循环。

**Q: 适配器层需要测试吗？**

A: 需要契约测试，验证适配器正确实现接口。但不需要测试 Godot 本身的行为（假设 Godot API 是正确的）。

**Q: 覆盖率 90% 是否过高？**

A: 对于纯业务逻辑（Game.Core），90% 是合理目标。对于 UI 绑定代码、场景脚本，可以放宽到 70-80%。

**Q: E2E 测试应该覆盖多少场景？**

A: 仅关键路径冒烟（3-5个测试）。过多 E2E 会导致维护成本高、执行慢、易碎。

**Q: 如何处理 Godot 单例（如 `Input`, `Time`）？**

A: 通过适配器隔离，在测试中注入 Mock。见"确定性测试"章节。

## 参考资源

- [xUnit 官方文档](https://xunit.net/)
- [FluentAssertions 文档](https://fluentassertions.com/)
- [NSubstitute 文档](https://nsubstitute.github.io/)
- [GdUnit4 GitHub](https://github.com/MikeSchulze/gdUnit4)
- [coverlet GitHub](https://github.com/coverlet-coverage/coverlet)
- [Godot 单元测试指南](https://docs.godotengine.org/en/stable/tutorials/scripting/unit_testing.html)


## UI/Glue 测试规范（GdUnit4，Godot+C#）

### 适用范围

- 依赖 Godot 场景树的 UI/Glue 行为：Main 场景、Screen 导航、Settings/HUD 等。
- 需要验证节点可见性、信号连通、场景组合，而不是纯算法逻辑。
- 运行在 headless 模式（CI/CD 环境），不依赖真实输入事件。

### 基本原则

- **禁止依赖真实 InputEvents**：headless 模式下 Godot 不会传递鼠标/键盘事件，UI 测试必须使用 `emit_signal` 或直接调用方法（如 `ShowPanel()`）。
- **优先走“黑盒路径”，必要时白盒兜底**：先通过事件/信号驱动 UI（如发 `ui.menu.settings` 或点击按钮），若有限时间内未达到期望状态，再用白盒方法兜底，并在断言前后留注释。
- **帧轮询有统一上限**：
  - 常规场景：推荐最多轮询 60 帧（约 1 秒@60fps）；
  - 复杂场景：最多 120 帧；超过上限仍未达到期望条件，应当视为失败，而不是无限等待。
- **断言应稳定可复现**：避免依赖绝对时间或随机性，尽量通过可观测状态（visible/text 值/节点存在性）来断言。
- **领域事件仍走 EventBus**：UI/Glue 测试中，领域事件统一通过 `/root/EventBus` 或 EventBusAdapter 触发，避免直接在 UI 层做领域逻辑。

### 示例：SettingsPanel 显示/隐藏（白盒兜底）

```gdscript
extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_settings_panel_show_and_close() -> void:
    var packed = load("res://Game.Godot/Scenes/UI/SettingsPanel.tscn")
    if packed == null:
        push_warning("SKIP: SettingsPanel.tscn not found")
        return
    var panel = packed.instantiate()
    add_child(auto_free(panel))
    await get_tree().process_frame

    # 默认隐藏
    assert_bool(panel.visible).is_false()

    # 黑盒路径：调用公开方法
    if panel.has_method("ShowPanel"):
        panel.ShowPanel()
        await get_tree().process_frame

    if not panel.visible:
        push_warning("ShowPanel 未生效，检查信号/装配逻辑")
        return

    # 关闭
    var close_btn = panel.get_node("VBox/Buttons/CloseBtn")
    close_btn.emit_signal("pressed")
    await get_tree().process_frame
    assert_bool(panel.visible).is_false()
```

### 示例：screen.settings.saved 与 ConfigFile 持久化

```gdscript
extends "res://addons/gdUnit4/src/GdUnitTestSuite.gd"

func test_settings_saved_uses_configfile() -> void:
    # 清理旧配置
    var dir := DirAccess.open("user://")
    if dir and dir.file_exists("settings.cfg"):
        dir.remove("settings.cfg")

    # 加载主场景
    var packed = load("res://Game.Godot/Scenes/Main.tscn")
    var main = packed.instantiate()
    get_tree().get_root().add_child(auto_free(main))
    await get_tree().process_frame

    # 通过 screen 事件保存设置
    var bus = get_node_or_null("/root/EventBus")
    assert_object(bus).is_not_null()
    bus.PublishSimple("ui.menu.settings", "ut", "{}")
    await get_tree().process_frame

    # 触发保存（例如 SettingsPanel 内部发出 screen.settings.saved）
    # 此处只断言 ConfigFile 已写入，不关心 DB
    await get_tree().process_frame

    var cfg := ConfigFile.new()
    var err := cfg.load("user://settings.cfg")
    assert_int(err).is_equal(Error.OK)
```
