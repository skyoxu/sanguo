# Phase 11: 场景集成测试（GdUnit4）

**阶段目标**: 建立完整的 Godot 场景集成测试框架，验证游戏场景、UI 交互和 Signal 系统的正确性

**工作量**: 8-10 人天  
**风险等级**: 中（GdUnit4 学习曲线，场景加载时序复杂）  
**依赖**: Phase 8（场景设计）、Phase 10（单元测试框架）  
**后续依赖**: Phase 12（E2E 测试）

---

## 11.1 场景集成测试框架设计

### 11.1.1 GdUnit4 集成

**安装 GdUnit4**：

```powershell
# scripts/install-gdunit4.ps1

param(
    [string]$ProjectRoot = "C:\buildgame\godotgame"
)

Write-Host "安装 GdUnit4..." -ForegroundColor Green

# 创建 addons 目录
$addonsPath = Join-Path $ProjectRoot "addons"
if (-not (Test-Path $addonsPath)) {
    New-Item -ItemType Directory -Path $addonsPath -Force | Out-Null
}

# 从 GitHub 克隆 GdUnit4
$gdunitPath = Join-Path $addonsPath "gdunit4"
if (-not (Test-Path $gdunitPath)) {
    Write-Host "克隆 GdUnit4 仓库..." -ForegroundColor Gray
    git clone https://github.com/MikeSchulze/gdUnit4.git $gdunitPath
} else {
    Write-Host "GdUnit4 已存在，跳过克隆" -ForegroundColor Gray
}

# 验证安装
$testPluginPath = Join-Path $gdunitPath "plugin.cfg"
if (Test-Path $testPluginPath) {
    Write-Host "PASS: GdUnit4 安装成功" -ForegroundColor Green
} else {
    Write-Host "FAIL: GdUnit4 安装失败" -ForegroundColor Red
    exit 1
}
```

**项目配置 (project.godot)**：

```ini
[addons]

gdunit4/enabled=true
gdunit4/test_timeout=5000
gdunit4/report_orphans=true
gdunit4/auto_load_runner=true
gdunit4/fail_orphans=false
```

### 11.1.2 GdUnit4 基础测试类

