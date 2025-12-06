# Phase 9: CloudEvents → Godot Signals 迁移

> 状态: 设计阶段
> 预估工时: 5-7 天
> 风险等级: 中
> 前置条件: Phase 1-8 完成

---

## 目标

将 vitegame 的 CloudEvents 事件系统迁移到 godotgame 的 Godot Signals，建立类型安全的信号架构与跨场景通信模式。

---

## 技术栈对比

## 事件命名规范（Godot 变体）

### 事件类别与命名规则

* UI 菜单事件：`ui.menu.<action>`
  - 示例：`ui.menu.start`、`ui.menu.settings`、`ui.menu.quit`
  - 用途：从 MainMenu/Settings 等 UI 按钮发出命令型事件，由 Main.gd 或其他 Glue 逻辑消费。
* Screen 事件：`screen.<name>.<action>`
  - 示例：`screen.start.loaded`、`screen.settings.saved`
  - 用途：描述 Screen 生命周期或关键操作（加载完成、保存成功等），通常由 Screen 自身发送，供上层 Glue/诊断使用。
* 领域事件：`core.<entity>.<action>`（推荐）
  - 示例：`core.score.updated`、`core.health.updated`、`core.game.started`
  - 用途：表达领域层状态变化，通常由 Game.Core 服务通过 IEventBus 发布，再由 Godot 适配层转为 Signal。
* Demo/示例事件：`demo.<name>`
  - 示例：`demo.event`
  - 用途：模板演示用事件，不建议在实际业务中使用 `demo.*` 命名。

> 说明：现有模板中同时存在 `game.started` / `score.changed` 等旧命名以及 `core.score.updated` 等新命名。对于新项目，请优先使用 `core.*.*` 作为领域事件命名，旧命名保留为示例与兼容。
> 规范：**新增或调整的事件命名必须使用 `core.*.*` / `ui.menu.*` / `screen.*.*` 三种前缀之一。旧的 `game.*` / `score.changed` 等事件仅作为历史示例和兼容保留，不再扩展。**

### 旧规范事件（兼容层）

当前仓库中仍保留少量早期事件命名，仅用于兼容和示例，不再作为推荐口径：

| 事件类型 | 使用位置 | 建议 |
| --- | --- | --- |
| game.started | Game.Core.Tests/Engine/GameEngineCoreEventTests.cs:58 | 迁移目标：`core.game.started` |
| score.changed | Game.Core.Tests/Engine/GameEngineCoreEventTests.cs:74 | 迁移目标：`core.score.updated` |
| player.health.changed | Game.Core.Tests/Engine/GameEngineCoreEventTests.cs:90 | 迁移目标：`core.player.health.updated` |

- 这些事件目前只出现在测试代码中，不影响运行时代码；
- 新增业务事件一律使用 `core.*.*` / `ui.menu.*` / `screen.*.*` 三类前缀；
- 将旧事件重命名为新规范事件的工作记录在 Phase-9 Backlog 中，不在本次 Phase 9 P0 范围内完成。

### 最小字段与 CloudEvents 对齐

- 最小字段集合：
  - `type`：事件类型（遵循上面的命名规则）；
  - `source`：事件来源（如 `GameEngineCore`、`MainMenu`）；
  - `data`：与业务相关的 JSON 或对象；
  - `time`：UTC 时间戳（ISO8601）；
  - `id`：全局唯一标识（GUID）。
- 在 C# 中由 `DomainEvent` 承载上述信息；
- 在 Godot 中，由 `EventBusAdapter` 将 `DomainEvent` 序列化为 `DomainEventEmitted(type, source, dataJson, id, specVersion, dataContentType, timestampIso)` Signal。

---

## Godot EventBusAdapter 用法（Publish / Subscribe）

### Publish 路径

- 领域层（Game.Core）：
  - 通过 IEventBus.PublishAsync(DomainEvent) 发送事件；
  - 事件命名遵守 ADR‑0004 / 本 Phase 命名规范。
- Godot 适配层（EventBusAdapter）：
  - 实现 IEventBus 接口；
  - 在 PublishAsync 中：
    - 若 Data 为 string，则直接作为 JSON 使用（空字符串退化为 `{}`）；
    - 否则使用 `System.Text.Json.JsonSerializer.Serialize(Data)` 序列化；
    - EmitSignal `DomainEventEmitted`，供 GDScript 订阅。
- GDScript/测试：
  - 优先通过 `EventBusAdapter.PublishSimple(type, source, data_json)` 发送简单事件，避免在 GDScript 中构造 DomainEvent；
  - 订阅 `/root/EventBus` 的 `DomainEventEmitted`，根据 `type` 和 `dataJson` 做 UI 更新或断言。

### Subscribe 路径

- C# 内部订阅：
  - 通过 `IEventBus.Subscribe(Func<DomainEvent, Task> handler)` 订阅领域事件；
  - 适用于需要统一收集日志、埋点或跨模块协调的场景。
- GDScript 订阅：
  - 在场景/节点中：
    - `var bus = get_node_or_null("/root/EventBus")`
    - `bus.connect("DomainEventEmitted", Callable(self, "_on_domain_event"))`
  - 在 `_on_domain_event(type, source, data_json, id, spec, content_type, ts)` 中，按 `type` 做分支处理：
    - 如 `core.score.updated` 更新 HUD 文本；
    - 如 `ui.menu.start` 触发 ScreenNavigator 切换。

