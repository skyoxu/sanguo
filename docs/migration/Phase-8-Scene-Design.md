# Phase 8: Scene Tree 与 Node 设计

> 状态: 设计阶段
> 预估工时: 8-12 天
> 风险等级: 中
> 前置条件: Phase 1-7 完成

---

## 目标

掌握 Godot Scene Tree 架构，建立 Node 组合与继承模式，实现可测试、可维护的场景设计。

---

## Scene Tree 核心概念

### Godot 场景树 vs LegacyUIFramework 组件树

| 概念 | LegacyUIFramework (LegacyProject) | Godot (godotgame) |
|-----|-----------------|------------------|
| 基本单元 | Component (函数/类) | Node (场景节点) |
| 组织方式 | JSX 嵌套 | Scene Tree 树形结构 |
| 复用机制 | 组件导入 | PackedScene 实例化 |
| 生命周期 | mount/unmount/render | _Ready/_Process/_ExitTree |
| 父子通信 | Props down/Callbacks up | Signals + GetNode |
| 状态管理 | useState/Context | Node Properties + Signals |
| 事件系统 | Synthetic Events | Godot Signals |

### Node 基础概念

```
Node (基类)
├─ Node2D (2D 游戏对象)
│  ├─ Sprite2D (精灵)
│  ├─ AnimatedSprite2D (动画精灵)
│  ├─ CollisionShape2D (碰撞形状)
│  ├─ Area2D (区域检测)
│  └─ CharacterBody2D (角色控制器)
│
├─ Node3D (3D 游戏对象)
│  ├─ MeshInstance3D (网格实例)
│  ├─ Camera3D (3D 相机)
│  └─ CollisionShape3D (3D 碰撞)
│
├─ Control (UI 节点)
│  ├─ Button
│  ├─ Label
│  └─ Container (VBoxContainer, HBoxContainer, etc.)
│
├─ CanvasLayer (画布层)
├─ Timer (定时器)
├─ AudioStreamPlayer (音频播放器)
└─ HTTPRequest (HTTP 请求)
```

---

## 1. Scene 文件结构

### 场景文件格式 (.tscn)

**Player.tscn** (文本格式，便于版本控制):

```
[gd_scene load_steps=4 format=3 uid="uid://player_scene"]

[ext_resource type="Script" path="res://Scripts/PlayerController.cs" id="1"]
[ext_resource type="Texture2D" uid="uid://player_texture" path="res://Assets/Textures/player.png" id="2"]

[sub_resource type="RectangleShape2D" id="1"]
size = Vector2(32, 32)

[node name="Player" type="CharacterBody2D"]
script = ExtResource("1")

[node name="Sprite" type="Sprite2D" parent="."]
texture = ExtResource("2")

[node name="CollisionShape" type="CollisionShape2D" parent="."]
shape = SubResource("1")

[node name="AnimationPlayer" type="AnimationPlayer" parent="."]
```

**关键部分解析**:

1. **load_steps**: 场景加载所需的资源数量（脚本、纹理、子资源等）
2. **uid**: 全局唯一标识符，用于跨场景引用
3. **ext_resource**: 外部资源引用（脚本、纹理、音频等）
4. **sub_resource**: 内联资源定义（形状、动画、材质等）
5. **node**: 节点定义，包括类型、父节点、属性

### Scene 继承 vs 组合

**继承模式** (适合变体设计):

```
BaseEnemy.tscn
├─ Sprite2D
├─ CollisionShape2D
└─ HealthBar

继承 ↓

FlyingEnemy.tscn (继承自 BaseEnemy.tscn)
└─ 添加 WingAnimation 节点
```

**组合模式** (适合功能组合):

```
Player.tscn
├─ Sprite2D
├─ CollisionShape2D
├─ InventoryComponent (实例化的场景)
├─ HealthComponent (实例化的场景)
└─ MovementComponent (实例化的场景)
```

---

## 2. Node 生命周期

### 核心生命周期方法

