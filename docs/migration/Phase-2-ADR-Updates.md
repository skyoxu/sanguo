# Phase 2: ADR 更新与新增

> 状态: 设计阶段
> 预估工时: 1-2 天
> 风险等级: 低
> 前置条件: Phase 1 完成

---

## 目标

制定 Godot 4.5 + C# 技术栈的架构决策记录（ADR），明确技术选型理由、约束条件和实施策略。

---

## ADR 新增清单

### ADR-0018: Godot Runtime and Distribution
### ADR-0019: Godot Security Baseline
### ADR-0020: Godot Test Strategy (TDD + GdUnit4)
### ADR-0021: C# Domain Layer Architecture
### ADR-0022: Godot Signal System and Contracts

### ADR 更新清单

以下现有 ADR 需要更新以支持 Godot 技术栈：

- **ADR-0003**: 可观测性 → 更新 Sentry Godot SDK 配置
- **ADR-0005**: 质量门禁 → 更新为 C#/.NET 工具链
- **ADR-0006**: 数据存储 → 更新为 godot-sqlite 适配
- **ADR-0015**: 性能预算 → 更新为 Godot 性能指标

---

## ADR-0018: Godot Runtime and Distribution

**文件路径**: `docs/adr/ADR-0018-godot-runtime-and-distribution.md`

**状态**: Proposed → Accepted（迁移启动后）

**核心决策**:

1. **运行时**: Godot Engine 4.5 (.NET 版本)
2. **分发方式**: Windows Desktop .exe + .pck 资源包
3. **平台支持**: Windows-only（ADR-0011 延续）
4. **版本锁定**: Godot 4.5.x stable + .NET 8 LTS

**理由**:

- [OK] 统一运行时：游戏引擎 + UI + 渲染 + 物理统一到 Godot
- [OK] 原生性能：无 Chromium 开销，启动速度提升 60%+
- [OK] 成熟工具链：Scene Editor + Node 系统 + 可视化调试
- [OK] C# 强类型：避免 GDScript 动态类型风险，利于 AI 生成代码
- [警告] 学习曲线：团队需要熟悉 Godot Scene Tree 与 Signals

**后果**:

- Electron/React/Phaser 完全弃用
- UI 从 React 组件迁移到 Godot Control 节点
- 事件系统从 CloudEvents 迁移到 Godot Signals
- 测试栈从 Vitest/Playwright 迁移到 xUnit/GdUnit4

**实施约束**:

- Export Templates 必须在 CI 缓存
- .pck 资源包需要签名（防篡改）
- 首次启动解压 .pck 需要进度提示

**参考资料**:
- Godot 4.5 文档: https://docs.godotengine.org/en/stable/
- C# 支持文档: https://docs.godotengine.org/en/stable/tutorials/scripting/c_sharp/

---

## ADR-0019: Godot Security Baseline

**文件路径**: `docs/adr/ADR-0019-godot-security-baseline.md`

**状态**: Proposed → Accepted

**核心决策**:

取代 ADR-0002（Electron 安全基线），建立 Godot 特定的安全口径：

1. **外链打开**: 仅允许 `https://` + 域白名单 + 审计日志
2. **HTTP 请求**: 统一 HTTPRequest 封装 + 域白名单 + 审计
3. **文件系统**: 强制 `user://` 写入，禁止任意绝对路径
4. **代码执行**: 禁止动态加载外部脚本/DLL/P_Invoke
5. **自启动控制**: 入口场景固定 + Autoload 白名单
6. **隐私保护**: Sentry 脱敏 + 用户 ID 哈希

**实施方式**:

```csharp
// C# equivalent (Godot 4 + C# + GdUnit4)
using Godot;
using System.Threading.Tasks;

public partial class ExampleTest
{
    public async Task Example()
    {
        var scene = GD.Load<PackedScene>("res://Game.Godot/Scenes/MainScene.tscn");
        var inst = scene?.Instantiate();
        var tree = (SceneTree)Engine.GetMainLoop();
        tree.Root.AddChild(inst);
        await ToSignal(tree, SceneTree.SignalName.ProcessFrame);
        inst.QueueFree();
    }
}
```

**C# 适配层**:

```csharp
// Game.Godot/Adapters/SecurityAdapter.cs

public class SecurityAdapter : ISecurityService
{
    private readonly Node _securityAutoload;

    public SecurityAdapter()
    {
        _securityAutoload = ((SceneTree)Engine.GetMainLoop())
            .Root.GetNode("/root/Security");
    }

    public bool OpenUrlSafe(string url)
    {
        return (bool)_securityAutoload.Call("open_url_safe", url);
    }
}
```