---



| 功能 | vitegame (CloudEvents) | godotgame (Godot Signals) |
|-----|----------------------|--------------------------|
| 事件定义 | TypeScript 接口 + CloudEvent<T> | C# [Signal] delegate |
| 事件发射 | eventBus.publish() | EmitSignal() |
| 事件订阅 | eventBus.subscribe() | Connect() |
| 参数传递 | CloudEvent data 字段 | Signal 方法参数 |
| 类型安全 | TypeScript 泛型 | C# Delegate 签名 |
| 解耦模式 | EventBus 中介 | Direct Signals + EventBus |
| 跨场景通信 | 全局 EventBus | Autoload EventBus + Signals |

---

## CloudEvents 规范回顾 (vitegame)

### CloudEvents 结构

```typescript
// src/shared/contracts/events.ts

import type { CloudEvent } from 'cloudevents';

// 基础事件结构
interface CeBase {
  specversion: '1.0';
  id: string;
  source: string;
  type: string;
  time: string;
  datacontenttype?: string;
}

// 泛型 CloudEvent
type AppEvent<T> = CloudEvent<T>;

// 具体事件示例
interface PlayerDamagedData {
  playerId: string;
  damage: number;
  remainingHealth: number;
  damageSource: string;
}

type PlayerDamagedEvent = AppEvent<PlayerDamagedData>;

// 工厂函数
export function createPlayerDamagedEvent(
  data: PlayerDamagedData
): PlayerDamagedEvent {
  return {
    specversion: '1.0',
    id: crypto.randomUUID(),
    source: 'https://app.game.local/player-service',
    type: 'app.player.damaged',
    time: new Date().toISOString(),
    data,
  };
}
```

### EventBus 使用 (vitegame)

```typescript
// src/services/EventBus.ts

class EventBus {
  private handlers = new Map<string, Set<(event: CloudEvent<any>) => void>>();

  subscribe<T>(eventType: string, handler: (event: CloudEvent<T>) => void): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);

    // 返回取消订阅函数
    return () => this.unsubscribe(eventType, handler);
  }

  publish<T>(event: CloudEvent<T>): void {
    const handlers = this.handlers.get(event.type);
    if (handlers) {
      handlers.forEach(handler => handler(event));
    }
  }

  unsubscribe<T>(eventType: string, handler: (event: CloudEvent<T>) => void): void {
    this.handlers.get(eventType)?.delete(handler);
  }
}

export const eventBus = new EventBus();
```

### 使用示例 (vitegame)

```typescript
// src/entities/Player.ts

import { eventBus } from '@/services/EventBus';
import { createPlayerDamagedEvent } from '@/shared/contracts/events';

export class Player {
  private health: number;

  constructor(maxHealth: number) {
    this.health = maxHealth;

    // 订阅伤害事件
    eventBus.subscribe('app.player.damaged', (event) => {
      console.log(`Player damaged: ${event.data.damage} damage`);
    });
  }

  takeDamage(amount: number, source: string): void {
    this.health -= amount;

    // 发布事件
    const event = createPlayerDamagedEvent({
      playerId: this.id,
      damage: amount,
      remainingHealth: this.health,
      damageSource: source,
    });

    eventBus.publish(event);
  }
}
```

---

## Godot Signals 核心概念

### Signal 定义方式

```csharp
// Game.Godot/Scripts/PlayerController.cs

using Godot;

namespace Game.Godot.Scripts;

public partial class PlayerController : CharacterBody2D
{
    // 方式 1: 无参数信号
    [Signal]
    public delegate void DeathEventHandler();

    // 方式 2: 单参数信号
    [Signal]
    public delegate void HealthChangedEventHandler(int newHealth);

    // 方式 3: 多参数信号
    [Signal]
    public delegate void DamagedEventHandler(int damage, string source, int remainingHealth);

    // 方式 4: 复杂参数信号（使用类）
    [Signal]
    public delegate void StateChangedEventHandler(PlayerState oldState, PlayerState newState);

    private int _health = 100;
    private int _maxHealth = 100;

    public void TakeDamage(int amount, string source)
    {
        int oldHealth = _health;
        _health = Mathf.Max(0, _health - amount);

        // 发射信号（方式 1：命名参数）
        EmitSignal(SignalName.Damaged, amount, source, _health);

        // 发射信号（方式 2：字符串名称）
        // EmitSignal("damaged", amount, source, _health);

        // 发射信号（方式 3：nameof）
        // EmitSignal(nameof(Damaged), amount, source, _health);

        // 健康值变化信号
        if (_health != oldHealth)
        {
            EmitSignal(SignalName.HealthChanged, _health);
        }

        // 死亡信号
        if (_health == 0)
        {
            EmitSignal(SignalName.Death);
        }
    }

    public void Heal(int amount)
    {
        int oldHealth = _health;
        _health = Mathf.Min(_maxHealth, _health + amount);

        if (_health != oldHealth)
        {
            EmitSignal(SignalName.HealthChanged, _health);
        }
    }
}
```

### Signal 连接方式