```csharp
// Game.Godot/Scripts/PlayerController.cs

using Godot;

namespace Game.Godot.Scripts;

public partial class PlayerController : CharacterBody2D
{
    // 1. _EnterTree: 节点进入场景树时调用（最早）
    public override void _EnterTree()
    {
        GD.Print("PlayerController: _EnterTree - Node added to tree");
        // 适用场景：注册全局监听器、初始化静态资源
    }

    // 2. _Ready: 节点及其子节点都加载完成后调用（初始化）
    public override void _Ready()
    {
        GD.Print("PlayerController: _Ready - Scene fully loaded");

        // 获取子节点引用（此时子节点已存在）
        _sprite = GetNode<Sprite2D>("Sprite");
        _collisionShape = GetNode<CollisionShape2D>("CollisionShape");

        // 连接信号
        BodyEntered += OnBodyEntered;

        // 初始化状态
        Health = MaxHealth;

        GD.Print("PlayerController initialized successfully");
    }

    // 3. _Process: 每帧调用（用于游戏逻辑更新）
    public override void _Process(double delta)
    {
        // 适用场景：输入处理、动画更新、UI 更新
        HandleInput(delta);
        UpdateAnimation();
    }

    // 4. _PhysicsProcess: 物理帧调用（固定时间步长）
    public override void _PhysicsProcess(double delta)
    {
        // 适用场景：物理移动、碰撞检测
        var velocity = Velocity;

        // 应用重力
        if (!IsOnFloor())
        {
            velocity.Y += Gravity * (float)delta;
        }

        // 处理移动
        var inputDirection = Input.GetAxis("move_left", "move_right");
        velocity.X = inputDirection * Speed;

        Velocity = velocity;
        MoveAndSlide();
    }

    // 5. _ExitTree: 节点从场景树移除前调用（清理）
    public override void _ExitTree()
    {
        GD.Print("PlayerController: _ExitTree - Cleanup before removal");

        // 断开信号连接
        if (IsInstanceValid(this))
        {
            BodyEntered -= OnBodyEntered;
        }

        // 释放非托管资源
        // 注意：Godot 管理的资源会自动释放
    }

    // 6. _Notification: 接收系统通知（高级用法）
    public override void _Notification(int what)
    {
        switch (what)
        {
            case NotificationEnterTree:
                GD.Print("Notification: Enter Tree");
                break;
            case NotificationExitTree:
                GD.Print("Notification: Exit Tree");
                break;
            case NotificationPaused:
                GD.Print("Notification: Paused");
                break;
            case NotificationUnpaused:
                GD.Print("Notification: Unpaused");
                break;
        }
    }

    private Sprite2D _sprite = null!;
    private CollisionShape2D _collisionShape = null!;

    [Export]
    public int MaxHealth { get; set; } = 100;

    [Export]
    public float Speed { get; set; } = 200f;

    [Export]
    public float Gravity { get; set; } = 980f;

    public int Health { get; private set; }

    private void HandleInput(double delta)
    {
        // 输入处理逻辑
    }

    private void UpdateAnimation()
    {
        // 动画更新逻辑
    }

    private void OnBodyEntered(Node2D body)
    {
        GD.Print($"Player collided with: {body.Name}");
    }
}
```

**生命周期顺序总结**:

```
场景加载时:
1. _EnterTree (父节点先于子节点)
2. _Ready (子节点先于父节点)

每帧更新:
3. _Process (渲染帧，帧率不固定)
4. _PhysicsProcess (物理帧，默认 60 FPS)

场景移除时:
5. _ExitTree (父节点先于子节点)
```

---

## 3. 父子节点关系与节点路径

### 获取子节点 (GetNode)

```csharp
// Game.Godot/Scripts/UIController.cs

public partial class UIController : Control
{
    private Label _scoreLabel = null!;
    private Button _startButton = null!;
    private VBoxContainer _menu = null!;

    public override void _Ready()
    {
        // 方式 1: 直接路径（推荐，类型安全）
        _scoreLabel = GetNode<Label>("HUD/ScoreLabel");

        // 方式 2: 绝对路径（从根节点开始）
        _startButton = GetNode<Button>("/root/Main/UI/Menu/StartButton");

        // 方式 3: 相对路径（../ 表示父节点）
        _menu = GetNode<VBoxContainer>("../Menu");

        // 方式 4: 使用 % 访问唯一名称节点（Godot 4.0+）
        var uniqueNode = GetNode<Control>("%UniqueNodeName");

        // 方式 5: 检查节点是否存在
        if (HasNode("HUD/HealthBar"))
        {
            var healthBar = GetNode<Control>("HUD/HealthBar");
        }

        // 方式 6: 使用 NodePath 变量（可在 Inspector 中配置）
        var customPath = new NodePath("HUD/ScoreLabel");
        _scoreLabel = GetNode<Label>(customPath);
    }
}
```

### Export NodePath 模式（推荐用于跨场景引用）

