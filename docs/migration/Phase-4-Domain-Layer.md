# Phase 4: 纯 C# 领域层迁移

> 状态: 实施阶段
> 预估工时: 10-15 天
> 风险等级: 中
> 前置条件: Phase 1-3 完成

---

## 目标

将 vitegame 的 TypeScript 业务逻辑迁移到 Game.Core 纯 C# 领域层，实现与 Godot 完全解耦，支持 TDD 红绿灯循环。

---

## 迁移策略

### 总体原则

1. **逻辑优先，UI 延后**：先迁移纯逻辑（算法/状态机/服务），UI 在 Phase 7 处理
2. **TDD 驱动**：先写失败的 xUnit 测试，再实现 C# 代码
3. **接口隔离**：所有外部依赖（时间/输入/资源）通过接口注入
4. **不可变优先**：ValueObjects 使用 C# record，Entities 谨慎使用 setter

### 迁移优先级

```
Priority 1 (核心逻辑，无外部依赖)
├─ 数学工具类 (MathHelper, RandomHelper)
├─ 值对象 (Position, Health, Damage)
└─ 实体基础属性 (Player 数据模型)

Priority 2 (领域服务，依赖接口)
├─ 战斗服务 (CombatService)
├─ 碰撞检测 (CollisionService)
└─ 分数计算 (ScoreService)

Priority 3 (复杂状态机)
├─ 游戏状态机 (GameStateMachine)
├─ 玩家状态 (PlayerState)
└─ 敌人 AI (EnemyAI)
```

---

## TypeScript → C# 映射规则

### 基础类型映射

| TypeScript | C# |
|-----------|-----|
| `number` (整数) | `int` / `long` |
| `number` (小数) | `double` / `float` |
| `string` | `string` |
| `boolean` | `bool` |
| `Array<T>` | `List<T>` / `T[]` |
| `Map<K, V>` | `Dictionary<K, V>` |
| `Set<T>` | `HashSet<T>` |
| `{ x: number, y: number }` | `record Position(double X, double Y)` |
| `undefined` / `null` | `T?` (nullable) |

### 类与接口映射

**TypeScript (vitegame)**:

```typescript
// src/domain/entities/Player.ts
export class Player {
  private health: number;
  private maxHealth: number;
  private position: { x: number; y: number };

  constructor(maxHealth: number) {
    this.health = maxHealth;
    this.maxHealth = maxHealth;
    this.position = { x: 0, y: 0 };
  }

  takeDamage(amount: number): void {
    this.health = Math.max(0, this.health - amount);
  }

  isAlive(): boolean {
    return this.health > 0;
  }

  move(dx: number, dy: number): void {
    this.position.x += dx;
    this.position.y += dy;
  }
}
```

**C# (godotgame)**:

```csharp
// Game.Core/Domain/ValueObjects/Position.cs
public record Position(double X, double Y)
{
    public Position Add(double dx, double dy) => new(X + dx, Y + dy);
}

// Game.Core/Domain/ValueObjects/Health.cs
public record Health
{
    public int Current { get; init; }
    public int Maximum { get; init; }

    public Health(int maximum)
    {
        Maximum = maximum;
        Current = maximum;
    }

    public Health TakeDamage(int amount)
    {
        var newCurrent = Math.Max(0, Current - amount);
        return this with { Current = newCurrent };
    }

    public bool IsAlive => Current > 0;
}

// Game.Core/Domain/Entities/Player.cs
public class Player
{
    public Health Health { get; private set; }
    public Position Position { get; private set; }

    public Player(int maxHealth)
    {
        Health = new Health(maxHealth);
        Position = new Position(0, 0);
    }

    public void TakeDamage(int amount)
    {
        Health = Health.TakeDamage(amount);
    }

    public bool IsAlive => Health.IsAlive;

    public void Move(double dx, double dy)
    {
        Position = Position.Add(dx, dy);
    }
}
```

### 异步代码映射

| TypeScript | C# |
|-----------|-----|
| `async function` | `async Task` / `async Task<T>` |
| `await somePromise()` | `await SomeMethodAsync()` |
| `Promise<T>` | `Task<T>` |
| `.then()` | `await` (不推荐 ContinueWith) |
| `.catch()` | `try-catch` |

---

## TDD 工作流示例

### 步骤 1: 红灯（写失败的测试）

