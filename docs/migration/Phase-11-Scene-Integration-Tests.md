# Phase 11: 鍦烘櫙闆嗘垚娴嬭瘯锛圙dUnit4锛?

**闃舵鐩爣**: 寤虹珛瀹屾暣鐨?Godot 鍦烘櫙闆嗘垚娴嬭瘯妗嗘灦锛岄獙璇佹父鎴忓満鏅€乁I 浜や簰鍜?Signal 绯荤粺鐨勬纭€?

**宸ヤ綔閲?*: 8-10 浜哄ぉ  
**椋庨櫓绛夌骇**: 涓紙GdUnit4 瀛︿範鏇茬嚎锛屽満鏅姞杞芥椂搴忓鏉傦級  
**渚濊禆**: Phase 8锛堝満鏅璁★級銆丳hase 10锛堝崟鍏冩祴璇曟鏋讹級  
**鍚庣画渚濊禆**: Phase 12锛圗2E 娴嬭瘯锛?

---

## 11.1 鍦烘櫙闆嗘垚娴嬭瘯妗嗘灦璁捐

### 11.1.1 GdUnit4 闆嗘垚

**瀹夎 GdUnit4**锛?

```powershell
# scripts/install-gdunit4.ps1

param(
    [string]$ProjectRoot = "C:\buildgame\sanguo"
)

Write-Host "瀹夎 GdUnit4..." -ForegroundColor Green

# 鍒涘缓 addons 鐩綍
$addonsPath = Join-Path $ProjectRoot "addons"
if (-not (Test-Path $addonsPath)) {
    New-Item -ItemType Directory -Path $addonsPath -Force | Out-Null
}

# 浠?GitHub 鍏嬮殕 GdUnit4
$gdunitPath = Join-Path $addonsPath "gdunit4"
if (-not (Test-Path $gdunitPath)) {
    Write-Host "鍏嬮殕 GdUnit4 浠撳簱..." -ForegroundColor Gray
    git clone https://github.com/MikeSchulze/gdUnit4.git $gdunitPath
} else {
    Write-Host "GdUnit4 宸插瓨鍦紝璺宠繃鍏嬮殕" -ForegroundColor Gray
}

# 楠岃瘉瀹夎
$testPluginPath = Join-Path $gdunitPath "plugin.cfg"
if (Test-Path $testPluginPath) {
    Write-Host "PASS: GdUnit4 瀹夎鎴愬姛" -ForegroundColor Green
} else {
    Write-Host "FAIL: GdUnit4 瀹夎澶辫触" -ForegroundColor Red
    exit 1
}
```

**椤圭洰閰嶇疆 (project.godot)**锛?

```ini
[addons]

gdunit4/enabled=true
gdunit4/test_timeout=5000
gdunit4/report_orphans=true
gdunit4/auto_load_runner=true
gdunit4/fail_orphans=false
```

### 11.1.2 GdUnit4 鍩虹娴嬭瘯绫?