```csharp
// Game.Godot/Scripts/PlayerController.cs

public partial class PlayerController : CharacterBody2D
{
    // 在 Inspector 中可拖拽配置节点路径
    [Export]
    public NodePath HealthBarPath { get; set; } = new NodePath("../UI/HealthBar");

    [Export]
    public NodePath CameraPath { get; set; } = new NodePath("Camera2D");

    private Control _healthBar = null!;
    private Camera2D _camera = null!;

    public override void _Ready()
    {
        // 运行时解析路径
        if (!HealthBarPath.IsEmpty)
        {
            _healthBar = GetNode<Control>(HealthBarPath);
        }

        if (!CameraPath.IsEmpty)
        {
            _camera = GetNode<Camera2D>(CameraPath);
        }
    }
}
```

**NodePath 最佳实践**:

1. **硬编码路径**：适合场景内部固定结构的节点
2. **Export NodePath**：适合需要在 Inspector 中配置的节点引用
3. **唯一名称 (%)**：适合跨场景的全局访问（需在编辑器中标记为 Unique）
4. **信号通信**：适合松耦合的节点通信（不依赖路径）

---

## 4. Scene 实例化与管理

### PackedScene 加载与实例化

```csharp
// Game.Godot/Scripts/EnemySpawner.cs

using Godot;
using System.Collections.Generic;

namespace Game.Godot.Scripts;

public partial class EnemySpawner : Node2D
{
    [Export]
    public PackedScene EnemyScene { get; set; } = null!;

    [Export]
    public float SpawnInterval { get; set; } = 2.0f;

    [Export]
    public int MaxEnemies { get; set; } = 10;

    private Timer _spawnTimer = null!;
    private List<Node2D> _activeEnemies = new();

    public override void _Ready()
    {
        // 方式 1: 在 Inspector 中配置 PackedScene
        // (推荐，便于可视化配置)

        // 方式 2: 代码加载场景
        // EnemyScene = GD.Load<PackedScene>("res://Scenes/Enemies/BasicEnemy.tscn");

        // 设置定时器
        _spawnTimer = new Timer
        {
            WaitTime = SpawnInterval,
            Autostart = true
        };
        _spawnTimer.Timeout += OnSpawnTimerTimeout;
        AddChild(_spawnTimer);
    }

    private void OnSpawnTimerTimeout()
    {
        if (_activeEnemies.Count >= MaxEnemies) return;

        SpawnEnemy();
    }

    public void SpawnEnemy()
    {
        if (EnemyScene == null)
        {
            GD.PushError("EnemyScene is not set!");
            return;
        }

        // 实例化场景
        var enemy = EnemyScene.Instantiate<Node2D>();

        // 设置位置
        enemy.Position = Position + new Vector2(
            GD.Randf() * 100 - 50,
            GD.Randf() * 100 - 50
        );

        // 添加到场景树（作为当前节点的兄弟节点）
        GetParent().AddChild(enemy);

        // 追踪敌人实例
        _activeEnemies.Add(enemy);

        // 监听敌人死亡信号
        if (enemy.HasSignal("defeated"))
        {
            enemy.Connect("defeated", Callable.From(() => OnEnemyDefeated(enemy)));
        }
    }

    private void OnEnemyDefeated(Node2D enemy)
    {
        _activeEnemies.Remove(enemy);

        // 延迟移除（等待死亡动画）
        enemy.QueueFree();
    }

    public override void _ExitTree()
    {
        // 清理所有敌人
        foreach (var enemy in _activeEnemies)
        {
            if (IsInstanceValid(enemy))
            {
                enemy.QueueFree();
            }
        }
        _activeEnemies.Clear();
    }
}
```

### 场景切换 (SceneTree.ChangeSceneToFile)