```csharp
// Game.Core.Tests/Domain/ValueObjects/HealthTests.cs

using FluentAssertions;
using Game.Core.Domain.ValueObjects;
using Xunit;

namespace Game.Core.Tests.Domain.ValueObjects;

public class HealthTests
{
    [Fact]
    public void New_Health_ShouldHaveFullCurrent()
    {
        // Arrange & Act
        var health = new Health(maximum: 100);

        // Assert
        health.Current.Should().Be(100);
        health.Maximum.Should().Be(100);
        health.IsAlive.Should().BeTrue();
    }

    [Fact]
    public void TakeDamage_ShouldReduceCurrent()
    {
        // Arrange
        var health = new Health(100);

        // Act
        var newHealth = health.TakeDamage(30);

        // Assert
        newHealth.Current.Should().Be(70);
        newHealth.IsAlive.Should().BeTrue();
    }

    [Fact]
    public void TakeDamage_ExceedingCurrent_ShouldClampToZero()
    {
        // Arrange
        var health = new Health(100);

        // Act
        var newHealth = health.TakeDamage(150);

        // Assert
        newHealth.Current.Should().Be(0);
        newHealth.IsAlive.Should().BeFalse();
    }

    [Fact]
    public void TakeDamage_ShouldNotModifyOriginal()
    {
        // Arrange
        var original = new Health(100);

        // Act
        var modified = original.TakeDamage(30);

        // Assert (不可变性)
        original.Current.Should().Be(100);
        modified.Current.Should().Be(70);
    }
}
```

**运行测试（红灯）**:

```powershell
cd Game.Core.Tests
dotnet test

# 预期输出：所有测试失败（Health 类尚未实现）
```

### 步骤 2: 绿灯（实现最小代码）

```csharp
// Game.Core/Domain/ValueObjects/Health.cs

namespace Game.Core.Domain.ValueObjects;

public record Health
{
    public int Current { get; init; }
    public int Maximum { get; init; }

    public Health(int maximum)
    {
        if (maximum < 0)
            throw new ArgumentOutOfRangeException(nameof(maximum));

        Maximum = maximum;
        Current = maximum;
    }

    public Health TakeDamage(int amount)
    {
        if (amount < 0)
            throw new ArgumentOutOfRangeException(nameof(amount));

        var newCurrent = Math.Max(0, Current - amount);
        return this with { Current = newCurrent };
    }

    public bool IsAlive => Current > 0;
}
```

**运行测试（绿灯）**:

```powershell
dotnet test

# 预期输出：所有测试通过
```

### 步骤 3: 重构（改进代码质量）

```csharp
// Game.Core/Domain/ValueObjects/Health.cs (重构版)

namespace Game.Core.Domain.ValueObjects;

/// <summary>
/// 表示生命值的不可变值对象
/// </summary>
public record Health
{
    public int Current { get; init; }
    public int Maximum { get; init; }

    public Health(int maximum)
    {
        ArgumentOutOfRangeException.ThrowIfNegative(maximum, nameof(maximum));

        Maximum = maximum;
        Current = maximum;
    }

    /// <summary>
    /// 承受伤害，返回新的 Health 实例（不可变）
    /// </summary>
    public Health TakeDamage(int amount)
    {
        ArgumentOutOfRangeException.ThrowIfNegative(amount, nameof(amount));

        var newCurrent = Math.Max(0, Current - amount);
        return this with { Current = newCurrent };
    }

    /// <summary>
    /// 治疗，返回新的 Health 实例
    /// </summary>
    public Health Heal(int amount)
    {
        ArgumentOutOfRangeException.ThrowIfNegative(amount, nameof(amount));

        var newCurrent = Math.Min(Maximum, Current + amount);
        return this with { Current = newCurrent };
    }

    public bool IsAlive => Current > 0;
    public bool IsFull => Current == Maximum;
    public double HealthPercentage => Maximum > 0 ? (double)Current / Maximum : 0;
}
```

**再次运行测试**:

```powershell
dotnet test --logger "console;verbosity=detailed"

# 预期输出：所有测试通过，覆盖率 ≥90%
```

---

## 接口隔离示例

### 定义端口接口

```csharp
// Game.Core/Ports/ITime.cs

namespace Game.Core.Ports;

/// <summary>
/// 时间服务接口（隔离 Godot 依赖）
/// </summary>
public interface ITime
{
    /// <summary>
    /// 获取当前时间戳（秒）
    /// </summary>
    double GetTimestamp();

    /// <summary>
    /// 获取上一帧到当前帧的时间间隔（秒）
    /// </summary>
    double GetDeltaTime();
}
```