```csharp
// Game.Godot/Scripts/HealthBarUI.cs

using Godot;

namespace Game.Godot.Scripts;

public partial class HealthBarUI : Control
{
    private ProgressBar _progressBar = null!;
    private Label _healthLabel = null!;
    private PlayerController _player = null!;

    public override void _Ready()
    {
        _progressBar = GetNode<ProgressBar>("ProgressBar");
        _healthLabel = GetNode<Label>("HealthLabel");
        _player = GetNode<PlayerController>("/root/Main/Player");

        // 方式 1: 直接连接到方法（推荐）
        _player.HealthChanged += OnPlayerHealthChanged;

        // 方式 2: 使用 Callable.From 包装 Lambda
        _player.Damaged += Callable.From<int, string, int>((damage, source, remaining) =>
        {
            GD.Print($"Player took {damage} damage from {source}");
            AnimateDamage();
        });

        // 方式 3: 使用 Connect 方法（字符串名称）
        _player.Connect(PlayerController.SignalName.Death, Callable.From(OnPlayerDeath));

        // 方式 4: 使用 Connect 方法（带 flags）
        _player.Connect(
            PlayerController.SignalName.StateChanged,
            Callable.From<PlayerState, PlayerState>(OnPlayerStateChanged),
            (uint)ConnectFlags.OneShot // 一次性连接
        );
    }

    private void OnPlayerHealthChanged(int newHealth)
    {
        _progressBar.Value = newHealth;
        _healthLabel.Text = $"{newHealth}/{_player.MaxHealth}";
    }

    private void OnPlayerDeath()
    {
        GD.Print("Player has died!");
        GetTree().ChangeSceneToFile("res://Scenes/GameOver.tscn");
    }

    private void OnPlayerStateChanged(PlayerState oldState, PlayerState newState)
    {
        GD.Print($"Player state changed: {oldState} -> {newState}");
    }

    private void AnimateDamage()
    {
        // 伤害闪烁动画
        var tween = CreateTween();
        tween.TweenProperty(_progressBar, "modulate", Colors.Red, 0.1);
        tween.TweenProperty(_progressBar, "modulate", Colors.White, 0.1);
    }

    public override void _ExitTree()
    {
        // 断开信号连接（防止内存泄漏）
        if (IsInstanceValid(_player))
        {
            _player.HealthChanged -= OnPlayerHealthChanged;
        }
    }
}
```

### Signal 与方法调用的选择

| 场景 | 使用 Signal | 使用方法调用 |
|-----|-----------|------------|
| 父节点调用子节点 | 否 | 是（直接调用） |
| 子节点通知父节点 | 是 | 否（违反依赖方向） |
| 同级节点通信 | 是 | [警告]（需通过共同父节点） |
| 跨场景通信 | 是（通过 EventBus） | 否 |
| 一对多通知 | 是 | 否 |
| 解耦模块 | 是 | 否 |
| 性能关键路径 | [警告]（有开销） | 是 |

---

## CloudEvents → Signals 迁移模式

### 模式 1: 简单事件迁移

**CloudEvents (vitegame)**:

```typescript
// 事件定义
interface CoinCollectedData {
  coinId: string;
  value: number;
}

type CoinCollectedEvent = AppEvent<CoinCollectedData>;

// 发布事件
eventBus.publish(createCoinCollectedEvent({ coinId: '123', value: 10 }));

// 订阅事件
eventBus.subscribe('app.game.coin.collected', (event) => {
  score += event.data.value;
});
```

**Godot Signals (godotgame)**:

```csharp
// Game.Godot/Scripts/Coin.cs

public partial class Coin : Area2D
{
    [Signal]
    public delegate void CollectedEventHandler(string coinId, int value);

    [Export]
    public string CoinId { get; set; } = Guid.NewGuid().ToString();

    [Export]
    public int Value { get; set; } = 10;

    public override void _Ready()
    {
        BodyEntered += OnBodyEntered;
    }

    private void OnBodyEntered(Node2D body)
    {
        if (body is PlayerController)
        {
            // 发射信号
            EmitSignal(SignalName.Collected, CoinId, Value);
            QueueFree();
        }
    }
}

// Game.Godot/Scripts/ScoreManager.cs

public partial class ScoreManager : Node
{
    private int _score = 0;

    public override void _Ready()
    {
        // 订阅所有金币的收集信号
        var coins = GetTree().GetNodesInGroup("coins");
        foreach (Node coin in coins)
        {
            if (coin is Coin coinScript)
            {
                coinScript.Collected += OnCoinCollected;
            }
        }
    }

    private void OnCoinCollected(string coinId, int value)
    {
        _score += value;
        GD.Print($"Coin collected: {coinId}, Total score: {_score}");
    }
}
```

### 模式 2: 复杂事件数据迁移

**CloudEvents (vitegame)**:

```typescript
// 复杂事件数据
interface EnemyDefeatedData {
  enemyId: string;
  enemyType: string;
  position: { x: number; y: number };
  rewards: {
    experience: number;
    gold: number;
    items: string[];
  };
  killedBy: string;
}

type EnemyDefeatedEvent = AppEvent<EnemyDefeatedData>;

// 发布
eventBus.publish(createEnemyDefeatedEvent({
  enemyId: 'enemy-123',
  enemyType: 'goblin',
  position: { x: 100, y: 200 },
  rewards: { experience: 50, gold: 25, items: ['sword'] },
  killedBy: 'player-456',
}));
```