```csharp
// Game.Godot/Scripts/SceneManager.cs

using Godot;

namespace Game.Godot.Scripts;

public partial class SceneManager : Node
{
    [Signal]
    public delegate void SceneChangedEventHandler(string oldScene, string newScene);

    private string _currentScene = string.Empty;

    public override void _Ready()
    {
        _currentScene = GetTree().CurrentScene?.SceneFilePath ?? string.Empty;
    }

    /// <summary>
    /// 切换到新场景（立即切换）
    /// </summary>
    public void ChangeScene(string scenePath)
    {
        var oldScene = _currentScene;

        var error = GetTree().ChangeSceneToFile(scenePath);
        if (error != Error.Ok)
        {
            GD.PushError($"Failed to change scene to {scenePath}: {error}");
            return;
        }

        _currentScene = scenePath;
        EmitSignal(SignalName.SceneChanged, oldScene, scenePath);
    }

    /// <summary>
    /// 切换到新场景（带过渡效果）
    /// </summary>
    public async void ChangeSceneWithTransition(string scenePath, float fadeTime = 0.5f)
    {
        // 创建过渡层
        var transition = new ColorRect
        {
            Color = Colors.Black,
            Modulate = new Color(1, 1, 1, 0)
        };
        transition.SetAnchorsPreset(Control.LayoutPreset.FullRect);

        GetTree().Root.AddChild(transition);

        // 淡出
        var tween = CreateTween();
        tween.TweenProperty(transition, "modulate:a", 1.0f, fadeTime);
        await ToSignal(tween, Tween.SignalName.Finished);

        // 切换场景
        ChangeScene(scenePath);

        // 淡入
        tween = CreateTween();
        tween.TweenProperty(transition, "modulate:a", 0.0f, fadeTime);
        await ToSignal(tween, Tween.SignalName.Finished);

        // 移除过渡层
        transition.QueueFree();
    }

    /// <summary>
    /// 预加载场景（后台加载，不阻塞）
    /// </summary>
    public async void PreloadSceneAsync(string scenePath)
    {
        var loader = ResourceLoader.LoadThreadedRequest(scenePath);

        while (true)
        {
            var status = ResourceLoader.LoadThreadedGetStatus(scenePath);

            if (status == ResourceLoader.ThreadLoadStatus.Loaded)
            {
                var scene = ResourceLoader.LoadThreadedGet(scenePath);
                GD.Print($"Scene preloaded: {scenePath}");
                break;
            }
            else if (status == ResourceLoader.ThreadLoadStatus.Failed ||
                     status == ResourceLoader.ThreadLoadStatus.InvalidResource)
            {
                GD.PushError($"Failed to preload scene: {scenePath}");
                break;
            }

            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        }
    }

    /// <summary>
    /// 重新加载当前场景
    /// </summary>
    public void ReloadCurrentScene()
    {
        GetTree().ReloadCurrentScene();
    }

    /// <summary>
    /// 添加子场景（不切换，叠加显示）
    /// </summary>
    public Node? AddSubScene(string scenePath)
    {
        var packedScene = GD.Load<PackedScene>(scenePath);
        if (packedScene == null)
        {
            GD.PushError($"Failed to load scene: {scenePath}");
            return null;
        }

        var instance = packedScene.Instantiate();
        GetTree().Root.AddChild(instance);

        return instance;
    }
}
```

---

## 5. Node Groups 与 Tags

### 使用 Groups 实现批量操作

```csharp
// Game.Godot/Scripts/Enemy.cs

public partial class Enemy : CharacterBody2D
{
    public override void _Ready()
    {
        // 添加到 "enemies" 组
        AddToGroup("enemies");
        AddToGroup("damageable");
    }
}

// Game.Godot/Scripts/Player.cs

public partial class Player : CharacterBody2D
{
    public override void _Ready()
    {
        AddToGroup("player");
        AddToGroup("damageable");
    }

    public void AttackAllEnemies(int damage)
    {
        // 获取所有 "enemies" 组的节点
        var enemies = GetTree().GetNodesInGroup("enemies");

        foreach (Node enemy in enemies)
        {
            if (enemy is Enemy enemyScript)
            {
                enemyScript.TakeDamage(damage);
            }
        }
    }

    public void HealAllDamageableUnits(int healAmount)
    {
        // 获取所有 "damageable" 组的节点
        var damageableUnits = GetTree().GetNodesInGroup("damageable");

        foreach (Node unit in damageableUnits)
        {
            if (unit.HasMethod("Heal"))
            {
                unit.Call("Heal", healAmount);
            }
        }
    }
}

// Game.Godot/Scripts/GameManager.cs

public partial class GameManager : Node
{
    public void PauseAllEnemies()
    {
        // 暂停所有敌人
        GetTree().CallGroup("enemies", "set_process", false);
        GetTree().CallGroup("enemies", "set_physics_process", false);
    }

    public void ResumeAllEnemies()
    {
        // 恢复所有敌人
        GetTree().CallGroup("enemies", "set_process", true);
        GetTree().CallGroup("enemies", "set_physics_process", true);
    }

    public int CountActiveEnemies()
    {
        return GetTree().GetNodesInGroup("enemies").Count;
    }
}
```