### 测试用 Fake 实现

```csharp
// Game.Core.Tests/Fakes/FakeTime.cs

namespace Game.Core.Tests.Fakes;

public class FakeTime : ITime
{
    public double CurrentTime { get; set; } = 0;
    public double Delta { get; set; } = 0.016; // 默认 60 FPS

    public double GetTimestamp() => CurrentTime;
    public double GetDeltaTime() => Delta;

    /// <summary>
    /// 模拟时间前进
    /// </summary>
    public void Advance(double seconds)
    {
        CurrentTime += seconds;
    }
}
```

### 使用依赖注入

```csharp
// Game.Core/Domain/Services/CombatService.cs

namespace Game.Core.Domain.Services;

public class CombatService
{
    private readonly ITime _time;

    public CombatService(ITime time)
    {
        _time = time ?? throw new ArgumentNullException(nameof(time));
    }

    public Damage CalculateDamage(int baseDamage, bool isCritical)
    {
        // 使用时间戳作为随机种子（可预测测试）
        var timestamp = _time.GetTimestamp();
        var seed = (int)(timestamp * 1000);
        var random = new Random(seed);

        var multiplier = isCritical ? 2.0 : 1.0;
        var variance = random.NextDouble() * 0.2 - 0.1; // ±10%
        var finalDamage = (int)(baseDamage * multiplier * (1 + variance));

        return new Damage(finalDamage);
    }
}
```

**测试用例**:

```csharp
// Game.Core.Tests/Domain/Services/CombatServiceTests.cs

public class CombatServiceTests
{
    [Fact]
    public void CalculateDamage_WithCritical_ShouldApplyMultiplier()
    {
        // Arrange
        var fakeTime = new FakeTime { CurrentTime = 1.0 };
        var service = new CombatService(fakeTime);

        // Act
        var damage = service.CalculateDamage(baseDamage: 100, isCritical: true);

        // Assert
        damage.Amount.Should().BeInRange(180, 220); // 100 * 2.0 ± 10%
    }

    [Fact]
    public void CalculateDamage_SameTimestamp_ShouldBeDeterministic()
    {
        // Arrange
        var fakeTime = new FakeTime { CurrentTime = 42.0 };
        var service = new CombatService(fakeTime);

        // Act
        var damage1 = service.CalculateDamage(100, false);
        var damage2 = service.CalculateDamage(100, false);

        // Assert (相同时间戳 = 相同结果，可重复测试)
        damage1.Amount.Should().Be(damage2.Amount);
    }
}
```

---

## 迁移检查清单

### 核心值对象（Priority 1）

- [ ] Position (X, Y, Add, Distance)
- [ ] Health (Current, Maximum, TakeDamage, Heal)
- [ ] Damage (Amount, Type, IsCritical)
- [ ] Score (Value, Add, Multiply)
- [ ] ItemQuantity (Count, Add, Subtract)

### 核心实体（Priority 1）

- [ ] Player (Health, Position, Move, TakeDamage)
- [ ] Enemy (Health, Position, AI State, Attack)
- [ ] Item (Id, Type, Quantity, IsUsable)

### 领域服务（Priority 2）

- [ ] CombatService (CalculateDamage, ApplyEffect)
- [ ] CollisionService (CheckCollision, Resolve)
- [ ] ScoreService (CalculateScore, ApplyBonus)
- [ ] InventoryService (AddItem, RemoveItem, UseItem)

### 状态机（Priority 3）

- [ ] GameStateMachine (Idle, Playing, Paused, GameOver)
- [ ] PlayerState (Idle, Moving, Attacking, Dead)
- [ ] EnemyAI (Patrol, Chase, Attack, Retreat)

### 工具类

- [ ] MathHelper (Clamp, Lerp, Distance)
- [ ] RandomHelper (NextInt, NextDouble, Choose)
- [ ] CollectionExtensions (Shuffle, Sample, Partition)

### 覆盖率目标

- [ ] 行覆盖率 ≥90%
- [ ] 分支覆盖率 ≥85%
- [ ] 所有公共方法有测试
- [ ] 边界条件有测试（0, 负数, MAX_VALUE）
- [ ] 异常路径有测试

---

## 代码规范

### 命名约定