**Godot Signals (godotgame)**:

```csharp
// Game.Godot/Scripts/EnemyRewards.cs

public class EnemyRewards
{
    public int Experience { get; set; }
    public int Gold { get; set; }
    public List<string> Items { get; set; } = new();
}

// Game.Godot/Scripts/Enemy.cs

public partial class Enemy : CharacterBody2D
{
    [Signal]
    public delegate void DefeatedEventHandler(
        string enemyId,
        string enemyType,
        Vector2 position,
        EnemyRewards rewards,
        string killedBy
    );

    [Export]
    public string EnemyId { get; set; } = Guid.NewGuid().ToString();

    [Export]
    public string EnemyType { get; set; } = "goblin";

    [Export]
    public int Experience { get; set; } = 50;

    [Export]
    public int Gold { get; set; } = 25;

    private int _health = 100;

    public void TakeDamage(int amount, string attackerId)
    {
        _health -= amount;

        if (_health <= 0)
        {
            // 构造奖励数据
            var rewards = new EnemyRewards
            {
                Experience = Experience,
                Gold = Gold,
                Items = new List<string> { "sword" }
            };

            // 发射信号
            EmitSignal(SignalName.Defeated, EnemyId, EnemyType, Position, rewards, attackerId);
            QueueFree();
        }
    }
}

// Game.Godot/Scripts/RewardManager.cs

public partial class RewardManager : Node
{
    public override void _Ready()
    {
        var enemies = GetTree().GetNodesInGroup("enemies");
        foreach (Node enemy in enemies)
        {
            if (enemy is Enemy enemyScript)
            {
                enemyScript.Defeated += OnEnemyDefeated;
            }
        }
    }

    private void OnEnemyDefeated(
        string enemyId,
        string enemyType,
        Vector2 position,
        EnemyRewards rewards,
        string killedBy
    )
    {
        GD.Print($"Enemy {enemyId} ({enemyType}) defeated at {position}");
        GD.Print($"Rewards: {rewards.Experience} XP, {rewards.Gold} gold");

        // 应用奖励到玩家
        var player = GetNode<PlayerController>($"/root/Main/Players/{killedBy}");
        if (player != null)
        {
            player.AddExperience(rewards.Experience);
            player.AddGold(rewards.Gold);
        }
    }
}
```

### 模式 3: EventBus 跨场景通信

**CloudEvents EventBus (vitegame)**:

```typescript
// 全局事件总线
export const globalEventBus = new EventBus();

// 场景 A 发布
globalEventBus.publish(createGameStateChangedEvent({ state: 'paused' }));

// 场景 B 订阅
globalEventBus.subscribe('app.game.state.changed', (event) => {
  console.log('Game state:', event.data.state);
});
```

**Godot EventBus Autoload (godotgame)**:

```csharp
// Game.Godot/Autoloads/EventBus.cs

using Godot;
using System;
using System.Collections.Generic;

namespace Game.Godot.Autoloads;

/// <summary>
/// 全局事件总线（Autoload 单例）
/// 用于跨场景通信和松耦合
/// </summary>
public partial class EventBus : Node
{
    public static EventBus Instance { get; private set; } = null!;

    // 游戏状态事件
    [Signal]
    public delegate void GameStateChangedEventHandler(string newState);

    // 玩家全局事件
    [Signal]
    public delegate void PlayerLevelUpEventHandler(string playerId, int newLevel);

    // 成就解锁事件
    [Signal]
    public delegate void AchievementUnlockedEventHandler(string achievementId, string title);

    // 系统通知事件
    [Signal]
    public delegate void SystemNotificationEventHandler(string message, string severity);

    public override void _EnterTree()
    {
        Instance = this;
    }

    // 辅助方法：发布游戏状态变化
    public void PublishGameStateChanged(string newState)
    {
        EmitSignal(SignalName.GameStateChanged, newState);
    }

    // 辅助方法：发布玩家升级
    public void PublishPlayerLevelUp(string playerId, int newLevel)
    {
        EmitSignal(SignalName.PlayerLevelUp, playerId, newLevel);
    }

    // 辅助方法:发布成就解锁
    public void PublishAchievementUnlocked(string achievementId, string title)
    {
        EmitSignal(SignalName.AchievementUnlocked, achievementId, title);
    }

    // 辅助方法:发布系统通知
    public void PublishSystemNotification(string message, string severity = "info")
    {
        EmitSignal(SignalName.SystemNotification, message, severity);
    }
}
```

**在 project.godot 中注册**:

```ini
[autoload]

EventBus="*res://Autoloads/EventBus.cs"
ServiceLocator="*res://Autoloads/ServiceLocator.cs"
```

**使用 EventBus**:

```csharp
// Game.Godot/Scripts/GameStateManager.cs

public partial class GameStateManager : Node
{
    private string _currentState = "playing";

    public void PauseGame()
    {
        _currentState = "paused";
        GetTree().Paused = true;

        // 通过 EventBus 发布全局事件
        EventBus.Instance.PublishGameStateChanged("paused");
    }

    public void ResumeGame()
    {
        _currentState = "playing";
        GetTree().Paused = false;

        EventBus.Instance.PublishGameStateChanged("playing");
    }
}

// Game.Godot/Scripts/UI/PauseMenuUI.cs

public partial class PauseMenuUI : Control
{
    public override void _Ready()
    {
        // 订阅 EventBus 全局事件
        EventBus.Instance.GameStateChanged += OnGameStateChanged;
    }

    private void OnGameStateChanged(string newState)
    {
        Visible = (newState == "paused");
        GD.Print($"Pause menu visibility: {Visible}");
    }

    public override void _ExitTree()
    {
        EventBus.Instance.GameStateChanged -= OnGameStateChanged;
    }
}

// Game.Godot/Scripts/UI/NotificationManager.cs

public partial class NotificationManager : Control
{
    private Label _notificationLabel = null!;

    public override void _Ready()
    {
        _notificationLabel = GetNode<Label>("NotificationLabel");

        // 订阅系统通知
        EventBus.Instance.SystemNotification += OnSystemNotification;
        EventBus.Instance.AchievementUnlocked += OnAchievementUnlocked;
    }

    private void OnSystemNotification(string message, string severity)
    {
        _notificationLabel.Text = message;
        _notificationLabel.Modulate = severity switch
        {
            "error" => Colors.Red,
            "warning" => Colors.Yellow,
            _ => Colors.White
        };

        ShowNotification();
    }

    private void OnAchievementUnlocked(string achievementId, string title)
    {
        _notificationLabel.Text = $"Achievement Unlocked: {title}";
        _notificationLabel.Modulate = Colors.Gold;
        ShowNotification();
    }

    private async void ShowNotification()
    {
        _notificationLabel.Visible = true;
        await ToSignal(GetTree().CreateTimer(3.0), Timer.SignalName.Timeout);
        _notificationLabel.Visible = false;
    }

    public override void _ExitTree()
    {
        EventBus.Instance.SystemNotification -= OnSystemNotification;
        EventBus.Instance.AchievementUnlocked -= OnAchievementUnlocked;
    }
}
```

---

## Signal 性能优化

### 优化 1: 避免频繁的 Connect/Disconnect

```csharp
// FAIL 错误：每帧都连接和断开
public override void _Process(double delta)
{
    _player.HealthChanged += OnHealthChanged;
    // ... 处理逻辑
    _player.HealthChanged -= OnHealthChanged;
}

// 正确：在 _Ready 和 _ExitTree 中管理连接
public override void _Ready()
{
    _player.HealthChanged += OnHealthChanged;
}

public override void _ExitTree()
{
    if (IsInstanceValid(_player))
    {
        _player.HealthChanged -= OnHealthChanged;
    }
}
```

### 优化 2: 使用 OneShot 连接（一次性事件）

```csharp
// 一次性连接（自动断开）
_enemy.Defeated += Callable.From(() =>
{
    GD.Print("Enemy defeated once!");
});
_enemy.Connect(
    Enemy.SignalName.Defeated,
    Callable.From(OnEnemyDefeated),
    (uint)ConnectFlags.OneShot
);
```

### 优化 3: 使用 Deferred 延迟处理

```csharp
// 延迟到空闲帧处理（避免在物理帧中修改场景树）
_player.Connect(
    PlayerController.SignalName.Death,
    Callable.From(OnPlayerDeath),
    (uint)ConnectFlags.Deferred
);

private void OnPlayerDeath()
{
    // 此方法会在空闲帧调用，安全地修改场景树
    GetTree().ChangeSceneToFile("res://Scenes/GameOver.tscn");
}
```

### 优化 4: 避免过多参数传递

```csharp
// FAIL 错误：传递过多参数
[Signal]
public delegate void ComplexEventEventHandler(
    string id, string name, int value, float time, Vector2 pos, Vector2 vel, Color color, bool flag
);

// 正确：使用数据类
public class EventData
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public int Value { get; set; }
    public float Time { get; set; }
    public Vector2 Position { get; set; }
    public Vector2 Velocity { get; set; }
    public Color Color { get; set; }
    public bool Flag { get; set; }
}

[Signal]
public delegate void ComplexEventEventHandler(EventData data);
```

---

## Signal 命名约定

### 命名规则

```csharp
// 1. 事件名称：PascalCase + 动词过去式
[Signal]
public delegate void HealthChangedEventHandler(int newHealth);

[Signal]
public delegate void DamagedEventHandler(int amount);

[Signal]
public delegate void StateEnteredEventHandler(string stateName);

// 2. Handler 后缀：EventHandler
public delegate void CollectedEventHandler(string itemId);

// 3. 信号参数：描述性命名
[Signal]
public delegate void ItemPickedUpEventHandler(string itemId, string itemName, int quantity);

// 4. 布尔状态变化：使用 Toggled/Changed
[Signal]
public delegate void VisibilityToggledEventHandler(bool isVisible);

[Signal]
public delegate void EnabledChangedEventHandler(bool isEnabled);

// 5. 生命周期事件：使用动作词
[Signal]
public delegate void SpawnedEventHandler();

[Signal]
public delegate void DestroyedEventHandler();

[Signal]
public delegate void InitializedEventHandler();
```

### 事件类型分类