**Groups 使用场景**:

1. **批量控制**：暂停/恢复一组节点
2. **碰撞筛选**：快速识别碰撞对象类型
3. **事件广播**：向特定组发送消息
4. **查询统计**：统计特定类型节点数量

---

## 6. Autoload (单例模式)

### 注册全局单例

**project.godot**:

```ini
[autoload]

ServiceLocator="*res://Autoloads/ServiceLocator.cs"
EventBus="*res://Autoloads/EventBus.cs"
GameState="*res://Autoloads/GameState.cs"
AudioManager="*res://Autoloads/AudioManager.cs"
```

**ServiceLocator Autoload**:

```csharp
// Game.Godot/Autoloads/ServiceLocator.cs

using Godot;
using Game.Core.Ports;
using Game.Godot.Adapters;

namespace Game.Godot.Autoloads;

/// <summary>
/// 全局服务定位器（Autoload 单例）
/// 在 project.godot 中注册为自动加载
/// </summary>
public partial class ServiceLocator : Node
{
    // 单例访问点
    public static ServiceLocator Instance { get; private set; } = null!;

    // 服务实例
    public ITime Time { get; private set; } = null!;
    public IInput InputService { get; private set; } = null!;
    public IResourceLoader ResourceLoader { get; private set; } = null!;
    public IAudioPlayer AudioPlayer { get; private set; } = null!;
    public IDataStore DataStore { get; private set; } = null!;
    public ILogger Logger { get; private set; } = null!;

    public override void _EnterTree()
    {
        // 设置单例（在 _EnterTree 中，确保最早初始化）
        Instance = this;
    }

    public override void _Ready()
    {
        // 注册所有适配器
        Time = new GodotTimeAdapter();
        InputService = new GodotInputAdapter();
        ResourceLoader = new GodotResourceLoader();
        AudioPlayer = new GodotAudioPlayer();
        DataStore = new SqliteDataStore();
        Logger = new GodotLogger("Game");

        // 初始化数据库
        DataStore.Open("user://game.db");

        GD.Print("ServiceLocator initialized successfully");
    }

    public override void _ExitTree()
    {
        DataStore?.Close();
    }
}
```

**EventBus Autoload**:

```csharp
// Game.Godot/Autoloads/EventBus.cs

using Godot;
using System;
using System.Collections.Generic;

namespace Game.Godot.Autoloads;

/// <summary>
/// 全局事件总线（发布-订阅模式）
/// </summary>
public partial class EventBus : Node
{
    public static EventBus Instance { get; private set; } = null!;

    private Dictionary<string, List<Action<object>>> _eventHandlers = new();

    public override void _EnterTree()
    {
        Instance = this;
    }

    /// <summary>
    /// 订阅事件
    /// </summary>
    public void Subscribe(string eventName, Action<object> handler)
    {
        if (!_eventHandlers.ContainsKey(eventName))
        {
            _eventHandlers[eventName] = new List<Action<object>>();
        }

        _eventHandlers[eventName].Add(handler);
    }

    /// <summary>
    /// 取消订阅
    /// </summary>
    public void Unsubscribe(string eventName, Action<object> handler)
    {
        if (_eventHandlers.ContainsKey(eventName))
        {
            _eventHandlers[eventName].Remove(handler);
        }
    }

    /// <summary>
    /// 发布事件
    /// </summary>
    public void Publish(string eventName, object data)
    {
        if (_eventHandlers.ContainsKey(eventName))
        {
            foreach (var handler in _eventHandlers[eventName])
            {
                try
                {
                    handler(data);
                }
                catch (Exception ex)
                {
                    GD.PushError($"EventBus error in handler for '{eventName}': {ex.Message}");
                }
            }
        }
    }

    /// <summary>
    /// 清空所有订阅
    /// </summary>
    public void Clear()
    {
        _eventHandlers.Clear();
    }
}
```

**使用 Autoload**:

```csharp
// Game.Godot/Scripts/PlayerController.cs

public partial class PlayerController : CharacterBody2D
{
    public override void _Ready()
    {
        // 访问全局服务
        var logger = ServiceLocator.Instance.Logger;
        logger.LogInfo("PlayerController initialized");

        // 订阅全局事件
        EventBus.Instance.Subscribe("player_damaged", OnPlayerDamaged);

        // 访问全局状态
        var currentLevel = GameState.Instance.CurrentLevel;
    }

    private void OnPlayerDamaged(object data)
    {
        var damage = (int)data;
        GD.Print($"Player took {damage} damage");
    }

    public void TakeDamage(int amount)
    {
        // 发布全局事件
        EventBus.Instance.Publish("player_damaged", amount);
    }

    public override void _ExitTree()
    {
        // 取消订阅
        EventBus.Instance.Unsubscribe("player_damaged", OnPlayerDamaged);
    }
}
```

---

## 7. 场景组织最佳实践

### 推荐目录结构

```
Game.Godot/Scenes/
├── Main.tscn                      # 主场景（启动入口）
│
├── UI/                            # UI 场景
│   ├── MainMenu.tscn
│   ├── HUD.tscn
│   ├── PauseMenu.tscn
│   ├── SettingsMenu.tscn
│   └── Components/                # 可复用 UI 组件
│       ├── PrimaryButton.tscn
│       ├── TextInput.tscn
│       └── HealthBar.tscn
│
├── Game/                          # 游戏实体场景
│   ├── Player/
│   │   ├── Player.tscn
│   │   └── PlayerCamera.tscn
│   ├── Enemies/
│   │   ├── BaseEnemy.tscn        # 敌人基类场景
│   │   ├── FlyingEnemy.tscn      # 继承自 BaseEnemy
│   │   └── GroundEnemy.tscn      # 继承自 BaseEnemy
│   ├── Items/
│   │   ├── Coin.tscn
│   │   ├── HealthPotion.tscn
│   │   └── Weapon.tscn
│   └── Effects/
│       ├── Explosion.tscn
│       ├── HitEffect.tscn
│       └── Particle.tscn
│
├── Levels/                        # 关卡场景
│   ├── Level1.tscn
│   ├── Level2.tscn
│   ├── BossLevel.tscn
│   └── Tilemap/                   # 地图相关
│       ├── GroundTileset.tres
│       └── WallTileset.tres
│
└── Components/                    # 功能组件（可附加到任何节点）
    ├── HealthComponent.tscn
    ├── MovementComponent.tscn
    ├── InventoryComponent.tscn
    └── AIComponent.tscn
```

### 场景命名约定

1. **PascalCase**: `PlayerController.tscn`, `MainMenu.tscn`
2. **语义化**: 名称体现功能，如 `HealthBar.tscn`, `EnemySpawner.tscn`
3. **组件后缀**: 功能组件使用 `Component` 后缀，如 `HealthComponent.tscn`
4. **Base 前缀**: 抽象基类使用 `Base` 前缀，如 `BaseEnemy.tscn`

### 场景设计原则

1. **单一职责**：每个场景只负责一个功能模块
2. **组合优于继承**：优先使用场景实例化组合功能
3. **最小化耦合**：通过 Signals 和 EventBus 解耦场景
4. **可测试性**：场景应能独立测试，不依赖特定父场景

---

## 8. 测试场景架构

### GdUnit4 场景测试

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

### xUnit 场景逻辑测试

```csharp
// Game.Core.Tests/Scenes/SceneManagerTests.cs

using FluentAssertions;
using Game.Core.Tests.Fakes;
using Game.Godot.Scripts;
using Xunit;

namespace Game.Core.Tests.Scenes;

public class SceneManagerTests
{
    [Fact]
    public void ChangeScene_ShouldEmitSceneChangedSignal()
    {
        // Arrange
        var fakeSceneTree = new FakeSceneTree();
        var sceneManager = new FakeSceneManager(fakeSceneTree);

        string? emittedOldScene = null;
        string? emittedNewScene = null;

        sceneManager.SceneChangedEvent += (oldScene, newScene) =>
        {
            emittedOldScene = oldScene;
            emittedNewScene = newScene;
        };

        // Act
        sceneManager.ChangeScene("res://Scenes/Levels/Level2.tscn");

        // Assert
        emittedOldScene.Should().Be("res://Scenes/Levels/Level1.tscn");
        emittedNewScene.Should().Be("res://Scenes/Levels/Level2.tscn");
    }

    [Fact]
    public void PreloadSceneAsync_ShouldLoadSceneInBackground()
    {
        // Arrange
        var fakeResourceLoader = new FakeResourceLoader();
        var sceneManager = new FakeSceneManager(fakeResourceLoader);

        // Act
        sceneManager.PreloadSceneAsync("res://Scenes/Levels/Level3.tscn");
        fakeResourceLoader.SimulateLoadComplete();

        // Assert
        fakeResourceLoader.IsSceneLoaded("res://Scenes/Levels/Level3.tscn").Should().BeTrue();
    }
}
```