**测试要求（GdUnit4 + xUnit）**:

```csharp
// Game.Core.Tests/SecurityTests.cs

[Fact]
public void OpenUrlSafe_ShouldRejectNonHttps()
{
    // Arrange
    var security = new FakeSecurityService();

    // Act
    var result = security.OpenUrlSafe("http://example.com");

    // Assert
    result.Should().BeFalse();
    security.ViolationLogs.Should().Contain(
        log => log.Reason == "URL not HTTPS"
    );
}

[Fact]
public void OpenUrlSafe_ShouldRejectUnlistedDomain()
{
    var security = new FakeSecurityService();
    var result = security.OpenUrlSafe("https://evil.com");

    result.Should().BeFalse();
    security.ViolationLogs.Should().Contain(
        log => log.Reason == "URL not in whitelist"
    );
}

[Fact]
public void OpenUrlSafe_ShouldAllowWhitelistedHttps()
{
    var security = new FakeSecurityService();
    var result = security.OpenUrlSafe("https://example.com/path");

    result.Should().BeTrue();
    security.AuditLogs.Should().Contain(
        log => log.Action == "URL opened"
    );
}
```

**门禁要求**:

- CI 运行 `scripts/ci/godot-security-audit.py`
- 扫描 `.gd`/`.cs` 文件，检测：
  - 裸调用 `OS.shell_open()` 而非 `Security.open_url_safe()`
  - 裸调用 `HTTPRequest` 而非 `Security.http_request_safe()`
  - 使用 `load()` 加载非 `res://` 路径
  - 使用 `FileAccess.open()` 绝对路径而非 `user://`
- 违例必须修复才能合并

**迁移对照**:

| Electron 概念 | Godot 对应 | 实施方式 |
|-------------|-----------|---------|
| webContents.setWindowOpenHandler | OS.shell_open() 封装 | Security.open_url_safe() |
| CSP (Content-Security-Policy) | HTTPRequest 白名单 | Security.http_request_safe() |
| Preload 白名单 | Autoload 单例白名单 | project.godot [autoload] 受控 |
| contextIsolation | - | 不适用（无 Renderer 进程） |

---

## ADR-0020: Godot Test Strategy (TDD + GdUnit4)

**文件路径**: `docs/adr/ADR-0020-godot-test-strategy.md`

**状态**: Proposed → Accepted

**核心决策**:

建立三层测试体系，支持 TDD 红绿灯循环：

1. **纯逻辑单元测试** (xUnit + FluentAssertions + NSubstitute)
   - 项目: `Game.Core.Tests`
   - 范围: 不依赖 Godot 的纯 C# 逻辑
   - 覆盖率要求: ≥90% 行覆盖率、≥85% 分支覆盖率

2. **适配层测试** (xUnit + Mock Godot API)
   - 项目: `Game.Core.Tests`（契约测试部分）
   - 范围: 测试 `ITime`/`IInput`/`IResourceLoader` 等接口
   - 方式: Fake/Mock 注入，不启动 Godot Engine

3. **场景集成测试** (GdUnit4)
   - 项目: `Game.Godot.Tests`
   - 范围: Node 生命周期、Signal 连接、资源加载
   - 运行方式: `godot --headless --run-tests`

4. **E2E 冒烟测试** (Godot Headless + 自建 TestRunner)
   - 项目: `Game.Godot.Tests/E2E`
   - 范围: 启动→主场景→关键信号→退出
   - 运行方式: `godot --headless --path . --scene res://Tests/E2ERunner.tscn`

**分层原则**:

```
                          ┌─────────────────┐
                          │  E2E 冒烟测试    │
                          │ (GdUnit4 Headless)│
                          └─────────────────┘
                                  ▲
                                  │
                          ┌───────┴────────┐
                          │  场景集成测试   │
                          │   (GdUnit4)    │
                          └───────┬────────┘
                                  ▲
                                  │
                    ┌─────────────┴──────────────┐
                    │   适配层测试 (xUnit Mock)   │
                    └─────────────┬──────────────┘
                                  ▲
                                  │
                    ┌─────────────┴──────────────┐
                    │   纯逻辑单元测试 (xUnit)     │
                    │   (Game.Core.Tests)        │
                    └────────────────────────────┘
```

**TDD 工作流**:

```csharp
// 1. 红灯：先写失败的测试 (Game.Core.Tests)
[Fact]
public void CalculateDamage_WithCritical_ShouldDouble()
{
    // Arrange
    var calculator = new DamageCalculator();
    var attack = new Attack { BaseDamage = 100, IsCritical = true };

    // Act
    var damage = calculator.Calculate(attack);

    // Assert
    damage.Should().Be(200);
}

// 2. 绿灯：实现最小代码让测试通过 (Game.Core)
public class DamageCalculator
{
    public int Calculate(Attack attack)
    {
        return attack.IsCritical ? attack.BaseDamage * 2 : attack.BaseDamage;
    }
}

// 3. 重构：改进代码质量
public class DamageCalculator
{
    private const int CriticalMultiplier = 2;

    public int Calculate(Attack attack)
    {
        var damage = attack.BaseDamage;
        if (attack.IsCritical)
        {
            damage *= CriticalMultiplier;
        }
        return damage;
    }
}
```

**隔离 Godot 依赖**:

```csharp
// 接口定义 (Game.Core/Ports)
public interface ITime
{
    double GetTimestamp();
    double GetDeltaTime();
}

// Fake 实现 (Game.Core.Tests)
public class FakeTime : ITime
{
    public double CurrentTime { get; set; } = 0;
    public double Delta { get; set; } = 0.016; // 60 FPS

    public double GetTimestamp() => CurrentTime;
    public double GetDeltaTime() => Delta;
}

// Godot 实现 (Game.Godot/Adapters)
public class GodotTimeAdapter : ITime
{
    public double GetTimestamp() => Time.GetTicksMsec() / 1000.0;
    public double GetDeltaTime() => Engine.GetPhysicsInterpolationFraction();
}

// 使用依赖注入
public class GameLoop
{
    private readonly ITime _time;

    public GameLoop(ITime time) // 构造器注入
    {
        _time = time;
    }

    public void Update()
    {
        var delta = _time.GetDeltaTime();
        // 游戏逻辑...
    }
}
```

**GdUnit4 场景测试示例**:

```csharp
// C# equivalent (Godot 4 + C# + GdUnit4)
using Godot;
using System.Threading.Tasks;

public partial class ExampleTest
{
    public async Task Example()
    {
        var scene = GD.Load<PackedScene>("res://Game.Godot/Scenes/MainScene.tscn");
        var inst = scene?.Instantiate();
        var tree = (SceneTree)Engine.GetMainLoop();
        tree.Root.AddChild(inst);
        await ToSignal(tree, SceneTree.SignalName.ProcessFrame);
        inst.QueueFree();
    }
}
```

**CI 集成**:

```powershell
# scripts/ci/run-tests.ps1

# 1. 运行 xUnit 单元测试 + 覆盖率
dotnet test Game.Core.Tests/Game.Core.Tests.csproj `
    --configuration Release `
    --collect:"XPlat Code Coverage" `
    --results-directory ./TestResults

# 2. 生成覆盖率报告
reportgenerator `
    -reports:"./TestResults/**/coverage.cobertura.xml" `
    -targetdir:"./coverage" `
    -reporttypes:"Html;Cobertura"

# 3. 运行 GdUnit4 场景测试
godot --headless --path . `
    --script res://addons/gdUnit4/bin/GdUnitCmdTool.cs `
    --conf res://GdUnitRunner.cfg `
    --output ./TestResults/gdunit4-results.xml

# 4. 运行 E2E 冒烟测试
godot --headless --path . `
    --scene res://Tests/E2ERunner.tscn `
    --quit-after 60