```csharp
// Game.Godot/Scripts/EventCategories.cs

namespace Game.Godot.Scripts;

/// <summary>
/// 玩家相关事件
/// </summary>
public partial class PlayerEvents
{
    [Signal] public delegate void HealthChangedEventHandler(int newHealth);
    [Signal] public delegate void DamagedEventHandler(int damage, string source);
    [Signal] public delegate void HealedEventHandler(int amount);
    [Signal] public delegate void DeathEventHandler();
    [Signal] public delegate void RespawnedEventHandler(Vector2 position);
    [Signal] public delegate void LevelUpEventHandler(int newLevel);
    [Signal] public delegate void ExperienceGainedEventHandler(int amount);
}

/// <summary>
/// 游戏状态事件
/// </summary>
public partial class GameStateEvents
{
    [Signal] public delegate void GameStartedEventHandler();
    [Signal] public delegate void GamePausedEventHandler();
    [Signal] public delegate void GameResumedEventHandler();
    [Signal] public delegate void GameOverEventHandler(int finalScore);
    [Signal] public delegate void LevelCompletedEventHandler(int levelId);
}

/// <summary>
/// 物品/背包事件
/// </summary>
public partial class InventoryEvents
{
    [Signal] public delegate void ItemAddedEventHandler(string itemId, int quantity);
    [Signal] public delegate void ItemRemovedEventHandler(string itemId, int quantity);
    [Signal] public delegate void ItemUsedEventHandler(string itemId);
    [Signal] public delegate void InventoryFullEventHandler();
}

/// <summary>
/// UI 事件
/// </summary>
public partial class UIEvents
{
    [Signal] public delegate void ButtonClickedEventHandler(string buttonName);
    [Signal] public delegate void MenuOpenedEventHandler(string menuName);
    [Signal] public delegate void MenuClosedEventHandler(string menuName);
    [Signal] public delegate void DialogueStartedEventHandler(string dialogueId);
    [Signal] public delegate void DialogueCompletedEventHandler(string dialogueId);
}
```

---

## Signal 测试策略

### GdUnit4 Signal 测试

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

### xUnit Signal 测试（使用 Fake）

```csharp
// Game.Core.Tests/Fakes/FakeSignalEmitter.cs

using System;
using System.Collections.Generic;

namespace Game.Core.Tests.Fakes;

public class FakeSignalEmitter
{
    private Dictionary<string, List<Delegate>> _handlers = new();

    public void Connect(string signalName, Delegate handler)
    {
        if (!_handlers.ContainsKey(signalName))
        {
            _handlers[signalName] = new List<Delegate>();
        }
        _handlers[signalName].Add(handler);
    }

    public void Disconnect(string signalName, Delegate handler)
    {
        _handlers[signalName]?.Remove(handler);
    }

    public void Emit(string signalName, params object[] args)
    {
        if (_handlers.ContainsKey(signalName))
        {
            foreach (var handler in _handlers[signalName])
            {
                handler.DynamicInvoke(args);
            }
        }
    }
}

// Game.Core.Tests/Signals/PlayerSignalTests.cs

using FluentAssertions;
using Game.Core.Tests.Fakes;
using Xunit;

namespace Game.Core.Tests.Signals;

public class PlayerSignalTests
{
    [Fact]
    public void HealthChanged_ShouldEmitCorrectValue()
    {
        // Arrange
        var emitter = new FakeSignalEmitter();
        int receivedHealth = 0;

        emitter.Connect("health_changed", (int newHealth) =>
        {
            receivedHealth = newHealth;
        });

        // Act
        emitter.Emit("health_changed", 75);

        // Assert
        receivedHealth.Should().Be(75);
    }

    [Fact]
    public void Damaged_ShouldEmitAllParameters()
    {
        // Arrange
        var emitter = new FakeSignalEmitter();
        int receivedDamage = 0;
        string receivedSource = string.Empty;
        int receivedRemaining = 0;

        emitter.Connect("damaged", (int damage, string source, int remaining) =>
        {
            receivedDamage = damage;
            receivedSource = source;
            receivedRemaining = remaining;
        });

        // Act
        emitter.Emit("damaged", 30, "enemy", 70);

        // Assert
        receivedDamage.Should().Be(30);
        receivedSource.Should().Be("enemy");
        receivedRemaining.Should().Be(70);
    }

    [Fact]
    public void MultipleSubscribers_ShouldAllReceiveSignal()
    {
        // Arrange
        var emitter = new FakeSignalEmitter();
        int subscriber1Count = 0;
        int subscriber2Count = 0;

        emitter.Connect("test_signal", () => subscriber1Count++);
        emitter.Connect("test_signal", () => subscriber2Count++);

        // Act
        emitter.Emit("test_signal");
        emitter.Emit("test_signal");

        // Assert
        subscriber1Count.Should().Be(2);
        subscriber2Count.Should().Be(2);
    }

    [Fact]
    public void Disconnect_ShouldStopReceivingSignals()
    {
        // Arrange
        var emitter = new FakeSignalEmitter();
        int callCount = 0;
        Action handler = () => callCount++;

        emitter.Connect("test_signal", handler);

        // Act
        emitter.Emit("test_signal");
        emitter.Disconnect("test_signal", handler);
        emitter.Emit("test_signal");

        // Assert
        callCount.Should().Be(1);
    }
}
```