---

## 9. CI 集成

### 场景结构验证 (GitHub Actions)

```yaml
# .github/workflows/scene-validation.yml

name: Scene Validation

on: [push, pull_request]

jobs:
  validate-scenes:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Godot
        uses: chickensoft-games/setup-godot@v1
        with:
          version: 4.5.0
          use-dotnet: true

      - name: Validate Scene Structure
        run: |
          # 检查所有场景文件语法
          godot --headless --script scripts/validate_scenes.cs

      - name: Run GdUnit4 Scene Tests
        run: |
          godot --headless --path . `
            --script res://addons/gdUnit4/bin/GdUnitCmdTool.cs `
            --conf res://GdUnitRunner.cfg `
            --output ./TestResults/scene-tests.xml

      - name: Upload Test Results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: scene-test-results
          path: TestResults/scene-tests.xml
```

**场景验证脚本** (`scripts/validate_scenes.cs`):

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

## 完成标准

- [ ] 理解 Scene Tree 架构与 Node 生命周期
- [ ] 掌握场景继承与组合模式
- [ ] 熟练使用 GetNode 和 NodePath
- [ ] 实现 PackedScene 实例化与场景切换
- [ ] 使用 Groups 实现批量操作
- [ ] 创建 Autoload 全局单例 (ServiceLocator/EventBus)
- [ ] 场景组织遵循最佳实践（目录结构与命名）
- [ ] GdUnit4 场景测试覆盖主要场景
- [ ] xUnit 逻辑测试覆盖场景管理逻辑
- [ ] CI 集成场景结构验证
- [ ] ScreenNavigator + ScreenRoot/HUD/Overlays 结构通过 GdUnit4 集成测试（如 test_screen_navigator.gd、test_screen_navigation_flow.gd）
- [ ] Settings SSoT 行为（ConfigFile 优先于 DB）通过集成测试验证（test_settings_precedence_placeholder.gd / test_settings_configfile_wins_over_db，符合 ADR‑0023）
- [ ] UI/Glue 测试符合 docs/testing-framework.md 中 UI/Glue 测试规范（帧轮询上限、无 InputEvents、EventBus 事件）

---

## 下一步

完成本阶段后，继续：

-> [Phase-9-Signal-System.md](Phase-9-Signal-System.md) — CloudEvents → Godot Signals 迁移

## Root 分层建议 / Root Layering

- 推荐主场景分层：
  - `ScreenRoot`（动态屏幕挂载点）
  - `HUD`（常驻 UI）
  - `Overlays`（Modal/Toast 等叠加）
  - 引导节点：`ThemeApplier`、`SettingsLoader`、`InputMapper`

> 口径对齐：Settings 读取/写入与持久化以 ADR‑0006（Godot 数据存储）、ADR‑0023（Settings SSoT = ConfigFile）以及 CH05/CH06 为准，本 Phase 聚焦场景/屏幕结构与信号流，不重复存储细节。

## 导航器 / Screen Navigator

- 组件：`Game.Godot/Scripts/Navigation/ScreenNavigator.cs`
- 用法：在主场景挂 `ScreenNavigator`，设置 `ScreenRootPath` 指向容器节点
- 切换：`nav.SwitchTo("res://Game.Godot/Scenes/Screens/StartScreen.tscn")`

### 与 MainMenu 联动

- Main 监听 `ui.menu.start`：优先加载示例 `DemoScreen`（当 `TEMPLATE_DEMO=1`），否则尝试加载 `Scenes/Screens/StartScreen.tscn`（若存在）


## Overlays 层用法 / Overlays Layer

- 在主场景下新增 `Overlays`（Control）：用于承载 Modal/Toast 等叠加层，避免与 ScreenRoot 互相影响。
- 使用方式：在需要时 `Overlays.AddChild(instance)`；示例组件位于 `Game.Godot/Examples/Components/**`。

## Screen 生命周期与信号约定 / Lifecycle & Signals

- 生命周期（推荐钩子）:
  - `Enter()`：Screen 被导航器实例化并即将显示（可选自定义方法）
  - `Exit()`：Screen 被替换前触发（释放资源/断开信号）（可选自定义方法）
- 信号命名：`screen.<name>.<action>`，例如 `screen.start.loaded`、`screen.settings.saved`
  - `screen.settings.saved` 事件应触发 SettingsPanel 通过 ConfigFile（user://settings.cfg）持久化设置（见 ADR‑0023），而不是直接写入数据库。
- 领域事件仍通过 `/root/EventBus`，UI 层尽量发布语义清晰的 screen 事件供上层协调。


### Overlays 节点（已添加）

- 主场景 `Main.tscn` 已添加 `Overlays` 容器节点（Control，锚定全屏），用于承载 Modal/Toast 等叠加层。

### 导航钩子（Enter/Exit）

- `ScreenNavigator.SwitchTo(...)` 会在卸载旧 Screen 前调用其 `Exit()`（若存在），在加载新 Screen 后调用其 `Enter()`（若存在），便于管理资源/信号。


### Overlays 用法示例

```csharp
// 在 Screen 中将 Modal/Toast 挂到 Overlays
var overlays = GetNodeOrNull<Control>("/root/Main/Overlays");
var ps = ResourceLoader.Load<PackedScene>("res://Game.Godot/Examples/Components/Modal.tscn");
if (overlays != null && ps != null) {
    var modal = ps.Instantiate<Control>();
    overlays.AddChild(modal);
    modal.Call("Open", "Message");
}
```


## Screen 过渡 / Screen Transitions

- 导航器支持淡入淡出过渡：`UseFadeTransition=true`，`FadeDurationSec` 可配置。
- 过渡期间 Overlays 会生成全屏 `ColorRect`（拦截输入），切换完成后移除。
- 可按需替换为自定义过渡（AnimationPlayer/Shader）。

## Z 次序与输入遮罩 / Z-Order & Input Mask

- `Overlays.z_index=100`，默认 `mouse_filter=Ignore`（1），需要阻塞输入的叠加层自行设置 `Stop`。
- 过渡遮罩自动设置为 `Stop`，确保切换时屏幕不接收输入。


### Enter/Exit 示例 / Example

```csharp
// Game.Godot/Scripts/Screens/StartScreen.cs
public void Enter() { GD.Print("[StartScreen] Enter"); }
public void Exit()  { GD.Print("[StartScreen] Exit"); }
```


## 跨 Screen 导航示例 / Cross-Screen Navigation

- 示例：`Examples/Screens/DemoScreen.tscn` 按钮导航到 `Scenes/Screens/SettingsScreen.tscn`；Settings 有 Back 返回 `StartScreen`。
- 观察日志：Enter/Exit 钩子、淡入淡出过渡遮罩。

## Screen 规范与模板 / Screen Guidelines & Template

- 路径与命名：
  - 路径：`Game.Godot/Scenes/Screens/<Name>.tscn` 与 `Game.Godot/Scripts/Screens/<Name>.cs` 一一对应。
  - 命名：`<Name>` 使用 PascalCase，节点名称与文件名一致，便于查找与导航。
- 资源管理：
  - 在 `_Ready` 仅做轻量初始化；重型加载放到 `Enter()` 或异步流程中（如 `CallDeferred`/Tween）。
  - 在 `Exit()` 里面释放订阅、断开信号、停止计时器、保存必要状态，避免泄漏。
  - Overlays 场景请添加到 `/root/Main/Overlays`，不要直接挂在 ScreenRoot，避免层级干扰。
- 事件与通信：
  - UI 内部事件：`screen.<name>.<action>` 命名（screen.start.loaded / screen.settings.saved）。
  - 领域事件：统一走 `/root/EventBus`，UI 层仅转换语义并发布。
- 模板（C#）：
```csharp
// Game.Godot/Scripts/Screens/MyScreen.cs
using Godot;
namespace Game.Godot.Scripts.Screens;
public partial class MyScreen : Control
{
    public override void _Ready() { GD.Print("[MyScreen] _Ready"); }
    public void Enter() => GD.Print("[MyScreen] Enter");
    public void Exit()  => GD.Print("[MyScreen] Exit");
}
```
- 模板（.tscn）：
```ini
[gd_scene load_steps=2 format=3]
[ext_resource type="Script" path="res://Game.Godot/Scripts/Screens/MyScreen.cs" id="1"]
[node name="MyScreen" type="Control"]
script = ExtResource("1")
```
- 脚手架：`./scripts/scaffold/new_screen.ps1 -Name MyScreen`（已包含 Enter/Exit 钩子）。