```

**覆盖率门禁**:

- xUnit 覆盖率 ≥90% 行 / ≥85% 分支（沿用 ADR-0005）
- GdUnit4 场景测试至少覆盖主场景、关键 UI、核心信号
- E2E 冒烟必须通过：启动、主场景加载、退出无崩溃

---

## ADR-0021: C# Domain Layer Architecture

**文件路径**: `docs/adr/ADR-0021-csharp-domain-layer-architecture.md`

**状态**: Proposed → Accepted

**核心决策**:

采用 **端口适配器模式**（Ports and Adapters / Hexagonal Architecture）分离纯逻辑与 Godot 依赖：

```
Game.Core (Pure C#)          Game.Godot (Godot C#)
─────────────────────       ──────────────────────
│                   │       │                    │
│  Domain Models    │       │  Adapters          │
│  ├─ Entities      │◄──────┤  ├─ GodotTimeAdapter
│  ├─ Value Objects │       │  ├─ GodotInputAdapter
│  └─ Services      │       │  └─ GodotResourceLoader
│                   │       │                    │
│  Ports (Interface)│       │  Scenes & Scripts  │
│  ├─ ITime         │       │  ├─ Main.tscn     │
│  ├─ IInput        │◄──────┤  ├─ Player.cs     │
│  ├─ IResourceLoad│       │  └─ Autoloads/    │
│  └─ IDataStore   │       │                    │
└───────────────────┘       └────────────────────┘
```

**项目结构**:

```
Game.Core/                          # .NET Class Library (不引用 Godot)
├─ Domain/
│  ├─ Entities/
│  │  ├─ Player.cs
│  │  ├─ Enemy.cs
│  │  └─ Item.cs
│  ├─ ValueObjects/
│  │  ├─ Position.cs
│  │  ├─ Health.cs
│  │  └─ Damage.cs
│  └─ Services/
│     ├─ CombatService.cs
│     ├─ InventoryService.cs
│     └─ ScoreService.cs
├─ Ports/ (Interfaces)
│  ├─ ITime.cs
│  ├─ IInput.cs
│  ├─ IResourceLoader.cs
│  └─ IDataStore.cs
└─ Game.Core.csproj

Game.Core.Tests/                    # xUnit 测试项目
├─ Domain/
│  ├─ CombatServiceTests.cs
│  └─ InventoryServiceTests.cs
├─ Fakes/
│  ├─ FakeTime.cs
│  ├─ FakeInput.cs
│  └─ FakeDataStore.cs
└─ Game.Core.Tests.csproj

Game.Godot/                         # Godot 项目（引用 Game.Core）
├─ Adapters/
│  ├─ GodotTimeAdapter.cs
│  ├─ GodotInputAdapter.cs
│  └─ GodotResourceLoader.cs
├─ Scenes/
│  ├─ Main.tscn
│  └─ Player.tscn
├─ Scripts/
│  ├─ PlayerController.cs          # 薄层：仅装配 + 信号转发
│  └─ EnemyController.cs
└─ Autoloads/
   ├─ ServiceLocator.cs             # DI 容器（手动注入）
   ├─ Security.cs                   # GDScript 安全封装
   └─ Observability.cs              # Sentry 初始化
```

**依赖注入示例**:

```csharp
// Autoload: ServiceLocator.cs (单例)
public partial class ServiceLocator : Node
{
    public static ServiceLocator Instance { get; private set; }

    public ITime Time { get; private set; }
    public IInput InputService { get; private set; }
    public IDataStore DataStore { get; private set; }

    public override void _Ready()
    {
        Instance = this;

        // 注入 Godot 适配器
        Time = new GodotTimeAdapter();
        InputService = new GodotInputAdapter();
        DataStore = new SqliteDataStore();
    }
}

// 使用示例 (PlayerController.cs)
public partial class PlayerController : Node2D
{
    private Player _player;
    private CombatService _combatService;

    public override void _Ready()
    {
        // 从 ServiceLocator 获取依赖
        var time = ServiceLocator.Instance.Time;
        var input = ServiceLocator.Instance.InputService;

        _player = new Player(time);
        _combatService = new CombatService(time);
    }

    public override void _Process(double delta)
    {
        var input = ServiceLocator.Instance.InputService;
        _player.HandleInput(input);
    }
}
```

**测试示例**:

```csharp
// Game.Core.Tests/Domain/CombatServiceTests.cs
public class CombatServiceTests
{
    [Fact]
    public void Attack_WithCritical_ShouldApplyMultiplier()
    {
        // Arrange
        var fakeTime = new FakeTime();
        var combatService = new CombatService(fakeTime);
        var attacker = new Player(fakeTime) { AttackPower = 100 };
        var target = new Enemy { Health = 1000 };

        // Act
        combatService.Attack(attacker, target, isCritical: true);

        // Assert
        target.Health.Should().Be(800); // 1000 - (100 * 2)
    }
}
```

**优势**:

- [OK] TDD 友好：80% 逻辑在不启动 Godot 的情况下测试
- [OK] 快速反馈：xUnit 测试秒级完成（vs GdUnit4 分钟级）
- [OK] 可移植性：Game.Core 可复用到其他 .NET 项目
- [OK] AI 生成友好：纯 C# 代码，类型明确，易于 Copilot/Claude 辅助

**约束**:

- Game.Core 项目禁止引用 Godot NuGet 包
- 所有 Godot API 调用必须经过接口（Ports）
- ServiceLocator 仅在 Godot 入口点使用（避免全局滥用）

---

## ADR-0022: Godot Signal System and Contracts

**文件路径**: `docs/adr/ADR-0022-godot-signal-system-and-contracts.md`

**状态**: Proposed → Accepted

**核心决策**:

从 CloudEvents 1.0 迁移到 Godot Signals，保留契约驱动开发思想：

**Godot Signal 命名规范**:

```csharp
// C# equivalent (Godot 4 + C# + GdUnit4)
using Godot;
using System.Threading.Tasks;

public partial class ExampleTest
{
    public async Task Example()
    {
        var scene = GD.Load<PackedScene>("res://Game.Godot/Scenes/MainScene.tscn");
        var inst = scene?.Instantiate();
        var tree = (SceneTree)Engine.GetMainLoop();
        tree.Root.AddChild(inst);
        await ToSignal(tree, SceneTree.SignalName.ProcessFrame);
        inst.QueueFree();
    }
}
```

**契约文档模板**:

```markdown
## Signal Contract: player_health_changed

### 契约声明
- **Signal Name**: `player_health_changed`
- **Description**: 玩家生命值变化时触发
- **Module**: Player System
- **ADR References**: ADR-0022

### 参数定义
| 参数名 | 类型 | 描述 | 约束 |
|-------|------|------|------|
| old_health | int | 变化前生命值 | >= 0 |
| new_health | int | 变化后生命值 | >= 0 |

### 发射位置
- `Player.cs` → `TakeDamage()` 方法
- `Player.cs` → `Heal()` 方法

### 监听位置
- `UI/HealthBar.cs` → 更新显示
- `GameState.cs` → 检查死亡条件
- `Observability.cs` → 记录事件

### 测试用例 (GdUnit4)
\`\`\`gdscript
func test_player_health_changed_signal():
    var player = Player.new()
    var signal_emitted = false
    var old_val = 0
    var new_val = 0

    player.health_changed.connect(func(old_h, new_h):
        signal_emitted = true
        old_val = old_h
        new_val = new_h
    )

    player.health = 100
    player.take_damage(20)

    assert_that(signal_emitted).is_true()
    assert_that(old_val).is_equal(100)
    assert_that(new_val).is_equal(80)
\`\`\`
```

**C# Signal 定义**:

```csharp
// Player.cs
public partial class Player : Node2D
{
    [Signal]
    public delegate void HealthChangedEventHandler(int oldHealth, int newHealth);

    private int _health = 100;
    public int Health
    {
        get => _health;
        set
        {
            if (_health != value)
            {
                int oldHealth = _health;
                _health = value;
                EmitSignal(SignalName.HealthChanged, oldHealth, _health);
            }
        }
    }

    public void TakeDamage(int damage)
    {
        Health -= damage;
    }
}
```

**监听示例**:

```csharp
// HealthBar.cs
public partial class HealthBar : Control
{
    private Player _player;

    public override void _Ready()
    {
        _player = GetNode<Player>("/root/Player");
        _player.HealthChanged += OnPlayerHealthChanged;
    }

    private void OnPlayerHealthChanged(int oldHealth, int newHealth)
    {
        GD.Print($"Health: {oldHealth} → {newHealth}");
        UpdateDisplay(newHealth);
    }

    public override void _ExitTree()
    {
        if (_player != null)
        {
            _player.HealthChanged -= OnPlayerHealthChanged;
        }
    }
}
```

**契约检查工具**:

```python
# scripts/ci/check-signal-contracts.py

import re
from pathlib import Path

def scan_signal_definitions(cs_files):
    """扫描所有 [Signal] 定义"""
    signals = []
    for file in cs_files:
        content = file.read_text(encoding='utf-8')
        matches = re.findall(
            r'\[Signal\]\s+public\s+delegate\s+void\s+(\w+)EventHandler\((.*?)\);',
            content,
            re.DOTALL
        )
        for match in matches:
            signal_name = match[0]
            params = match[1].strip()
            signals.append({
                'name': signal_name,
                'params': params,
                'file': file
            })
    return signals

def check_contract_docs(signals, docs_dir):
    """检查每个 Signal 是否有契约文档"""
    missing = []
    for sig in signals:
        doc_file = docs_dir / f"signal-{sig['name']}.md"
        if not doc_file.exists():
            missing.append(sig)

    if missing:
        print("FAIL 以下 Signals 缺少契约文档：")
        for sig in missing:
            print(f"  - {sig['name']} (in {sig['file']})")
        return False

    print("[OK] 所有 Signals 均有契约文档")
    return True

if __name__ == '__main__':
    cs_files = Path('Game.Godot').rglob('*.cs')
    signals = scan_signal_definitions(cs_files)
    docs_dir = Path('docs/contracts/signals')

    success = check_contract_docs(signals, docs_dir)
    exit(0 if success else 1)
```

**迁移对照**:

| CloudEvents 概念 | Godot Signal 对应 | 说明 |
|-----------------|------------------|------|
| `type: "app.player.health.changed"` | `signal health_changed` | 使用 snake_case |
| `source: "player-service"` | Signal 发射节点路径 | `/root/Player` |
| `data: { oldHealth, newHealth }` | Signal 参数 | `(int, int)` |
| `id: "uuid"` | - | 不需要 ID（内存内通信） |
| `time: "ISO8601"` | - | 可选：自行传递 timestamp |

**保留的 CloudEvents 场景**:

对于需要跨进程/网络通信的事件（如上报到后端），仍使用 CloudEvents：

```csharp
// Observability.cs
public void LogGameEvent(string eventType, object data)
{
    var cloudEvent = new CloudEvent
    {
        Type = eventType,
        Source = new Uri("app://godotgame"),
        Data = JsonSerializer.Serialize(data),
        Time = DateTimeOffset.UtcNow
    };

    SentrySDK.CaptureMessage($"Game Event: {eventType}", cloudEvent);
}
```

---

## 现有 ADR 更新

### ADR-0003 更新: Sentry Godot SDK

**变更点**:

```diff
- 初始化位置: Electron Main Process
+ 初始化位置: Godot Autoload (Observability.cs 或 .cs)

- SDK: @sentry/electron
+ SDK: sentry-godot (GDNative 插件)

- 示例代码:
-   import * as Sentry from '@sentry/electron';
-   Sentry.init({ dsn: '...' });
+   # Autoload: Observability.cs
+   var sentry = preload("res://addons/sentry-godot/sentry.cs").new()
+   sentry.init({ "dsn": "..." })
```

### ADR-0005 更新: 质量门禁工具链

**变更点**:

```diff
- 类型检查: tsc --noEmit
+ 类型检查: dotnet build /warnaserror

- Lint: eslint
+ Lint: dotnet format analyzers (StyleCop + Roslyn)

- 单元测试: vitest
+ 单元测试: dotnet test (xUnit + coverlet)

- E2E: playwright
+ E2E: godot --headless + GdUnit4

- 重复检测: jscpd (支持 .ts/.tsx)
+ 重复检测: jscpd (支持 .cs/.gd)
```

### ADR-0006 更新: godot-sqlite 适配

**变更点**:

```diff
- 库: better-sqlite3 (Node.js)
+ 库: godot-sqlite (GDNative 插件)

- 初始化:
-   const db = require('better-sqlite3')('game.db');
+   var db = SQLite.new()
+   db.path = "user://game.db"
+   db.open_db()

- 查询:
-   const rows = db.prepare('SELECT * FROM users').all();
+   db.query("SELECT * FROM users")
+   var rows = db.query_result
```

### ADR-0015 更新: Godot 性能指标

**变更点**:

```diff
- 指标: FCP (First Contentful Paint, Lighthouse)
+ 指标: 主场景首次 _ready() 完成时间

- 指标: 场景切换时间 (Performance API)
+ 指标: SceneTree.change_scene_to_file() 耗时

- 采集方式: Playwright tracing
+ 采集方式: Godot Performance.get_monitor() + 自定义计时

- 预算: FCP ≤ 800ms (P95)
+ 预算: 主场景加载 ≤ 3s (P95, headless), ≤ 5s (硬上限)
```

---

## 实施检查清单

- [ ] ADR-0018 到 ADR-0022 草案已创建
- [ ] ADR-0003/0005/0006/0015 更新完成
- [ ] 所有新 ADR 经过团队评审
- [ ] ADR 状态更新为 Accepted
- [ ] Base 文档引用新 ADR（01/02/03/05 章）
- [ ] 迁移计划与 ADR 保持一致

---

## 下一步

完成本阶段后，继续：

➡️ [Phase-3-Project-Structure.md](Phase-3-Project-Structure.md) — Godot 项目结构设计