---

## Signal 文档化

### XML 文档注释

```csharp
// Game.Godot/Scripts/PlayerController.cs

namespace Game.Godot.Scripts;

public partial class PlayerController : CharacterBody2D
{
    /// <summary>
    /// 当玩家生命值发生变化时发射。
    /// </summary>
    /// <param name="newHealth">新的生命值（0 到 MaxHealth）</param>
    /// <example>
    /// <code>
    /// player.HealthChanged += (newHealth) => {
    ///     GD.Print($"Player health: {newHealth}");
    /// };
    /// </code>
    /// </example>
    [Signal]
    public delegate void HealthChangedEventHandler(int newHealth);

    /// <summary>
    /// 当玩家受到伤害时发射（在 HealthChanged 之前）。
    /// </summary>
    /// <param name="damage">伤害数值</param>
    /// <param name="source">伤害来源（如 "enemy", "trap", "fall"）</param>
    /// <param name="remainingHealth">剩余生命值</param>
    /// <remarks>
    /// 此信号适用于播放伤害音效、显示伤害数字、触发受击动画等。
    /// </remarks>
    [Signal]
    public delegate void DamagedEventHandler(int damage, string source, int remainingHealth);

    /// <summary>
    /// 当玩家死亡时发射（生命值降至 0）。
    /// </summary>
    /// <remarks>
    /// 此信号只会在生命值首次降至 0 时发射一次。
    /// 适用于触发死亡动画、显示游戏结束界面、记录死亡统计等。
    /// </remarks>
    [Signal]
    public delegate void DeathEventHandler();

    /// <summary>
    /// 当玩家状态发生变化时发射（如 Idle → Running → Jumping）。
    /// </summary>
    /// <param name="oldState">旧状态</param>
    /// <param name="newState">新状态</param>
    /// <example>
    /// <code>
    /// player.StateChanged += (oldState, newState) => {
    ///     GD.Print($"Player state: {oldState} -> {newState}");
    ///     AnimationPlayer.Play(newState.ToString());
    /// };
    /// </code>
    /// </example>
    [Signal]
    public delegate void StateChangedEventHandler(PlayerState oldState, PlayerState newState);
}
```

---

## 迁移检查清单

### 事件定义迁移

- [ ] CloudEvents 类型定义 → [Signal] delegate 定义
- [ ] CloudEvent<T> 数据结构 → Signal 参数列表
- [ ] 事件工厂函数 → EmitSignal() 调用
- [ ] 事件命名规范（app.entity.action → EntityActionEventHandler）

### 事件发射迁移

- [ ] eventBus.publish() → EmitSignal(SignalName.XXX, ...)
- [ ] 事件参数序列化 → 直接传递参数（或使用数据类）
- [ ] 事件源 (source) → 隐式（通过发射节点）或显式传递

### 事件订阅迁移

- [ ] eventBus.subscribe() → signal += handler
- [ ] 订阅取消 (unsubscribe) → signal -= handler
- [ ] 订阅生命周期管理（_Ready 订阅，_ExitTree 取消）

### EventBus 迁移

- [ ] 全局 EventBus → Autoload EventBus.cs
- [ ] 跨场景事件 → EventBus.Instance.XXXChanged 信号
- [ ] EventBus.publish/subscribe → EventBus.EmitSignal/Connect

### 测试迁移

- [ ] Jest 事件测试 → GdUnit4 GdUnitSignalSpy
- [ ] 测试事件发射 → signal_spy.is_emitted()
- [ ] 测试事件参数 → signal_spy.get_last_args()
- [ ] xUnit 逻辑测试 → FakeSignalEmitter

### 文档迁移

- [ ] CloudEvents 契约文档 → Signal XML 文档注释
- [ ] 事件参数说明 → <param> 标签
- [ ] 使用示例 → <example> 标签

---

## 性能基准

### Signal 性能测试

```csharp
// Game.Godot.Tests/Performance/SignalPerformanceTest.cs

using Godot;
using System.Diagnostics;

namespace Game.Godot.Tests.Performance;

public partial class SignalPerformanceTest : Node
{
    [Signal]
    public delegate void TestSignalEventHandler(int value);

    public override void _Ready()
    {
        // 测试 1: 单订阅者性能
        TestSingleSubscriber();

        // 测试 2: 多订阅者性能
        TestMultipleSubscribers();

        // 测试 3: 参数传递性能
        TestParameterPassing();
    }

    private void TestSingleSubscriber()
    {
        TestSignal += OnTestSignal;

        var sw = Stopwatch.StartNew();
        for (int i = 0; i < 100000; i++)
        {
            EmitSignal(SignalName.TestSignal, i);
        }
        sw.Stop();

        GD.Print($"Single subscriber: {sw.ElapsedMilliseconds}ms for 100k emissions");

        TestSignal -= OnTestSignal;
    }

    private void TestMultipleSubscribers()
    {
        for (int i = 0; i < 10; i++)
        {
            TestSignal += OnTestSignal;
        }

        var sw = Stopwatch.StartNew();
        for (int i = 0; i < 100000; i++)
        {
            EmitSignal(SignalName.TestSignal, i);
        }
        sw.Stop();

        GD.Print($"10 subscribers: {sw.ElapsedMilliseconds}ms for 100k emissions");

        // 清理
        for (int i = 0; i < 10; i++)
        {
            TestSignal -= OnTestSignal;
        }
    }

    private void TestParameterPassing()
    {
        TestSignal += OnTestSignal;

        var sw = Stopwatch.StartNew();
        for (int i = 0; i < 100000; i++)
        {
            EmitSignal(SignalName.TestSignal, i);
        }
        sw.Stop();

        GD.Print($"Parameter passing: {sw.ElapsedMilliseconds}ms for 100k emissions");

        TestSignal -= OnTestSignal;
    }

    private void OnTestSignal(int value)
    {
        // 空处理器
    }
}
```