```csharp
// 命名空间：PascalCase
namespace Game.Core.Domain.Entities;

// 类/接口：PascalCase
public class Player { }
public interface ITime { }

// 方法：PascalCase
public void TakeDamage(int amount) { }

// 属性：PascalCase
public int Health { get; private set; }

// 字段（私有）：_camelCase
private readonly ITime _time;

// 常量：UPPER_SNAKE_CASE 或 PascalCase
private const int MAX_HEALTH = 100;

// 局部变量：camelCase
var playerHealth = 100;
```

### 不可变性

```csharp
// 推荐：record 实现值对象（不可变）
public record Position(double X, double Y)
{
    public Position Add(double dx, double dy) => new(X + dx, Y + dy);
}

// 推荐：init-only 属性
public class Player
{
    public Health Health { get; init; }
    public Position Position { get; init; }
}

// 避免：可变值对象
public class Position
{
    public double X { get; set; } // 不推荐
    public double Y { get; set; }
}
```

### 异常处理

```csharp
// 推荐：ArgumentException.ThrowIfXXX（.NET 8）
public Health(int maximum)
{
    ArgumentOutOfRangeException.ThrowIfNegative(maximum, nameof(maximum));
    Maximum = maximum;
}

// 推荐：自定义业务异常
public class InvalidGameStateException : Exception
{
    public InvalidGameStateException(string message) : base(message) { }
}

// 避免：捕获所有异常
try
{
    // ...
}
catch (Exception) // 过于宽泛
{
}
```

---

## 性能优化建议

### 使用 Span<T> 避免数组分配

```csharp
// 避免：频繁分配数组
public int SumArray(int[] numbers)
{
    return numbers.Sum();
}

// 推荐：使用 ReadOnlySpan<T>
public int SumSpan(ReadOnlySpan<int> numbers)
{
    int sum = 0;
    foreach (var num in numbers)
    {
        sum += num;
    }
    return sum;
}
```

### 避免 LINQ 过度使用（热路径）

```csharp
// 避免：热路径使用 LINQ（每帧调用）
public Player FindNearestEnemy(List<Enemy> enemies, Position playerPos)
{
    return enemies
        .OrderBy(e => Vector2.Distance(e.Position, playerPos))
        .FirstOrDefault();
}

// 推荐：手动循环（更快）
public Enemy? FindNearestEnemy(List<Enemy> enemies, Position playerPos)
{
    Enemy? nearest = null;
    double minDistance = double.MaxValue;

    foreach (var enemy in enemies)
    {
        var distance = playerPos.DistanceTo(enemy.Position);
        if (distance < minDistance)
        {
            minDistance = distance;
            nearest = enemy;
        }
    }

    return nearest;
}
```

### 对象池模式（避免 GC 压力）

```csharp
// Game.Core/Utilities/ObjectPool.cs

public class ObjectPool<T> where T : new()
{
    private readonly Stack<T> _pool = new();

    public T Rent()
    {
        return _pool.Count > 0 ? _pool.Pop() : new T();
    }

    public void Return(T obj)
    {
        _pool.Push(obj);
    }
}
```

---

## 迁移进度追踪

创建 Python 脚本自动统计迁移进度：

**scripts/python/migration-progress.py**:

```python
import os
from pathlib import Path

def count_cs_files(directory):
    return len(list(Path(directory).rglob('*.cs')))

def count_test_files(directory):
    return len(list(Path(directory).rglob('*Tests.cs')))

def calculate_coverage():
    # 调用 coverlet 生成覆盖率
    os.system('dotnet test --collect:"XPlat Code Coverage" --results-directory ./TestResults')

    # 解析覆盖率报告
    # (实现省略，实际需解析 coverage.cobertura.xml)

if __name__ == '__main__':
    core_files = count_cs_files('Game.Core')
    test_files = count_test_files('Game.Core.Tests')

    print(f"Game.Core 文件数: {core_files}")
    print(f"测试文件数: {test_files}")
    print(f"测试/代码比: {test_files / core_files:.2f}")

    calculate_coverage()
```

---

## 完成标准

- [ ] 所有 Priority 1 值对象与实体迁移完成
- [ ] 所有 Priority 2 领域服务迁移完成
- [ ] xUnit 测试覆盖率 ≥90% 行 / ≥85% 分支
- [ ] `dotnet test` 全部通过
- [ ] 代码通过 `dotnet format analyzers` 检查
- [ ] 无 StyleCop / Roslyn 警告
- [ ] 所有公共 API 有 XML 文档注释

---

## 下一步

完成本阶段后，继续：

➡️ [Phase-5-Adapter-Layer.md](Phase-5-Adapter-Layer.md) — Godot 适配层设计