**鍩虹娴嬭瘯宸ュ叿绫?* (`Game.Godot/Tests/GdUnitTestBase.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Collections.Generic;
using System.Threading.Tasks;

/// <summary>
/// GdUnit4 闆嗘垚娴嬭瘯鐨勫熀绫伙紝鎻愪緵甯哥敤宸ュ叿鏂规硶
/// </summary>
public partial class GdUnitTestBase : Node
{
    protected Node2D CurrentScene { get; set; }
    protected Control CurrentUI { get; set; }
    
    /// <summary>
    /// 鍒濆鍖栨祴璇曞満鏅?
    /// </summary>
    protected async Task<T> LoadScene<T>(string scenePath) where T : Node
    {
        var scene = GD.Load<PackedScene>(scenePath);
        AssertThat(scene).IsNotNull().WithMessage($"鍦烘櫙鏈壘鍒? {scenePath}");
        
        var instance = scene.Instantiate<T>();
        AddChild(instance);
        await Task.Delay(100); // 绛夊緟鍦烘櫙鍒濆鍖?
        
        return instance;
    }
    
    /// <summary>
    /// 妯℃嫙鐢ㄦ埛杈撳叆锛堟寜閿級
    /// </summary>
    protected void SimulateKeyPress(Key key)
    {
        var inputEvent = InputEventKey.Create();
        inputEvent.Keycode = key;
        inputEvent.Pressed = true;
        Input.ParseInputEvent(inputEvent);
        
        // 妯℃嫙閲婃斁
        inputEvent.Pressed = false;
        Input.ParseInputEvent(inputEvent);
    }
    
    /// <summary>
    /// 妯℃嫙榧犳爣鐐瑰嚮
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
    /// 绛夊緟淇″彿鍙戝皠
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
            .WithMessage($"淇″彿鏈湪 {timeoutMs}ms 鍐呭彂灏? {signal}");
    }
    
    /// <summary>
    /// 鑾峰彇娴嬭瘯鏁版嵁鐩綍
    /// </summary>
    protected string GetTestDataPath(string fileName) 
        => $"res://Game.Godot/Tests/TestData/{fileName}";
}
```

---

## 11.2 涓诲満鏅祴璇?(MainScene)

### 11.2.1 MainScene.cs 娴嬭瘯

**娴嬭瘯鏂囦欢** (`Game.Godot/Tests/Scenes/MainSceneTest.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Threading.Tasks;

/// <summary>
/// MainScene 闆嗘垚娴嬭瘯
/// 娴嬭瘯鍦烘櫙鍒濆鍖栥€佽彍鍗曚氦浜掋€佸満鏅浆鎹?
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
            .WithMessage("GameStartRequested 淇″彿搴旇鍙戝皠");
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
            .WithMessage("璁剧疆闈㈡澘搴旇鏄剧ず");
    }
    
    [Test]
    public async Task BackButton_OnPressed_ShouldHideSettingsPanel()
    {
        // Arrange
        var settingsButton = _mainScene.GetNode<Button>("UI/MainMenu/SettingsButton");
        var settingsPanel = _mainScene.GetNode<PanelContainer>("UI/SettingsPanel");
        var backButton = settingsPanel.GetNode<Button>("BackButton");
        
        // 鎵撳紑璁剧疆闈㈡澘
        settingsButton.EmitSignal(Button.SignalName.Pressed);
        await Task.Delay(100);
        
        // Act
        backButton.EmitSignal(Button.SignalName.Pressed);
        await Task.Delay(100);
        
        // Assert
        AssertThat(settingsPanel).IsNotVisible()
            .WithMessage("璁剧疆闈㈡澘搴旇闅愯棌");
    }
}
```

### 11.2.2 MainScene.cs 瀹炵幇鍙傝€?

**鏇存柊 MainScene** (`Game.Godot/Scenes/MainScene.cs`):

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

## 11.3 娓告垙鍦烘櫙娴嬭瘯 (GameScene)

### 11.3.1 GameScene 闆嗘垚娴嬭瘯

**娴嬭瘯鏂囦欢** (`Game.Godot/Tests/Scenes/GameSceneTest.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Threading.Tasks;

/// <summary>
/// GameScene 闆嗘垚娴嬭瘯
/// 娴嬭瘯娓告垙鍒濆鍖栥€佽鑹茬敓鎴愩€佷簨浠剁郴缁熼泦鎴?
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
            .WithMessage("娓告垙鍦烘櫙搴斿寘鍚?Player 鑺傜偣");
    }
    
    [Test]
    public void GameScene_OnReady_ShouldInitializeGameState()
    {
        // Arrange & Act
        var gameStateManager = _gameScene.GetNode<GameStateManager>("GameStateManager");
        
        // Assert
        AssertThat(gameStateManager).IsNotNull();
        AssertThat(gameStateManager.IsInitialized).IsTrue()
            .WithMessage("娓告垙鐘舵€佺鐞嗗櫒搴旇鍒濆鍖?);
    }
    
    [Test]
    public async Task PlayerInput_Move_ShouldUpdatePlayerPosition()
    {
        // Arrange
        var player = _gameScene.GetNode<CharacterBody2D>("Player");
        var initialPosition = player.Position;
        
        // Act
        SimulateKeyPress(Key.Right);
        await Task.Delay(100); // 绛夊緟鐗╃悊甯?
        
        // Assert
        AssertThat(player.Position.X).IsGreater(initialPosition.X)
            .WithMessage("鐜╁搴斿悜鍙崇Щ鍔?);
    }
    
    [Test]
    public void EnemySpawner_ShouldSpawnEnemies()
    {
        // Arrange
        var spawner = _gameScene.GetNode<EnemySpawner>("EnemySpawner");
        var enemyCount = _gameScene.GetTree().GetNodeCount() - 1; // 鎺掗櫎鍦烘櫙鑺傜偣鏈韩
        
        // Act
        spawner.SpawnWave(3);
        
        // Assert
        var newEnemyCount = _gameScene.GetTree().GetNodeCount() - 1;
        AssertThat(newEnemyCount).IsGreater(enemyCount)
            .WithMessage("鏁屼汉鐢熸垚鍣ㄥ簲鐢熸垚鏁屼汉");
    }
}
```

### 11.3.2 GameScene.cs 瀹炵幇鍙傝€?

**GameScene 瀹炵幇** (`Game.Godot/Scenes/GameScene.cs`):

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

## 11.4 UI 缁勪欢娴嬭瘯

### 11.4.1 鎸夐挳缁勪欢娴嬭瘯

**娴嬭瘯鏂囦欢** (`Game.Godot/Tests/UI/CustomButtonTest.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Threading.Tasks;

/// <summary>
/// 鑷畾涔夋寜閽粍浠舵祴璇?
/// 娴嬭瘯鎸夐挳鐘舵€併€佽瑙夊弽棣堛€佺偣鍑讳簨浠?
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
        _button.GetMouseFilter(); // 纭繚鎸夐挳鍙帴鏀惰緭鍏?
        var mouseEnterEvent = InputEventMouseMotion.Create();
        mouseEnterEvent.Position = _button.GetGlobalRect().GetCenter();
        Input.ParseInputEvent(mouseEnterEvent);
        _button.EmitSignal(Control.SignalName.MouseEntered);
        
        // Assert
        // 鎮仠鏃堕€氬父浼氭敼鍙橀鑹叉垨缂╂斁
        AssertThat(_button.Modulate).IsNotEqual(originalModulate)
            .WithMessage("鎸夐挳鎮仠鏃跺簲鏀瑰彉澶栬");
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
            .WithMessage("鎸夐挳搴斿彂灏?Pressed 淇″彿");
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
            .WithMessage("绂佺敤鐨勬寜閽笉搴斿搷搴旂偣鍑?);
    }
}
```

### 11.4.2 鑷畾涔夋寜閽疄鐜?

**CustomButton 瀹炵幇** (`Game.Godot/UI/CustomButton.cs`):

```csharp
using Godot;

/// <summary>
/// 鑷畾涔夋寜閽紝鏀寔鎮仠銆佹寜鍘嬬瓑瑙嗚鍙嶉
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

## 11.5 Signal 绯荤粺闆嗘垚娴嬭瘯

### 11.5.1 Signal 閾惧紡璋冪敤娴嬭瘯

**娴嬭瘯鏂囦欢** (`Game.Godot/Tests/Systems/SignalBusTest.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Collections.Generic;
using System.Threading.Tasks;

/// <summary>
/// Signal 鎬荤嚎闆嗘垚娴嬭瘯
/// 娴嬭瘯浜嬩欢鐨勫彂灏勩€佺洃鍚€佷紶鎾?
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
            .WithMessage("鎵€鏈夌洃鍚€呭簲鏀跺埌淇″彿");
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
            .WithMessage("鍙栨秷璁㈤槄鍚庝笉搴旀敹鍒颁俊鍙?);
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
            .WithMessage("寤惰繜淇″彿搴旇鍙戝皠");
    }
}
```

### 11.5.2 SignalBus 瀹炵幇

**SignalBus 瀹炵幇** (`Game.Godot/Systems/SignalBus.cs`):

```csharp
using Godot;
using System;
using System.Collections.Generic;

/// <summary>
/// 鍏ㄥ眬浜嬩欢鎬荤嚎锛岀敤浜庡満鏅棿閫氫俊
/// 浣跨敤鍙戝竷-璁㈤槄妯″紡
/// </summary>
public partial class SignalBus : Node
{
    private Dictionary<string, List<Action<Variant>>> _subscribers = new();
    
    /// <summary>
    /// 璁㈤槄浜嬩欢
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
    /// 鍙栨秷璁㈤槄
    /// </summary>
    public void Unsubscribe(string signalName, Action<Variant> callback)
    {
        if (_subscribers.ContainsKey(signalName))
        {
            _subscribers[signalName].Remove(callback);
        }
    }
    
    /// <summary>
    /// 鍙戝皠浜嬩欢锛堝悓姝ワ級
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
    /// 鍙戝皠浜嬩欢锛堝紓姝ュ欢杩燂級
    /// </summary>
    public async void EmitAsync(string signalName, Variant data, float delaySeconds)
    {
        await Task.Delay((int)(delaySeconds * 1000));
        Emit(signalName, data);
    }
    
    /// <summary>
    /// 娓呯┖鎵€鏈夎闃?
    /// </summary>
    public void Clear()
    {
        _subscribers.Clear();
    }
}
```

---

## 11.6 瀹屾暣闆嗘垚娴嬭瘯鍦烘櫙

### 11.6.1 绔埌绔満鏅祴璇?

**娴嬭瘯鏂囦欢** (`Game.Godot/Tests/Scenes/FullGameFlowTest.cs`):

```csharp
using Godot;
using GdUnit4.Api;
using System.Threading.Tasks;

/// <summary>
/// 瀹屾暣娓告垙娴佺▼闆嗘垚娴嬭瘯
/// 浠庝富鑿滃崟 鈫?娓告垙寮€濮?鈫?鍑绘潃鏁屼汉 鈫?娓告垙缁撴潫
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
        await Task.Delay(1000); // 绛夊緟鍦烘櫙鍔犺浇
        
        // Assert
        AssertThat(gameStarted).IsTrue()
            .WithMessage("娓告垙搴旇宸插惎鍔?);
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
        await Task.Delay(200); // 绛夊緟鏀诲嚮鍔ㄧ敾
        
        // Assert
        AssertThat(enemy.Health.Current).IsLess(initialHealth)
            .WithMessage("鏁屼汉琛€閲忓簲璇ュ噺灏?);
    }
}
```

---

## 11.7 娴嬭瘯鏁版嵁鍜?Fixtures

### 11.7.1 娴嬭瘯 Fixture 宸ュ巶

**Fixture 宸ュ巶** (`Game.Godot/Tests/Fixtures/GameFixtures.cs`):

```csharp
using System;

/// <summary>
/// 娓告垙鏁版嵁娴嬭瘯 Fixtures
/// 鎻愪緵甯哥敤鐨勬祴璇曟暟鎹璞?
/// </summary>
public static class GameFixtures
{
    /// <summary>
    /// 鍒涘缓娴嬭瘯鐢ㄧ帺瀹?
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
    /// 鍒涘缓娴嬭瘯鐢ㄦ晫浜?
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
    /// 鍒涘缓娴嬭瘯鐢ㄦ父鎴忓満鏅厤缃?
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

### 11.7.2 娴嬭瘯鍦烘櫙鏁版嵁

**Test Scenes TscnData** 鐩綍缁撴瀯锛?

```
Game.Godot/Tests/
鈹溾攢鈹€ TestScenes/
鈹?  鈹溾攢鈹€ MinimalGameScene.tscn    # 鏈€灏忓寲娓告垙鍦烘櫙
鈹?  鈹溾攢鈹€ UITestScene.tscn         # UI 缁勪欢娴嬭瘯鍦烘櫙
鈹?  鈹斺攢鈹€ SignalTestScene.tscn     # Signal 绯荤粺娴嬭瘯鍦烘櫙
鈹溾攢鈹€ TestData/
鈹?  鈹溾攢鈹€ player.json              # 鐜╁鏁版嵁鏍锋湰
鈹?  鈹溾攢鈹€ enemies.json             # 鏁屼汉鏁版嵁鏍锋湰
鈹?  鈹斺攢鈹€ game_config.json         # 娓告垙閰嶇疆鏍锋湰
鈹斺攢鈹€ Fixtures/
    鈹斺攢鈹€ GameFixtures.cs
```

---

## 11.8 娴嬭瘯鎵ц鍜屾姤鍛?

### 11.8.1 杩愯 GdUnit4 娴嬭瘯

**PowerShell 娴嬭瘯杩愯鑴氭湰** (`scripts/run-gdunit4-tests.ps1`):

```powershell
param(
    [string]$ProjectRoot = "C:\buildgame\sanguo",
    [switch]$OpenReport = $false,
    [string]$TestFilter = "*",
    [switch]$Headless = $false
)

Write-Host "杩愯 GdUnit4 鍦烘櫙闆嗘垚娴嬭瘯..." -ForegroundColor Green

$godotExe = "godot"
$projectPath = $ProjectRoot

# 鏋勫缓 Godot 鍛戒护
$godotArgs = @(
    "--path", $projectPath,
    "-s", "addons/gdunit4/bin/gdunitcli.cs",
    "-r", "$TestFilter.cs"
)

if ($Headless) {
    $godotArgs += "--headless"
}

# 杩愯娴嬭瘯
Write-Host "鎵ц鍛戒护: $godotExe $($godotArgs -join ' ')" -ForegroundColor Gray
& $godotExe $godotArgs

$lastExitCode = $LASTEXITCODE

if ($lastExitCode -eq 0) {
    Write-Host "PASS: GdUnit4 娴嬭瘯閫氳繃" -ForegroundColor Green
} else {
    Write-Host "FAIL: GdUnit4 娴嬭瘯澶辫触 (exit code: $lastExitCode)" -ForegroundColor Red
}

# 鎵撳紑鎶ュ憡锛堝鏋滄寚瀹氾級
if ($OpenReport) {
    $reportPath = Join-Path $projectPath "addons/gdunit4/reports/report.html"
    if (Test-Path $reportPath) {
        Invoke-Item $reportPath
    }
}

exit $lastExitCode
```

### 11.8.2 CI 闆嗘垚

**GitHub Actions 宸ヤ綔娴?* (`.github/workflows/gdunit4-tests.yml`):

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
      
      - name: 瀹夎 Godot 4.5
        run: |
          # 鍋囪 Godot 宸查€氳繃鍏朵粬鏂瑰紡瀹夎鎴栧彲浠庣紦瀛樿幏鍙?
          $godotPath = "C:\Program Files\Godot\bin\godot.exe"
          if (Test-Path $godotPath) {
            Write-Host "Godot 宸插畨瑁?
          } else {
            Write-Host "闇€瑕佸畨瑁?Godot 4.5"
          }
      
      - name: 杩愯 GdUnit4 娴嬭瘯
        run: |
          .\scripts\run-gdunit4-tests.ps1 `
            -ProjectRoot ${{ github.workspace }} `
            -Headless
      
      - name: 涓婁紶娴嬭瘯鎶ュ憡
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: gdunit4-reports
          path: addons/gdunit4/reports/
      
      - name: 妫€鏌ユ祴璇曠粨鏋?
        run: |
          if ($LASTEXITCODE -ne 0) {
            exit 1
          }
```

---

## 11.9 瀹屾垚娓呭崟

- [ ] GdUnit4 瀹夎骞堕厤缃?
- [ ] 缂栧啓 MainScene 闆嗘垚娴嬭瘯锛堚墺4 涓祴璇曠敤渚嬶級
- [ ] 缂栧啓 GameScene 闆嗘垚娴嬭瘯锛堚墺5 涓祴璇曠敤渚嬶級
- [ ] 缂栧啓 UI 缁勪欢娴嬭瘯锛圕ustomButton 绛夛級
- [ ] 缂栧啓 Signal 绯荤粺闆嗘垚娴嬭瘯锛堚墺4 涓祴璇曠敤渚嬶級
- [ ] 缂栧啓瀹屾暣娴佺▼闆嗘垚娴嬭瘯锛堢鍒扮锛?
- [ ] 鍒涘缓娴嬭瘯 Fixtures 鍜屾祴璇曟暟鎹?
- [ ] 楠岃瘉鎵€鏈夋祴璇曢€氳繃锛?00% 閫氳繃鐜囷級
- [ ] 鐢熸垚娴嬭瘯瑕嗙洊鐜囨姤鍛婏紙鈮?0%锛?
- [ ] 闆嗘垚鍒?CI 娴佺▼
- [ ] 鏇存柊鏂囨。鍜屾祴璇曡繍琛屾寚鍗?

**瀹屾垚鏍囧織**:

```bash
# 鎵€鏈?GdUnit4 娴嬭瘯閫氳繃
.\scripts\run-gdunit4-tests.ps1 -ProjectRoot . -Headless
# 杈撳嚭锛歅ASS GdUnit4 娴嬭瘯閫氳繃

# 闆嗘垚娴嬭瘯瑕嗙洊鐜囪揪鍒?80%+
# 鎶ュ憡浣嶇疆锛歛ddons/gdunit4/reports/coverage.html
```

---

## 11.10 椋庨櫓鍜岀紦瑙?

| 椋庨櫓 | 褰卞搷 | 缂撹В绛栫暐 |
|------|------|--------|
| 鍦烘櫙鍔犺浇寤惰繜 | 娴嬭瘯瓒呮椂澶辫触 | 璁剧疆鍚堢悊瓒呮椂锛?000ms锛夛紝棰勫姞杞藉叕鍏辫祫婧?|
| Signal 鏃跺簭闂 | 绔炴€佹潯浠?| 浣跨敤 `await Task.Delay()` 鍚屾锛屼娇鐢?`WaitForSignal()` |
| 娴嬭瘯闅旂涓嶈冻 | 浜ゅ弶姹℃煋 | 姣忎釜娴嬭瘯 `[Before]`/`[After]` 娓呯悊璧勬簮 |
| Godot 缂栬緫鍣ㄤ緷璧?| 鏃犳硶 CI 杩愯 | 浣跨敤 `--headless` 妯″紡 |
| GdUnit4 鐗堟湰鍐茬獊 | 鎻掍欢鍔犺浇澶辫触 | 閿佸畾 GdUnit4 鐗堟湰锛屽畾鏈熸洿鏂板吋瀹规€ф鏌?|

---

## 11.11 鍚庣画 Phase

**Phase 12: E2E 娴嬭瘯** (Godot Headless + 鑷姩鍖?
- 浠庝富鑿滃崟瀹屾暣娓告垙娴佺▼鑷姩鍖栨祴璇?
- 鎬ц兘鍩哄噯娴嬭瘯
- 鍘嬪姏娴嬭瘯锛堝娉㈡晫浜猴級


## Python 绛夋晥鑴氭湰绀轰緥锛圙dUnit4锛?

浠ヤ笅绀轰緥鎻愪緵鍦?Windows 涓婁娇鐢?Python 鎵ц GdUnit4 鍦烘櫙娴嬭瘯鐨勬渶灏忓彲鐢ㄨ剼鏈紝浣滀负 PowerShell 鍖呰鑴氭湰鐨勬浛浠ｆ柟妗堛€?

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

璇存槑锛?
- 鎶ュ憡榛樿杈撳嚭鍒?`addons/gdunit4/reports/`锛屽彲鍦?CI 宸ヤ欢涓敹闆嗐€?
- 濡傞渶灏嗘姤鍛婂鍒跺埌浠撳簱 `logs/ci/YYYY-MM-DD/`锛屽弬鑰?Phase-13 鏂囨。涓殑 Python 鏀堕泦鐗囨銆?


> 鍙傝€?Runner 鎺ュ叆鎸囧崡锛氳 docs/migration/gdunit4-csharp-runner-integration.md銆?


---

## 鍋ュ．鎬ф敞鍏ユ祴璇曪紙寤鸿锛?

- 鍦?C# 娴嬭瘯涓敞鍏ュ紓甯歌矾寰勶紙鍦烘櫙鍔犺浇澶辫触/鑺傜偣缂哄け/淇″彿鏈Е鍙戯級
- 瀵光€滃け璐ヤ竴娆¤嚜鍔ㄩ噸璇曪紱浠嶅け璐ュ垯闄嶇骇/杩斿洖涓昏彍鍗曗€濈殑娴佺▼杩涜鏂█
- 灏嗗紓甯告敞鍏ョ殑缁撴灉鍐欏叆鎶ュ憡锛屼綔涓衡€滃満鏅祴璇曢€氳繃鐜?100%鈥濈殑鍓嶇疆闂ㄧ渚濇嵁锛堜笌 Phase-13 鑱氬悎涓€鑷达級
# Phase 11 鈥?鍦烘櫙闆嗘垚娴嬭瘯锛圖eprecated锛?
> 鐘舵€侊細Deprecated锛堟湰椤靛凡搴熷純锛屼粎浣滃巻鍙插弬鑰冿級銆傝闃呰骞朵互 REVISED 鐗堟湰涓哄敮涓€鍙ｅ緞锛歚docs/migration/Phase-11-Scene-Integration-Tests-REVISED.md`銆?
鏈〉淇濈暀鏄负浜嗚拷婧縼绉绘€濊矾鐨勬紨杩涖€傚疄闄呮墽琛屼笌楠屾敹浠?REVISED 鏂囨。涓哄噯銆?