### 性能阈值

| 场景 | 目标阈值 |
|-----|---------|
| 单订阅者 100k 发射 | < 50ms |
| 10 订阅者 100k 发射 | < 200ms |
| 参数传递 100k 发射 | < 60ms |
| EventBus 全局事件 1k 发射 | < 10ms |

---

## CI 集成

### Signal 合规检查 (GitHub Actions)

```yaml
# .github/workflows/signal-compliance.yml

name: Signal Compliance

on:
  push:
    paths:
      - 'Game.Godot/Scripts/**/*.cs'
      - 'Game.Godot/Autoloads/**/*.cs'
  pull_request:
    paths:
      - 'Game.Godot/Scripts/**/*.cs'
      - 'Game.Godot/Autoloads/**/*.cs'

jobs:
  signal-compliance:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup .NET 8
        uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '8.0.x'

      - name: Check Signal Naming Convention
        shell: pwsh
        run: |
          # 检查 [Signal] 命名是否符合 EventHandler 后缀
          $violations = Select-String -Path "Game.Godot/**/*.cs" -Pattern "\[Signal\].*delegate.*(?<!EventHandler)\(\);" -Encoding UTF8

          if ($violations) {
            Write-Error "Signal naming violations found:"
            $violations | ForEach-Object { Write-Host $_.Line }
            exit 1
          }

      - name: Check Signal Documentation
        shell: pwsh
        run: |
          # 检查 [Signal] 是否有 XML 文档注释
          $files = Get-ChildItem -Path "Game.Godot/Scripts" -Filter "*.cs" -Recurse
          $undocumented = @()

          foreach ($file in $files) {
            $content = Get-Content $file.FullName -Raw
            $signals = [regex]::Matches($content, '\[Signal\][^\r\n]*\r?\n\s*public delegate')

            foreach ($match in $signals) {
              $linesBefore = $content.Substring(0, $match.Index) -split '\r?\n'
              $lastLine = $linesBefore[-1]

              if ($lastLine -notmatch '///\s*<summary>') {
                $undocumented += "$($file.Name): $($match.Value)"
              }
            }
          }

          if ($undocumented.Count -gt 0) {
            Write-Error "Undocumented signals found:"
            $undocumented | ForEach-Object { Write-Host $_ }
            exit 1
          }

      - name: Run Signal Tests
        run: |
          dotnet test Game.Core.Tests/Game.Core.Tests.csproj `
            --filter "FullyQualifiedName~Signal" `
            --verbosity normal
```

---

## 实现与测试范围（当前模板）

- 已覆盖：
  - `GameEngineCore` 关键 DomainEvent 通过 xUnit 用例验证（见下方 Test-Refs）。
  - Godot 侧 `EventBusAdapter` 已通过代表性 GdUnit4 用例验证事件转发和序列化（Adapters/Integration 小集）。
- 未覆盖（刻意暂不处理）：
  - 历史 `game.*` / `score.changed` 事件的全量重命名与迁移。
  - 所有领域服务的 1:1 事件用例（当前模板仅保留代表性样例，留待具体游戏项目按需扩展）。

## Backlog（后续可选优化）

- 逐步将历史 `game.*` 事件迁移为 `core.*.*` 命名，并视需要保留兼容层。
- 为主要领域服务补充成对的 xUnit + GdUnit4 事件测试用例。

## Test-Refs

- `Game.Core.Tests/Engine/GameEngineCoreEventTests.cs`
- `Tests.Godot/tests/Adapters/test_event_bus_adapter.gd`
- `Tests.Godot/tests/Integration/test_settings_event_integration.gd`

## 完成标准

- [ ] 所有 CloudEvents 事件定义已迁移到 [Signal] delegate
- [ ] EventBus Autoload 已创建并在 project.godot 注册
- [ ] 所有事件发射已从 eventBus.publish() 迁移到 EmitSignal()
- [ ] 所有事件订阅已从 eventBus.subscribe() 迁移到 signal += handler
- [ ] 信号命名符合约定（PascalCase + EventHandler 后缀）
- [ ] 所有信号有 XML 文档注释（<summary>, <param>, <example>）
- [ ] GdUnit4 信号测试覆盖主要场景（GdUnitSignalSpy）
- [ ] xUnit 逻辑测试覆盖信号逻辑（FakeSignalEmitter）
- [ ] 信号性能测试达到基准阈值
- [ ] CI 管道包含信号合规检查

---

## 下一步

完成本阶段后,继续:

➡️ [Phase-10-Unit-Tests.md](Phase-10-Unit-Tests.md) — xUnit 单元测试迁移