**基础测试工具类** (`Game.Godot/Tests/GdUnitTestBase.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Collections.Generic;
using System.Threading.Tasks;

/// <summary>
/// GdUnit4 集成测试的基类，提供常用工具方法
/// </summary>
public partial class GdUnitTestBase : Node
{
    protected Node2D CurrentScene { get; set; }
    protected Control CurrentUI { get; set; }
    
    /// <summary>
    /// 初始化测试场景
    /// </summary>
    protected async Task<T> LoadScene<T>(string scenePath) where T : Node
    {
        var scene = GD.Load<PackedScene>(scenePath);
        AssertThat(scene).IsNotNull().WithMessage($"场景未找到: {scenePath}");
        
        var instance = scene.Instantiate<T>();
        AddChild(instance);
        await Task.Delay(100); // 等待场景初始化
        
        return instance;
    }
    
    /// <summary>
    /// 模拟用户输入（按键）
    /// </summary>
    protected void SimulateKeyPress(Key key)
    {
        var inputEvent = InputEventKey.Create();
        inputEvent.Keycode = key;
        inputEvent.Pressed = true;
        Input.ParseInputEvent(inputEvent);
        
        // 模拟释放
        inputEvent.Pressed = false;
        Input.ParseInputEvent(inputEvent);
    }
    
    /// <summary>
    /// 模拟鼠标点击
    /// </summary>
    protected void SimulateMouseClick(Vector2 position)
    {
        var inputEvent = InputEventMouseButton.Create();
        inputEvent.Position = position;
        inputEvent.ButtonIndex = MouseButton.Left;
        inputEvent.Pressed = true;
        Input.ParseInputEvent(inputEvent);
        
        inputEvent.Pressed = false;
        Input.ParseInputEvent(inputEvent);
    }
    
    /// <summary>
    /// 等待信号发射
    /// </summary>
    protected async Task WaitForSignal(GodotObject source, StringName signal, int timeoutMs = 5000)
    {
        var signalAwaiter = ToSignal(source, signal);
        var task = (Task)signalAwaiter;
        
        var completedTask = await Task.WhenAny(
            task,
            Task.Delay(timeoutMs)
        );
        
        AssertThat(completedTask == task)
            .WithMessage($"信号未在 {timeoutMs}ms 内发射: {signal}");
    }
    
    /// <summary>
    /// 获取测试数据目录
    /// </summary>
    protected string GetTestDataPath(string fileName) 
        => $"res://Game.Godot/Tests/TestData/{fileName}";
}
```

---

## 11.2 主场景测试 (MainScene)

### 11.2.1 MainScene.cs 测试

**测试文件** (`Game.Godot/Tests/Scenes/MainSceneTest.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Threading.Tasks;

/// <summary>
/// MainScene 集成测试
/// 测试场景初始化、菜单交互、场景转换
/// </summary>
[TestClass]
public partial class MainSceneTest : GdUnitTestBase
{
    private MainScene _mainScene;
    
    [Before]
    public async Task Setup()
    {
        _mainScene = await LoadScene<MainScene>("res://Game.Godot/Scenes/MainScene.tscn");
    }
    
    [After]
    public void Cleanup()
    {
        if (_mainScene != null && !_mainScene.IsQueuedForDeletion())
        {
            _mainScene.QueueFree();
        }
    }
    
    [Test]
    public void MainScene_OnReady_ShouldInitializeUI()
    {
        // Arrange
        AssertThat(_mainScene).IsNotNull();
        
        // Act
        var mainMenu = _mainScene.GetNode<VBoxContainer>("UI/MainMenu");
        var playButton = mainMenu.GetNode<Button>("PlayButton");
        var settingsButton = mainMenu.GetNode<Button>("SettingsButton");
        
        // Assert
        AssertThat(mainMenu).IsVisible();
        AssertThat(playButton).IsVisible();
        AssertThat(settingsButton).IsVisible();
    }
    
    [Test]
    public void PlayButton_OnPressed_ShouldEmitGameStartSignal()
    {
        // Arrange
        var playButton = _mainScene.GetNode<Button>("UI/MainMenu/PlayButton");
        var signalEmitted = false;
        
        _mainScene.Connect(
            SignalName.GameStartRequested,
            Callable.From(() => signalEmitted = true)
        );
        
        // Act
        playButton.EmitSignal(Button.SignalName.Pressed);
        
        // Assert
        AssertThat(signalEmitted).IsTrue()
            .WithMessage("GameStartRequested 信号应被发射");
    }
    
    [Test]
    public void SettingsButton_OnPressed_ShouldShowSettingsPanel()
    {
        // Arrange
        var settingsButton = _mainScene.GetNode<Button>("UI/MainMenu/SettingsButton");
        var settingsPanel = _mainScene.GetNode<PanelContainer>("UI/SettingsPanel");
        
        // Act
        settingsButton.EmitSignal(Button.SignalName.Pressed);
        
        // Assert
        AssertThat(settingsPanel).IsVisible()
            .WithMessage("设置面板应被显示");
    }
    
    [Test]
    public async Task BackButton_OnPressed_ShouldHideSettingsPanel()
    {
        // Arrange
        var settingsButton = _mainScene.GetNode<Button>("UI/MainMenu/SettingsButton");
        var settingsPanel = _mainScene.GetNode<PanelContainer>("UI/SettingsPanel");
        var backButton = settingsPanel.GetNode<Button>("BackButton");
        
        // 打开设置面板
        settingsButton.EmitSignal(Button.SignalName.Pressed);
        await Task.Delay(100);
        
        // Act
        backButton.EmitSignal(Button.SignalName.Pressed);
        await Task.Delay(100);
        
        // Assert
        AssertThat(settingsPanel).IsNotVisible()
            .WithMessage("设置面板应被隐藏");
    }
}
```

### 11.2.2 MainScene.cs 实现参考

**更新 MainScene** (`Game.Godot/Scenes/MainScene.cs`):

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

---

## 11.3 游戏场景测试 (GameScene)

### 11.3.1 GameScene 集成测试

**测试文件** (`Game.Godot/Tests/Scenes/GameSceneTest.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Threading.Tasks;

/// <summary>
/// GameScene 集成测试
/// 测试游戏初始化、角色生成、事件系统集成
/// </summary>
[TestClass]
public partial class GameSceneTest : GdUnitTestBase
{
    private GameScene _gameScene;
    
    [Before]
    public async Task Setup()
    {
        _gameScene = await LoadScene<GameScene>("res://Game.Godot/Scenes/GameScene.tscn");
    }
    
    [After]
    public void Cleanup()
    {
        if (_gameScene != null && !_gameScene.IsQueuedForDeletion())
        {
            _gameScene.QueueFree();
        }
    }
    
    [Test]
    public void GameScene_OnReady_ShouldCreatePlayer()
    {
        // Arrange & Act
        var playerNode = _gameScene.GetNode("Player");
        
        // Assert
        AssertThat(playerNode).IsNotNull()
            .WithMessage("游戏场景应包含 Player 节点");
    }
    
    [Test]
    public void GameScene_OnReady_ShouldInitializeGameState()
    {
        // Arrange & Act
        var gameStateManager = _gameScene.GetNode<GameStateManager>("GameStateManager");
        
        // Assert
        AssertThat(gameStateManager).IsNotNull();
        AssertThat(gameStateManager.IsInitialized).IsTrue()
            .WithMessage("游戏状态管理器应被初始化");
    }
    
    [Test]
    public async Task PlayerInput_Move_ShouldUpdatePlayerPosition()
    {
        // Arrange
        var player = _gameScene.GetNode<CharacterBody2D>("Player");
        var initialPosition = player.Position;
        
        // Act
        SimulateKeyPress(Key.Right);
        await Task.Delay(100); // 等待物理帧
        
        // Assert
        AssertThat(player.Position.X).IsGreater(initialPosition.X)
            .WithMessage("玩家应向右移动");
    }
    
    [Test]
    public void EnemySpawner_ShouldSpawnEnemies()
    {
        // Arrange
        var spawner = _gameScene.GetNode<EnemySpawner>("EnemySpawner");
        var enemyCount = _gameScene.GetTree().GetNodeCount() - 1; // 排除场景节点本身
        
        // Act
        spawner.SpawnWave(3);
        
        // Assert
        var newEnemyCount = _gameScene.GetTree().GetNodeCount() - 1;
        AssertThat(newEnemyCount).IsGreater(enemyCount)
            .WithMessage("敌人生成器应生成敌人");
    }
}
```

### 11.3.2 GameScene.cs 实现参考

**GameScene 实现** (`Game.Godot/Scenes/GameScene.cs`):

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

---

## 11.4 UI 组件测试

### 11.4.1 按钮组件测试

**测试文件** (`Game.Godot/Tests/UI/CustomButtonTest.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Threading.Tasks;

/// <summary>
/// 自定义按钮组件测试
/// 测试按钮状态、视觉反馈、点击事件
/// </summary>
[TestClass]
public partial class CustomButtonTest : GdUnitTestBase
{
    private CustomButton _button;
    
    [Before]
    public async Task Setup()
    {
        _button = new CustomButton();
        AddChild(_button);
        _button.Size = new Vector2(100, 50);
    }
    
    [After]
    public void Cleanup()
    {
        _button?.QueueFree();
    }
    
    [Test]
    public void Button_OnMouseEnter_ShouldShowHoverState()
    {
        // Arrange
        var originalModulate = _button.Modulate;
        
        // Act
        _button.GetMouseFilter(); // 确保按钮可接收输入
        var mouseEnterEvent = InputEventMouseMotion.Create();
        mouseEnterEvent.Position = _button.GetGlobalRect().GetCenter();
        Input.ParseInputEvent(mouseEnterEvent);
        _button.EmitSignal(Control.SignalName.MouseEntered);
        
        // Assert
        // 悬停时通常会改变颜色或缩放
        AssertThat(_button.Modulate).IsNotEqual(originalModulate)
            .WithMessage("按钮悬停时应改变外观");
    }
    
    [Test]
    public void Button_OnPressed_ShouldEmitPressedSignal()
    {
        // Arrange
        var pressed = false;
        _button.Pressed += () => pressed = true;
        
        // Act
        _button.EmitSignal(Button.SignalName.Pressed);
        
        // Assert
        AssertThat(pressed).IsTrue()
            .WithMessage("按钮应发射 Pressed 信号");
    }
    
    [Test]
    public void Button_Disabled_ShouldNotRespond()
    {
        // Arrange
        _button.Disabled = true;
        var clicked = false;
        _button.Pressed += () => clicked = true;
        
        // Act
        _button.EmitSignal(Button.SignalName.Pressed);
        
        // Assert
        AssertThat(clicked).IsFalse()
            .WithMessage("禁用的按钮不应响应点击");
    }
}
```

### 11.4.2 自定义按钮实现

**CustomButton 实现** (`Game.Godot/UI/CustomButton.cs`):

```csharp
using Godot;

/// <summary>
/// 自定义按钮，支持悬停、按压等视觉反馈
/// </summary>
public partial class CustomButton : Button
{
    private Color _normalColor = Colors.White;
    private Color _hoverColor = new Color(1.2f, 1.2f, 1.2f);
    private Color _pressedColor = new Color(0.8f, 0.8f, 0.8f);
    
    public override void _Ready()
    {
        MouseEntered += OnMouseEntered;
        MouseExited += OnMouseExited;
        Pressed += OnPressed;
        ReleasesFocus = true;
    }
    
    private void OnMouseEntered()
    {
        if (!Disabled)
        {
            Modulate = _hoverColor;
        }
    }
    
    private void OnMouseExited()
    {
        Modulate = _normalColor;
    }
    
    private void OnPressed()
    {
        if (!Disabled)
        {
            Modulate = _pressedColor;
            var tween = CreateTween();
            tween.TweenProperty(this, "modulate", _normalColor, 0.2f);
        }
    }
}
```

---

## 11.5 Signal 系统集成测试

### 11.5.1 Signal 链式调用测试

**测试文件** (`Game.Godot/Tests/Systems/SignalBusTest.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Collections.Generic;
using System.Threading.Tasks;

/// <summary>
/// Signal 总线集成测试
/// 测试事件的发射、监听、传播
/// </summary>
[TestClass]
public partial class SignalBusTest : GdUnitTestBase
{
    private SignalBus _signalBus;
    
    [Before]
    public void Setup()
    {
        _signalBus = new SignalBus();
        AddChild(_signalBus);
    }
    
    [After]
    public void Cleanup()
    {
        _signalBus?.QueueFree();
    }
    
    [Test]
    public void SignalBus_OnEmitSignal_ShouldNotifyAllListeners()
    {
        // Arrange
        var receivedEvents = new List<string>();
        
        _signalBus.Subscribe("player.health.changed", (Variant data) =>
        {
            receivedEvents.Add($"listener1: {data}");
        });
        
        _signalBus.Subscribe("player.health.changed", (Variant data) =>
        {
            receivedEvents.Add($"listener2: {data}");
        });
        
        // Act
        _signalBus.Emit("player.health.changed", 50);
        
        // Assert
        AssertThat(receivedEvents.Count).IsEqual(2)
            .WithMessage("所有监听者应收到信号");
        AssertThat(receivedEvents[0]).Contains("listener1");
        AssertThat(receivedEvents[1]).Contains("listener2");
    }
    
    [Test]
    public void SignalBus_OnUnsubscribe_ShouldNotNotifyListener()
    {
        // Arrange
        var receivedEvents = new List<string>();
        var callback = (Variant data) => receivedEvents.Add("received");
        
        _signalBus.Subscribe("test.signal", callback);
        _signalBus.Unsubscribe("test.signal", callback);
        
        // Act
        _signalBus.Emit("test.signal", null);
        
        // Assert
        AssertThat(receivedEvents.Count).IsEqual(0)
            .WithMessage("取消订阅后不应收到信号");
    }
    
    [Test]
    public async Task SignalBus_OnEmitWithDelay_ShouldWorkCorrectly()
    {
        // Arrange
        var signalReceived = false;
        
        _signalBus.Subscribe("delayed.signal", (Variant data) =>
        {
            signalReceived = true;
        });
        
        // Act
        _signalBus.EmitAsync("delayed.signal", null, 0.1f);
        await Task.Delay(200);
        
        // Assert
        AssertThat(signalReceived).IsTrue()
            .WithMessage("延迟信号应被发射");
    }
}
```

### 11.5.2 SignalBus 实现

**SignalBus 实现** (`Game.Godot/Systems/SignalBus.cs`):

```csharp
using Godot;
using System;
using System.Collections.Generic;

/// <summary>
/// 全局事件总线，用于场景间通信
/// 使用发布-订阅模式
/// </summary>
public partial class SignalBus : Node
{
    private Dictionary<string, List<Action<Variant>>> _subscribers = new();
    
    /// <summary>
    /// 订阅事件
    /// </summary>
    public void Subscribe(string signalName, Action<Variant> callback)
    {
        if (!_subscribers.ContainsKey(signalName))
        {
            _subscribers[signalName] = new List<Action<Variant>>();
        }
        _subscribers[signalName].Add(callback);
    }
    
    /// <summary>
    /// 取消订阅
    /// </summary>
    public void Unsubscribe(string signalName, Action<Variant> callback)
    {
        if (_subscribers.ContainsKey(signalName))
        {
            _subscribers[signalName].Remove(callback);
        }
    }
    
    /// <summary>
    /// 发射事件（同步）
    /// </summary>
    public void Emit(string signalName, Variant data)
    {
        if (_subscribers.ContainsKey(signalName))
        {
            foreach (var callback in _subscribers[signalName])
            {
                try
                {
                    callback?.Invoke(data);
                }
                catch (Exception ex)
                {
                    GD.PrintErr($"Signal handler error for {signalName}: {ex.Message}");
                }
            }
        }
    }
    
    /// <summary>
    /// 发射事件（异步延迟）
    /// </summary>
    public async void EmitAsync(string signalName, Variant data, float delaySeconds)
    {
        await Task.Delay((int)(delaySeconds * 1000));
        Emit(signalName, data);
    }
    
    /// <summary>
    /// 清空所有订阅
    /// </summary>
    public void Clear()
    {
        _subscribers.Clear();
    }
}
```

---

## 11.6 完整集成测试场景

### 11.6.1 端到端场景测试

**测试文件** (`Game.Godot/Tests/Scenes/FullGameFlowTest.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Threading.Tasks;

/// <summary>
/// 完整游戏流程集成测试
/// 从主菜单 → 游戏开始 → 击杀敌人 → 游戏结束
/// </summary>
[TestClass]
public partial class FullGameFlowTest : GdUnitTestBase
{
    private MainScene _mainScene;
    private GameScene _gameScene;
    
    [Before]
    public async Task Setup()
    {
        _mainScene = await LoadScene<MainScene>("res://Game.Godot/Scenes/MainScene.tscn");
    }
    
    [After]
    public void Cleanup()
    {
        _mainScene?.QueueFree();
        _gameScene?.QueueFree();
    }
    
    [Test]
    public async Task FullFlow_MainMenuToGame_ShouldLoadGameScene()
    {
        // Arrange
        var playButton = _mainScene.GetNode<Button>("UI/MainMenu/PlayButton");
        var gameStarted = false;
        
        _mainScene.Connect(
            SignalName.GameStartRequested,
            Callable.From(() => gameStarted = true)
        );
        
        // Act
        playButton.EmitSignal(Button.SignalName.Pressed);
        await Task.Delay(1000); // 等待场景加载
        
        // Assert
        AssertThat(gameStarted).IsTrue()
            .WithMessage("游戏应该已启动");
    }
    
    [Test]
    public async Task GameFlow_PlayerAttacksEnemy_ShouldReduceHealth()
    {
        // Arrange
        _gameScene = await LoadScene<GameScene>("res://Game.Godot/Scenes/GameScene.tscn");
        var player = _gameScene.GetNode<Player>("Player");
        var enemy = _gameScene.GetNode<Enemy>("Enemy");
        var initialHealth = enemy.Health.Current;
        
        // Act
        player.Attack(enemy);
        await Task.Delay(200); // 等待攻击动画
        
        // Assert
        AssertThat(enemy.Health.Current).IsLess(initialHealth)
            .WithMessage("敌人血量应该减少");
    }
}
```

---

## 11.7 测试数据和 Fixtures

### 11.7.1 测试 Fixture 工厂

**Fixture 工厂** (`Game.Godot/Tests/Fixtures/GameFixtures.cs`):

```csharp
using System;

/// <summary>
/// 游戏数据测试 Fixtures
/// 提供常用的测试数据对象
/// </summary>
public static class GameFixtures
{
    /// <summary>
    /// 创建测试用玩家
    /// </summary>
    public static Player CreateTestPlayer(
        string name = "TestPlayer",
        int health = 100,
        int level = 1)
    {
        return new Player
        {
            Name = name,
            Health = new Health(health),
            Level = level,
            Experience = 0
        };
    }
    
    /// <summary>
    /// 创建测试用敌人
    /// </summary>
    public static Enemy CreateTestEnemy(
        string name = "TestEnemy",
        int health = 30,
        int damage = 5)
    {
        return new Enemy
        {
            Name = name,
            Health = new Health(health),
            Damage = damage,
            RewardExp = 10
        };
    }
    
    /// <summary>
    /// 创建测试用游戏场景配置
    /// </summary>
    public static GameConfig CreateTestGameConfig()
    {
        return new GameConfig
        {
            MaxWaves = 10,
            WaveDelay = 2.0f,
            EnemiesPerWave = 5,
            DifficultyMultiplier = 1.2f
        };
    }
}
```

### 11.7.2 测试场景数据

**Test Scenes TscnData** 目录结构：

```
Game.Godot/Tests/
├── TestScenes/
│   ├── MinimalGameScene.tscn    # 最小化游戏场景
│   ├── UITestScene.tscn         # UI 组件测试场景
│   └── SignalTestScene.tscn     # Signal 系统测试场景
├── TestData/
│   ├── player.json              # 玩家数据样本
│   ├── enemies.json             # 敌人数据样本
│   └── game_config.json         # 游戏配置样本
└── Fixtures/
    └── GameFixtures.cs
```

---

## 11.8 测试执行和报告

### 11.8.1 运行 GdUnit4 测试

**PowerShell 测试运行脚本** (`scripts/run-gdunit4-tests.ps1`):

```powershell
param(
    [string]$ProjectRoot = "C:\buildgame\godotgame",
    [switch]$OpenReport = $false,
    [string]$TestFilter = "*",
    [switch]$Headless = $false
)

Write-Host "运行 GdUnit4 场景集成测试..." -ForegroundColor Green

$godotExe = "godot"
$projectPath = $ProjectRoot

# 构建 Godot 命令
$godotArgs = @(
    "--path", $projectPath,
    "-s", "addons/gdunit4/bin/gdunitcli.cs",
    "-r", "$TestFilter.cs"
)

if ($Headless) {
    $godotArgs += "--headless"
}

# 运行测试
Write-Host "执行命令: $godotExe $($godotArgs -join ' ')" -ForegroundColor Gray
& $godotExe $godotArgs

$lastExitCode = $LASTEXITCODE

if ($lastExitCode -eq 0) {
    Write-Host "PASS: GdUnit4 测试通过" -ForegroundColor Green
} else {
    Write-Host "FAIL: GdUnit4 测试失败 (exit code: $lastExitCode)" -ForegroundColor Red
}

# 打开报告（如果指定）
if ($OpenReport) {
    $reportPath = Join-Path $projectPath "addons/gdunit4/reports/report.html"
    if (Test-Path $reportPath) {
        Invoke-Item $reportPath
    }
}

exit $lastExitCode
```

### 11.8.2 CI 集成

**GitHub Actions 工作流** (`.github/workflows/gdunit4-tests.yml`):

```yaml
name: GdUnit4 Scene Integration Tests

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'Game.Godot/**'
      - '.github/workflows/gdunit4-tests.yml'
  pull_request:
    branches: [ main, develop ]
    paths:
      - 'Game.Godot/**'

jobs:
  gdunit4-tests:
    runs-on: windows-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: 安装 Godot 4.5
        run: |
          # 假设 Godot 已通过其他方式安装或可从缓存获取
          $godotPath = "C:\Program Files\Godot\bin\godot.exe"
          if (Test-Path $godotPath) {
            Write-Host "Godot 已安装"
          } else {
            Write-Host "需要安装 Godot 4.5"
          }
      
      - name: 运行 GdUnit4 测试
        run: |
          .\scripts\run-gdunit4-tests.ps1 `
            -ProjectRoot ${{ github.workspace }} `
            -Headless
      
      - name: 上传测试报告
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: gdunit4-reports
          path: addons/gdunit4/reports/
      
      - name: 检查测试结果
        run: |
          if ($LASTEXITCODE -ne 0) {
            exit 1
          }
```

---

## 11.9 完成清单

- [ ] GdUnit4 安装并配置
- [ ] 编写 MainScene 集成测试（≥4 个测试用例）
- [ ] 编写 GameScene 集成测试（≥5 个测试用例）
- [ ] 编写 UI 组件测试（CustomButton 等）
- [ ] 编写 Signal 系统集成测试（≥4 个测试用例）
- [ ] 编写完整流程集成测试（端到端）
- [ ] 创建测试 Fixtures 和测试数据
- [ ] 验证所有测试通过（100% 通过率）
- [ ] 生成测试覆盖率报告（≥80%）
- [ ] 集成到 CI 流程
- [ ] 更新文档和测试运行指南

**完成标志**:

```bash
# 所有 GdUnit4 测试通过
.\scripts\run-gdunit4-tests.ps1 -ProjectRoot . -Headless
# 输出：PASS GdUnit4 测试通过

# 集成测试覆盖率达到 80%+
# 报告位置：addons/gdunit4/reports/coverage.html
```

---

## 11.10 风险和缓解

| 风险 | 影响 | 缓解策略 |
|------|------|--------|
| 场景加载延迟 | 测试超时失败 | 设置合理超时（5000ms），预加载公共资源 |
| Signal 时序问题 | 竞态条件 | 使用 `await Task.Delay()` 同步，使用 `WaitForSignal()` |
| 测试隔离不足 | 交叉污染 | 每个测试 `[Before]`/`[After]` 清理资源 |
| Godot 编辑器依赖 | 无法 CI 运行 | 使用 `--headless` 模式 |
| GdUnit4 版本冲突 | 插件加载失败 | 锁定 GdUnit4 版本，定期更新兼容性检查 |

---

## 11.11 后续 Phase

**Phase 12: E2E 测试** (Godot Headless + 自动化)
- 从主菜单完整游戏流程自动化测试
- 性能基准测试
- 压力测试（多波敌人）


## Python 等效脚本示例（GdUnit4）

以下示例提供在 Windows 上使用 Python 执行 GdUnit4 场景测试的最小可用脚本，作为 PowerShell 包装脚本的替代方案。

```python
# scripts/run_gdunit4_tests.py
import subprocess

def main() -> int:
    cmd = [
        'godot', '--headless', '--path', 'Game.Godot',
        '--script', 'res://addons/gdunit4/runners/GdUnit4CmdLnRunner.cs',
        '--gdunit-headless=yes', '--repeat=1'
    ]
    print('>', ' '.join(cmd))
    subprocess.check_call(cmd)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
```

说明：
- 报告默认输出到 `addons/gdunit4/reports/`，可在 CI 工件中收集。
- 如需将报告复制到仓库 `logs/ci/YYYY-MM-DD/`，参考 Phase-13 文档中的 Python 收集片段。


> 参考 Runner 接入指南：见 docs/migration/gdunit4-csharp-runner-integration.md。


---

## 健壮性注入测试（建议）

- 在 C# 测试中注入异常路径（场景加载失败/节点缺失/信号未触发）
- 对“失败一次自动重试；仍失败则降级/返回主菜单”的流程进行断言
- 将异常注入的结果写入报告，作为“场景测试通过率=100%”的前置门禁依据（与 Phase-13 聚合一致）
