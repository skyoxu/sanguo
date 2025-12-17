# Phase 10: Jest → xUnit 单元测试迁移

> 状态: 设计阶段
> 预估工时: 8-12 天
> 风险等级: 中
> 前置条件: Phase 1-9 完成

---

## 目标

将 LegacyProject 的 Jest + TypeScript 单元测试迁移到 godotgame 的 xUnit + C# 单元测试，建立类型安全的测试套件与 AI-first 覆盖率门禁。

---

## 技术栈对比

| 功能 | LegacyProject (Node.js) | godotgame (.NET 8) |
|-----|-------------------|-------------------|
| 测试框架 | Jest 29 | xUnit 2.x |
| 断言库 | Jest expect() | FluentAssertions |
| 测试隔离 | describe/it 嵌套 | [Fact]/[Theory] 扁平 |
| 测试双 | jest.mock / jest.fn | Moq / NSubstitute / Fakes |
| 参数化测试 | test.each() | [Theory] + [InlineData] |
| 生命周期 | beforeEach/afterEach | Constructor/IDisposable |
| 覆盖率 | c8 / istanbul | coverlet |
| 运行器 | jest CLI | dotnet test |
| CI 集成 | NodePkg test | dotnet test --logger trx |

### Godot+C# 变体（Game.Core + xUnit）

- 测试项目：`Game.Core.Tests`（纯 C#，不依赖 Godot 引擎）。
- 框架与工具：xUnit 2.x + FluentAssertions，采用 AAA 模式；需要参数化时使用 `[Theory]` + `[InlineData]`。
- 代表性样板用例：
  - `Domain/ValueObjects/DamageTests.cs`：验证 Damage 值对象的裁剪与 Critical 标志（EffectiveAmount 不为负）。
  - `Engine/GameEngineCoreEventTests.cs`：通过 fake `IEventBus` 捕获 `DomainEvent`，验证事件 Type/Source/Data（如 `game.started`、`score.changed`）。
- CI 集成（Windows）：
  - 通过 `scripts/python/run_dotnet.py` / `scripts/python/ci_pipeline.py` 调用 `dotnet test` 并收集 coverlet 覆盖率；
  - 覆盖率与测试结果落盘至 `logs/unit/<YYYY-MM-DD>/`，具体阈值与门禁见 `docs/testing-framework.md`。

### Test-Refs（当前模板样板用例）

- `Game.Core.Tests/Domain/ValueObjects/DamageTests.cs`
- `Game.Core.Tests/Engine/GameEngineCoreEventTests.cs`
- `Game.Core.Tests/Config/GameConfigTests.cs`（如存在）

覆盖率与测试结果统一输出到 `logs/unit/<YYYY-MM-DD>/summary.json`，作为 Phase 10 与 Phase 13 质量门禁脚本的单一入口数据源。

---

## Jest 测试结构回顾

### 典型 Jest 测试 (LegacyProject)

```typescript
// src/domain/entities/Player.test.ts

import { Player } from './Player';
import { FakeTime } from '@/tests/fakes/FakeTime';

describe('Player', () => {
  let player: Player;
  let fakeTime: FakeTime;

  beforeEach(() => {
    fakeTime = new FakeTime();
    player = new Player(fakeTime);
  });

  describe('constructor', () => {
    it('should initialize with default health', () => {
      expect(player.health).toBe(100);
      expect(player.maxHealth).toBe(100);
    });

    it('should initialize at position (0, 0)', () => {
      expect(player.position).toEqual({ x: 0, y: 0 });
    });
  });

  describe('takeDamage', () => {
    it('should reduce health by damage amount', () => {
      player.takeDamage(30);
      expect(player.health).toBe(70);
    });

    it('should not reduce health below zero', () => {
      player.takeDamage(150);
      expect(player.health).toBe(0);
    });

    it('should emit damaged event', () => {
      const mockHandler = jest.fn();
      player.on('damaged', mockHandler);

      player.takeDamage(20);

      expect(mockHandler).toHaveBeenCalledWith({
        damage: 20,
        remainingHealth: 80,
      });
    });
  });

  describe('move', () => {
    it('should update position', () => {
      player.move(10, 15);
      expect(player.position).toEqual({ x: 10, y: 15 });
    });

    it('should clamp position to bounds', () => {
      player.move(1000, 2000);
      expect(player.position).toEqual({ x: 800, y: 600 });
    });
  });

  describe('heal', () => {
    beforeEach(() => {
      player.takeDamage(40);
    });

    it('should increase health', () => {
      player.heal(20);
      expect(player.health).toBe(80);
    });

    it('should not exceed max health', () => {
      player.heal(100);
      expect(player.health).toBe(100);
    });
  });
});
```

---

## xUnit 测试结构

### 等价 xUnit 测试 (godotgame)

```csharp
// Game.Core.Tests/Domain/Entities/PlayerTests.cs

using FluentAssertions;
using Game.Core.Domain.Entities;
using Game.Core.Tests.Fakes;
using Xunit;

namespace Game.Core.Tests.Domain.Entities;

/// <summary>
/// Player 实体单元测试
/// </summary>
public class PlayerTests : IDisposable
{
    private readonly Player _player;
    private readonly FakeTime _fakeTime;

    // Constructor = beforeEach
    public PlayerTests()
    {
        _fakeTime = new FakeTime();
        _player = new Player(_fakeTime);
    }

    // IDisposable = afterEach
    public void Dispose()
    {
        // Cleanup resources if needed
    }

    [Fact]
    public void Constructor_ShouldInitializeWithDefaultHealth()
    {
        // Arrange & Act (done in constructor)

        // Assert
        _player.Health.Should().Be(100);
        _player.MaxHealth.Should().Be(100);
    }

    [Fact]
    public void Constructor_ShouldInitializeAtOrigin()
    {
        // Arrange & Act (done in constructor)

        // Assert
        _player.Position.X.Should().Be(0);
        _player.Position.Y.Should().Be(0);
    }

    [Fact]
    public void TakeDamage_ShouldReduceHealthByDamageAmount()
    {
        // Arrange
        const int damage = 30;

        // Act
        _player.TakeDamage(damage);

        // Assert
        _player.Health.Should().Be(70);
    }

    [Fact]
    public void TakeDamage_ShouldNotReduceHealthBelowZero()
    {
        // Arrange
        const int damage = 150;

        // Act
        _player.TakeDamage(damage);

        // Assert
        _player.Health.Should().Be(0);
    }

    [Fact]
    public void TakeDamage_ShouldEmitDamagedEvent()
    {
        // Arrange
        int receivedDamage = 0;
        int receivedRemainingHealth = 0;

        _player.Damaged += (damage, remainingHealth) =>
        {
            receivedDamage = damage;
            receivedRemainingHealth = remainingHealth;
        };

        // Act
        _player.TakeDamage(20);

        // Assert
        receivedDamage.Should().Be(20);
        receivedRemainingHealth.Should().Be(80);
    }

    [Fact]
    public void Move_ShouldUpdatePosition()
    {
        // Arrange
        const double x = 10;
        const double y = 15;

        // Act
        _player.Move(x, y);

        // Assert
        _player.Position.X.Should().Be(10);
        _player.Position.Y.Should().Be(15);
    }

    [Fact]
    public void Move_ShouldClampPositionToBounds()
    {
        // Arrange
        const double x = 1000;
        const double y = 2000;

        // Act
        _player.Move(x, y);

        // Assert
        _player.Position.X.Should().Be(800);
        _player.Position.Y.Should().Be(600);
    }

    [Fact]
    public void Heal_ShouldIncreaseHealth()
    {
        // Arrange
        _player.TakeDamage(40);
        const int healAmount = 20;

        // Act
        _player.Heal(healAmount);

        // Assert
        _player.Health.Should().Be(80);
    }

    [Fact]
    public void Heal_ShouldNotExceedMaxHealth()
    {
        // Arrange
        _player.TakeDamage(40);
        const int healAmount = 100;

        // Act
        _player.Heal(healAmount);

        // Assert
        _player.Health.Should().Be(100);
    }
}
```

---

## 核心迁移模式

### 1. describe/it → [Fact]/[Theory]

**Jest (嵌套结构)**:

```typescript
describe('Player', () => {
  describe('takeDamage', () => {
    it('should reduce health', () => {
      // test
    });

    it('should not go below zero', () => {
      // test
    });
  });
});
```

**xUnit (扁平结构 + 命名约定)**:

```csharp
public class PlayerTests
{
    [Fact]
    public void TakeDamage_ShouldReduceHealth()
    {
        // test
    }

    [Fact]
    public void TakeDamage_ShouldNotGoBelowZero()
    {
        // test
    }
}
```

**命名约定**:
- **格式**: `MethodName_Scenario_ExpectedBehavior`
- **示例**:
  - `TakeDamage_WithNegativeAmount_ThrowsArgumentException`
  - `Constructor_WithNullTime_ThrowsArgumentNullException`
  - `Move_WithValidCoordinates_UpdatesPosition`

---

### 2. expect() → FluentAssertions

**Jest 断言 → FluentAssertions 映射表**:

| Jest | FluentAssertions | 说明 |
|------|-----------------|------|
| `expect(x).toBe(y)` | `x.Should().Be(y)` | 值相等 |
| `expect(x).toEqual(y)` | `x.Should().BeEquivalentTo(y)` | 深度相等 |
| `expect(x).toBeNull()` | `x.Should().BeNull()` | Null 检查 |
| `expect(x).toBeDefined()` | `x.Should().NotBeNull()` | 非 Null |
| `expect(x).toBeTruthy()` | `x.Should().BeTrue()` | 真值 |
| `expect(x).toBeGreaterThan(y)` | `x.Should().BeGreaterThan(y)` | 大于 |
| `expect(x).toContain(y)` | `x.Should().Contain(y)` | 包含 |
| `expect(arr).toHaveLength(n)` | `arr.Should().HaveCount(n)` | 长度/数量 |
| `expect(fn).toThrow()` | `fn.Should().Throw<Exception>()` | 异常 |
| `expect(mock).toHaveBeenCalled()` | `mock.Verify(m => m.Method(), Times.Once)` | Mock 调用 |

**示例迁移**:

```typescript
// Jest
expect(player.health).toBe(100);
expect(player.position).toEqual({ x: 0, y: 0 });
expect(player.items).toHaveLength(5);
expect(() => player.takeDamage(-10)).toThrow('Damage must be positive');
```

```csharp
// xUnit + FluentAssertions
player.Health.Should().Be(100);
player.Position.Should().BeEquivalentTo(new Vector2D(0, 0));
player.Items.Should().HaveCount(5);
Action act = () => player.TakeDamage(-10);
act.Should().Throw<ArgumentException>()
   .WithMessage("Damage must be positive*");
```

---

### 3. beforeEach/afterEach → Constructor/IDisposable

**Jest 生命周期**:

```typescript
describe('Player', () => {
  let player: Player;
  let fakeTime: FakeTime;

  beforeEach(() => {
    fakeTime = new FakeTime();
    player = new Player(fakeTime);
  });

  afterEach(() => {
    // cleanup
  });

  it('test 1', () => { /* ... */ });
  it('test 2', () => { /* ... */ });
});
```

**xUnit 生命周期**:

```csharp
public class PlayerTests : IDisposable
{
    private readonly Player _player;
    private readonly FakeTime _fakeTime;

    // beforeEach
    public PlayerTests()
    {
        _fakeTime = new FakeTime();
        _player = new Player(_fakeTime);
    }

    // afterEach
    public void Dispose()
    {
        // Cleanup
    }

    [Fact]
    public void Test1() { /* ... */ }

    [Fact]
    public void Test2() { /* ... */ }
}
```

**Class Fixtures (共享上下文)**:

```csharp
// 当需要在多个测试间共享昂贵的初始化（如数据库连接）
public class DatabaseFixture : IDisposable
{
    public SqliteDataStore DataStore { get; }

    public DatabaseFixture()
    {
        DataStore = new SqliteDataStore();
        DataStore.Open(":memory:");
        // Initialize schema
    }

    public void Dispose()
    {
        DataStore.Close();
    }
}

public class UserRepositoryTests : IClassFixture<DatabaseFixture>
{
    private readonly DatabaseFixture _fixture;

    public UserRepositoryTests(DatabaseFixture fixture)
    {
        _fixture = fixture;
    }

    [Fact]
    public void GetById_ShouldReturnUser()
    {
        // Use _fixture.DataStore
    }
}
```

---

### 4. test.each() → [Theory] + [InlineData]

**Jest 参数化测试**:

```typescript
describe('Player.takeDamage', () => {
  test.each([
    [10, 90],
    [50, 50],
    [100, 0],
    [150, 0],
  ])('when damage is %i, health should be %i', (damage, expectedHealth) => {
    player.takeDamage(damage);
    expect(player.health).toBe(expectedHealth);
  });
});
```

**xUnit 参数化测试**:

```csharp
public class PlayerTests
{
    [Theory]
    [InlineData(10, 90)]
    [InlineData(50, 50)]
    [InlineData(100, 0)]
    [InlineData(150, 0)]
    public void TakeDamage_ShouldReduceHealthCorrectly(int damage, int expectedHealth)
    {
        // Arrange
        var fakeTime = new FakeTime();
        var player = new Player(fakeTime);

        // Act
        player.TakeDamage(damage);

        // Assert
        player.Health.Should().Be(expectedHealth);
    }
}
```

**MemberData (复杂数据)**:

```csharp
public class PlayerTests
{
    public static IEnumerable<object[]> DamageTestData =>
        new List<object[]>
        {
            new object[] { 10, 90, "minor damage" },
            new object[] { 50, 50, "moderate damage" },
            new object[] { 100, 0, "lethal damage" },
            new object[] { 150, 0, "overkill damage" },
        };

    [Theory]
    [MemberData(nameof(DamageTestData))]
    public void TakeDamage_VariousScenarios(int damage, int expectedHealth, string scenario)
    {
        // Arrange
        var player = new Player(new FakeTime());

        // Act
        player.TakeDamage(damage);

        // Assert
        player.Health.Should().Be(expectedHealth, because: scenario);
    }
}
```

---

### 5. jest.mock → Moq / NSubstitute / Fakes

**Jest Mock**:

```typescript
// Jest
const mockTime = {
  getTimestamp: jest.fn(() => 1234567890),
  getDeltaTime: jest.fn(() => 0.016),
  getElapsedTime: jest.fn(() => 60.0),
};

const player = new Player(mockTime);
player.update();

expect(mockTime.getDeltaTime).toHaveBeenCalled();
```

**选择 1: Moq (验证行为)**:

```csharp
using Moq;

// Moq
var mockTime = new Mock<ITime>();
mockTime.Setup(t => t.GetTimestamp()).Returns(1234567890);
mockTime.Setup(t => t.GetDeltaTime()).Returns(0.016);
mockTime.Setup(t => t.GetElapsedTime()).Returns(60.0);

var player = new Player(mockTime.Object);
player.Update();

mockTime.Verify(t => t.GetDeltaTime(), Times.Once);
```

**选择 2: NSubstitute (更简洁)**:

```csharp
using NSubstitute;

// NSubstitute
var mockTime = Substitute.For<ITime>();
mockTime.GetTimestamp().Returns(1234567890);
mockTime.GetDeltaTime().Returns(0.016);
mockTime.GetElapsedTime().Returns(60.0);

var player = new Player(mockTime);
player.Update();

mockTime.Received(1).GetDeltaTime();
```

**选择 3: Fake 实现 (推荐用于简单场景)**:

```csharp
// Game.Core.Tests/Fakes/FakeTime.cs

public class FakeTime : ITime
{
    private double _timestamp = 1234567890;
    private double _deltaTime = 0.016;
    private double _elapsedTime = 0;

    public double GetTimestamp() => _timestamp;
    public double GetDeltaTime() => _deltaTime;
    public double GetElapsedTime() => _elapsedTime;

    public void SetTimestamp(double value) => _timestamp = value;
    public void SetDeltaTime(double value) => _deltaTime = value;
    public void AdvanceTime(double seconds) => _elapsedTime += seconds;
}

// Usage
var fakeTime = new FakeTime();
fakeTime.SetDeltaTime(0.032); // Simulate slow frame
var player = new Player(fakeTime);
player.Update();
```

**Fake vs Mock 选择原则**:

| 场景 | 使用 Fake | 使用 Mock (Moq/NSubstitute) |
|-----|----------|---------------------------|
| 简单状态对象 | [OK] FakeTime, FakeInput | 否 |
| 需要验证调用次数/顺序 | 否 | [OK] Mock |
| 复杂依赖/多方法调用 | 否 | [OK] Mock |
| 跨测试复用 | [OK] 共享 Fake | 否（每测试创建 Mock） |
| 可读性优先 | [OK] 更直观 | [警告] 学习曲线 |

---

## AAA 模式 (Arrange-Act-Assert)

### 标准 AAA 结构

```csharp
[Fact]
public void TakeDamage_WithValidAmount_ShouldReduceHealth()
{
    // Arrange (准备测试数据和依赖)
    var fakeTime = new FakeTime();
    var player = new Player(fakeTime);
    const int damage = 30;
    const int expectedHealth = 70;

    // Act (执行被测操作)
    player.TakeDamage(damage);

    // Assert (验证结果)
    player.Health.Should().Be(expectedHealth);
}
```

### 复杂 AAA 示例

```csharp
[Fact]
public void Move_WithCollision_ShouldStopAtBoundary()
{
    // Arrange
    var fakeTime = new FakeTime();
    var player = new Player(fakeTime);
    var mockCollisionDetector = new Mock<ICollisionDetector>();

    // 设置碰撞检测器在 x=500 处返回碰撞
    mockCollisionDetector
        .Setup(cd => cd.CheckCollision(It.IsAny<Vector2D>()))
        .Returns((Vector2D pos) => pos.X >= 500);

    player.SetCollisionDetector(mockCollisionDetector.Object);

    // Act
    player.Move(600, 100); // 尝试移动到 x=600

    // Assert
    player.Position.X.Should().Be(499); // 应该停在边界
    player.Position.Y.Should().Be(100);
    mockCollisionDetector.Verify(
        cd => cd.CheckCollision(It.IsAny<Vector2D>()),
        Times.AtLeastOnce
    );
}
```

---

## 异步测试迁移

### Jest 异步测试

```typescript
// Jest async/await
describe('UserService', () => {
  it('should fetch user by id', async () => {
    const user = await userService.getUserById('123');
    expect(user.username).toBe('alice');
  });

  it('should throw on invalid id', async () => {
    await expect(userService.getUserById('')).rejects.toThrow('Invalid ID');
  });
});
```

### xUnit 异步测试

```csharp
// xUnit async Task
public class UserServiceTests
{
    [Fact]
    public async Task GetUserById_ShouldReturnUser()
    {
        // Arrange
        var service = new UserService(new FakeDataStore());

        // Act
        var user = await service.GetUserByIdAsync("123");

        // Assert
        user.Username.Should().Be("alice");
    }

    [Fact]
    public async Task GetUserById_WithInvalidId_ShouldThrowArgumentException()
    {
        // Arrange
        var service = new UserService(new FakeDataStore());

        // Act
        Func<Task> act = async () => await service.GetUserByIdAsync("");

        // Assert
        await act.Should().ThrowAsync<ArgumentException>()
            .WithMessage("Invalid ID*");
    }
}
```

---

## 测试分类与过滤

### [Trait] 标记

```csharp
// Game.Core.Tests/Domain/Entities/PlayerTests.cs

public class PlayerTests
{
    [Fact]
    [Trait("Category", "Unit")]
    [Trait("Feature", "Player")]
    public void TakeDamage_ShouldReduceHealth()
    {
        // ...
    }

    [Fact]
    [Trait("Category", "Unit")]
    [Trait("Feature", "Player")]
    [Trait("Priority", "High")]
    public void Move_ShouldUpdatePosition()
    {
        // ...
    }

    [Fact]
    [Trait("Category", "Integration")]
    [Trait("Feature", "Player")]
    public void SaveToDatabase_ShouldPersist()
    {
        // ...
    }
}
```

### 运行特定分类测试

```bash
# 只运行单元测试
dotnet test --filter "Category=Unit"

# 运行特定功能的测试
dotnet test --filter "Feature=Player"

# 运行高优先级测试
dotnet test --filter "Priority=High"

# 组合过滤
dotnet test --filter "Category=Unit&Feature=Player"
```

---

## 覆盖率配置与门禁

### coverlet 配置 (Game.Core.Tests.csproj)

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="coverlet.collector" Version="6.0.0">
      <PrivateAssets>all</PrivateAssets>
      <IncludeAssets>runtime; build; native; contentfiles; analyzers</IncludeAssets>
    </PackageReference>
    <PackageReference Include="xunit" Version="2.9.3" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.8.2">
      <PrivateAssets>all</PrivateAssets>
      <IncludeAssets>runtime; build; native; contentfiles; analyzers</IncludeAssets>
    </PackageReference>
    <PackageReference Include="FluentAssertions" Version="7.0.0" />
    <PackageReference Include="Moq" Version="4.20.0" />
  </ItemGroup>

  <ItemGroup>
    <ProjectReference Include="..\Game.Core\Game.Core.csproj" />
  </ItemGroup>
</Project>
```

### 覆盖率命令

```bash
# 生成覆盖率报告
dotnet test Game.Core.Tests/Game.Core.Tests.csproj \
  --collect:"XPlat Code Coverage" \
  --results-directory ./TestResults

# 使用 ReportGenerator 生成 HTML 报告
dotnet tool install -g dotnet-reportgenerator-globaltool

reportgenerator \
  -reports:./TestResults/**/coverage.cobertura.xml \
  -targetdir:./TestResults/CoverageReport \
  -reporttypes:Html
```

### 覆盖率门禁脚本

```javascript
// scripts/quality_gates.mjs

import { readFileSync } from 'fs';
import { parseStringPromise } from 'xml2js';

const COVERAGE_LINE_THRESHOLD = 90;
const COVERAGE_BRANCH_THRESHOLD = 85;

async function checkCoverage() {
  const coverageXml = readFileSync('./TestResults/coverage.cobertura.xml', 'utf-8');
  const coverage = await parseStringPromise(coverageXml);

  const lineRate = parseFloat(coverage.coverage.$['line-rate']) * 100;
  const branchRate = parseFloat(coverage.coverage.$['branch-rate']) * 100;

  console.log(`Line Coverage: ${lineRate.toFixed(2)}%`);
  console.log(`Branch Coverage: ${branchRate.toFixed(2)}%`);

  if (lineRate < COVERAGE_LINE_THRESHOLD) {
    console.error(`FAIL Line coverage ${lineRate.toFixed(2)}% is below threshold ${COVERAGE_LINE_THRESHOLD}%`);
    process.exit(1);
  }

  if (branchRate < COVERAGE_BRANCH_THRESHOLD) {
    console.error(`FAIL Branch coverage ${branchRate.toFixed(2)}% is below threshold ${COVERAGE_BRANCH_THRESHOLD}%`);
    process.exit(1);
  }

  console.log('Coverage thresholds met');
}

checkCoverage().catch(err => {
  console.error(err);
  process.exit(1);
});
```

---

## 测试组织最佳实践

### 推荐目录结构

```
Game.Core.Tests/
├── Domain/
│   ├── Entities/
│   │   ├── PlayerTests.cs
│   │   ├── EnemyTests.cs
│   │   └── ItemTests.cs
│   ├── ValueObjects/
│   │   ├── Vector2DTests.cs
│   │   └── HealthPointsTests.cs
│   └── Services/
│       ├── GameLogicServiceTests.cs
│       └── ScoreServiceTests.cs
├── Infrastructure/
│   ├── Repositories/
│   │   ├── UserRepositoryTests.cs
│   │   └── SaveGameRepositoryTests.cs
│   └── Migrations/
│       └── DatabaseMigrationTests.cs
├── Fakes/
│   ├── FakeTime.cs
│   ├── FakeInput.cs
│   ├── FakeDataStore.cs
│   └── FakeLogger.cs
└── Fixtures/
    └── DatabaseFixture.cs
```

### 命名约定

```csharp
// Good: 测试命名清晰
[Fact]
public void Constructor_WithValidParameters_ShouldInitializeProperties()

[Fact]
public void TakeDamage_WithNegativeAmount_ThrowsArgumentException()

[Fact]
public void Move_WhenOutOfBounds_ClampsToMaxBoundary()

// Bad: 测试命名含糊
[Fact]
public void Test1()

[Fact]
public void ItWorks()

[Fact]
public void TestTakeDamage()
```

---

## 测试数据构建器模式

### 问题：复杂对象创建

```csharp
// Bad: 每个测试都重复创建复杂对象
[Fact]
public void Test1()
{
    var player = new Player(new FakeTime())
    {
        Health = 100,
        MaxHealth = 100,
        Position = new Vector2D(50, 50),
        Velocity = new Vector2D(10, 0),
        Items = new List<Item>
        {
            new Item { Id = "1", Name = "Sword" },
            new Item { Id = "2", Name = "Shield" }
        }
    };
    // test...
}

[Fact]
public void Test2()
{
    var player = new Player(new FakeTime())
    {
        Health = 50,
        MaxHealth = 100,
        Position = new Vector2D(100, 100),
        // ... 重复创建
    };
    // test...
}
```

### 解决方案：Builder Pattern

```csharp
// Game.Core.Tests/Builders/PlayerBuilder.cs

public class PlayerBuilder
{
    private ITime _time = new FakeTime();
    private int _health = 100;
    private int _maxHealth = 100;
    private Vector2D _position = new Vector2D(0, 0);
    private Vector2D _velocity = new Vector2D(0, 0);
    private List<Item> _items = new();

    public static PlayerBuilder APlayer() => new();

    public PlayerBuilder WithHealth(int health)
    {
        _health = health;
        return this;
    }

    public PlayerBuilder WithMaxHealth(int maxHealth)
    {
        _maxHealth = maxHealth;
        return this;
    }

    public PlayerBuilder At(double x, double y)
    {
        _position = new Vector2D(x, y);
        return this;
    }

    public PlayerBuilder WithVelocity(double vx, double vy)
    {
        _velocity = new Vector2D(vx, vy);
        return this;
    }

    public PlayerBuilder WithItem(Item item)
    {
        _items.Add(item);
        return this;
    }

    public PlayerBuilder Injured()
    {
        _health = 30;
        return this;
    }

    public PlayerBuilder AtFullHealth()
    {
        _health = _maxHealth;
        return this;
    }

    public Player Build()
    {
        var player = new Player(_time)
        {
            Health = _health,
            MaxHealth = _maxHealth,
            Position = _position,
            Velocity = _velocity
        };

        foreach (var item in _items)
        {
            player.AddItem(item);
        }

        return player;
    }
}

// 使用示例
public class PlayerTests
{
    [Fact]
    public void TakeDamage_WhenInjured_ShouldReduceHealth()
    {
        // Arrange
        var player = PlayerBuilder.APlayer()
            .Injured()
            .At(50, 50)
            .Build();

        // Act
        player.TakeDamage(10);

        // Assert
        player.Health.Should().Be(20);
    }

    [Fact]
    public void Move_FromOrigin_ShouldUpdatePosition()
    {
        // Arrange
        var player = PlayerBuilder.APlayer()
            .AtFullHealth()
            .Build();

        // Act
        player.Move(10, 15);

        // Assert
        player.Position.Should().BeEquivalentTo(new Vector2D(10, 15));
    }
}
```

---

## 特定场景测试模式

### 1. 异常测试

```csharp
[Fact]
public void TakeDamage_WithNegativeAmount_ThrowsArgumentException()
{
    // Arrange
    var player = PlayerBuilder.APlayer().Build();

    // Act
    Action act = () => player.TakeDamage(-10);

    // Assert
    act.Should().Throw<ArgumentException>()
       .WithMessage("Damage must be positive*")
       .And.ParamName.Should().Be("amount");
}

[Fact]
public void Constructor_WithNullTime_ThrowsArgumentNullException()
{
    // Arrange & Act
    Action act = () => new Player(null!);

    // Assert
    act.Should().Throw<ArgumentNullException>()
       .WithParameterName("time");
}
```

### 2. 事件/信号测试

```csharp
[Fact]
public void TakeDamage_ShouldRaiseDamagedEvent()
{
    // Arrange
    var player = PlayerBuilder.APlayer().Build();
    int receivedDamage = 0;
    int receivedHealth = 0;

    player.Damaged += (damage, health) =>
    {
        receivedDamage = damage;
        receivedHealth = health;
    };

    // Act
    player.TakeDamage(25);

    // Assert
    receivedDamage.Should().Be(25);
    receivedHealth.Should().Be(75);
}

[Fact]
public void TakeDamage_WhenHealthReachesZero_ShouldRaiseDeathEvent()
{
    // Arrange
    var player = PlayerBuilder.APlayer().WithHealth(10).Build();
    bool deathEventRaised = false;

    player.Death += () => deathEventRaised = true;

    // Act
    player.TakeDamage(20);

    // Assert
    deathEventRaised.Should().BeTrue();
    player.Health.Should().Be(0);
}
```

### 3. 时间依赖测试

```csharp
[Fact]
public void Update_ShouldUseCorrectDeltaTime()
{
    // Arrange
    var fakeTime = new FakeTime();
    fakeTime.SetDeltaTime(0.032); // 30 FPS

    var player = new Player(fakeTime);
    player.Velocity = new Vector2D(100, 0); // 100 units/sec

    // Act
    player.Update(); // Should move 100 * 0.032 = 3.2 units

    // Assert
    player.Position.X.Should().BeApproximately(3.2, 0.01);
}

[Fact]
public void Cooldown_AfterElapsedTime_ShouldExpire()
{
    // Arrange
    var fakeTime = new FakeTime();
    var player = new Player(fakeTime);
    player.StartCooldown(5.0); // 5 second cooldown

    // Act
    fakeTime.AdvanceTime(6.0);
    player.Update();

    // Assert
    player.IsCooldownActive.Should().BeFalse();
}
```

### 4. 状态转换测试

```csharp
[Theory]
[InlineData(PlayerState.Idle, PlayerState.Running)]
[InlineData(PlayerState.Running, PlayerState.Jumping)]
[InlineData(PlayerState.Jumping, PlayerState.Falling)]
[InlineData(PlayerState.Falling, PlayerState.Idle)]
public void TransitionTo_WithValidTransition_ShouldChangeState(
    PlayerState fromState,
    PlayerState toState)
{
    // Arrange
    var player = PlayerBuilder.APlayer().Build();
    player.SetState(fromState);

    // Act
    player.TransitionTo(toState);

    // Assert
    player.CurrentState.Should().Be(toState);
}

[Fact]
public void TransitionTo_WithInvalidTransition_ShouldThrowInvalidOperationException()
{
    // Arrange
    var player = PlayerBuilder.APlayer().Build();
    player.SetState(PlayerState.Idle);

    // Act
    Action act = () => player.TransitionTo(PlayerState.Falling);

    // Assert
    act.Should().Throw<InvalidOperationException>()
       .WithMessage("Cannot transition from Idle to Falling*");
}
```

---

## 测试替身完整示例

### FakeTime 实现

```csharp
// Game.Core.Tests/Fakes/FakeTime.cs

using Game.Core.Ports;

namespace Game.Core.Tests.Fakes;

public class FakeTime : ITime
{
    private double _timestamp = 1234567890;
    private double _deltaTime = 0.016; // 60 FPS
    private double _elapsedTime = 0;

    public double GetTimestamp() => _timestamp;
    public double GetDeltaTime() => _deltaTime;
    public double GetElapsedTime() => _elapsedTime;

    public void SetTimestamp(double value) => _timestamp = value;
    public void SetDeltaTime(double value) => _deltaTime = value;

    public void AdvanceTime(double seconds)
    {
        _elapsedTime += seconds;
        _timestamp += seconds;
    }

    public void Reset()
    {
        _timestamp = 1234567890;
        _deltaTime = 0.016;
        _elapsedTime = 0;
    }
}
```

### FakeInput 实现

```csharp
// Game.Core.Tests/Fakes/FakeInput.cs

using Game.Core.Ports;

namespace Game.Core.Tests.Fakes;

public class FakeInput : IInput
{
    private readonly Dictionary<string, bool> _pressedActions = new();
    private readonly Dictionary<string, bool> _justPressedActions = new();
    private readonly Dictionary<string, bool> _justReleasedActions = new();
    private Vector2D _mousePosition = Vector2D.Zero;

    public void SetActionPressed(string action, bool pressed)
    {
        _pressedActions[action] = pressed;
    }

    public void SimulateActionPress(string action)
    {
        _justPressedActions[action] = true;
        _pressedActions[action] = true;
    }

    public void SimulateActionRelease(string action)
    {
        _justReleasedActions[action] = true;
        _pressedActions[action] = false;
    }

    public void SetMousePosition(Vector2D position)
    {
        _mousePosition = position;
    }

    public bool IsActionPressed(string action)
    {
        return _pressedActions.GetValueOrDefault(action, false);
    }

    public bool IsActionJustPressed(string action)
    {
        var result = _justPressedActions.GetValueOrDefault(action, false);
        _justPressedActions[action] = false; // 消费
        return result;
    }

    public bool IsActionJustReleased(string action)
    {
        var result = _justReleasedActions.GetValueOrDefault(action, false);
        _justReleasedActions[action] = false; // 消费
        return result;
    }

    public Vector2D GetAxis(string negativeX, string positiveX, string negativeY, string positiveY)
    {
        var x = (IsActionPressed(positiveX) ? 1.0 : 0.0) - (IsActionPressed(negativeX) ? 1.0 : 0.0);
        var y = (IsActionPressed(positiveY) ? 1.0 : 0.0) - (IsActionPressed(negativeY) ? 1.0 : 0.0);
        return new Vector2D(x, y);
    }

    public Vector2D GetMousePosition()
    {
        return _mousePosition;
    }

    public void Reset()
    {
        _pressedActions.Clear();
        _justPressedActions.Clear();
        _justReleasedActions.Clear();
        _mousePosition = Vector2D.Zero;
    }
}
```

### FakeDataStore 实现

```csharp
// Game.Core.Tests/Fakes/FakeDataStore.cs

using Game.Core.Ports;

namespace Game.Core.Tests.Fakes;

public class FakeDataStore : IDataStore
{
    private readonly Dictionary<Type, Dictionary<string, object>> _tables = new();
    private bool _isOpen = false;

    public void Open(string dbPath)
    {
        _isOpen = true;
    }

    public void Close()
    {
        _isOpen = false;
        _tables.Clear();
    }

    public void Execute(string sql, params object[] parameters)
    {
        EnsureOpen();
        // 简化实现：不真正解析 SQL，仅用于测试
    }

    public T? QuerySingle<T>(string sql, params object[] parameters) where T : class
    {
        EnsureOpen();
        var table = GetTable<T>();
        return table.Values.FirstOrDefault() as T;
    }

    public List<T> Query<T>(string sql, params object[] parameters) where T : class
    {
        EnsureOpen();
        var table = GetTable<T>();
        return table.Values.Cast<T>().ToList();
    }

    // Test helper methods
    public void Insert<T>(string id, T entity) where T : class
    {
        EnsureOpen();
        var table = GetTable<T>();
        table[id] = entity;
    }

    public void Clear<T>() where T : class
    {
        if (_tables.ContainsKey(typeof(T)))
        {
            _tables[typeof(T)].Clear();
        }
    }

    private Dictionary<string, object> GetTable<T>()
    {
        var type = typeof(T);
        if (!_tables.ContainsKey(type))
        {
            _tables[type] = new Dictionary<string, object>();
        }
        return _tables[type];
    }

    private void EnsureOpen()
    {
        if (!_isOpen)
        {
            throw new InvalidOperationException("Database not opened");
        }
    }
}
```

---

## CI 集成

### GitHub Actions 配置

```yaml
# .github/workflows/tests.yml

name: Unit Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup .NET 8
        uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '8.0.x'

      - name: Restore dependencies
        run: dotnet restore Game.Core.Tests/Game.Core.Tests.csproj

      - name: Build
        run: dotnet build Game.Core.Tests/Game.Core.Tests.csproj --no-restore

      - name: Run unit tests with coverage
        run: |
          dotnet test Game.Core.Tests/Game.Core.Tests.csproj `
            --no-build `
            --verbosity normal `
            --collect:"XPlat Code Coverage" `
            --results-directory ./TestResults `
            --logger trx

      - name: Generate coverage report
        run: |
          dotnet tool install -g dotnet-reportgenerator-globaltool
          reportgenerator `
            -reports:./TestResults/**/coverage.cobertura.xml `
            -targetdir:./TestResults/CoverageReport `
            -reporttypes:Html;Cobertura

      - name: Check coverage thresholds
        run: node scripts/quality_gates.mjs

      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: ./TestResults/CoverageReport

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: ./TestResults/*.trx

      - name: Publish coverage to Codecov
        if: always()
        uses: codecov/codecov-action@v3
        with:
          files: ./TestResults/**/coverage.cobertura.xml
          flags: unittests
          name: codecov-godotgame
```

---

## 完成标准

- [ ] 所有 Jest 单元测试已迁移到 xUnit
- [ ] 使用 FluentAssertions 替代 Jest expect()
- [ ] AAA 模式在所有测试中一致应用
- [ ] 测试命名符合 `MethodName_Scenario_ExpectedBehavior` 约定
- [ ] [Theory] + [InlineData] 用于参数化测试
- [ ] Fake 实现提供给核心端口 (ITime, IInput, IDataStore, ILogger)
- [ ] Builder 模式用于复杂对象创建
- [ ] 覆盖率达到 ≥90% 行覆盖率，≥85% 分支覆盖率
- [ ] coverlet 配置正确，生成 Cobertura 报告
- [ ] CI 管道包含单元测试执行和覆盖率门禁
- [ ] 测试分类使用 [Trait] 标记（Category, Feature, Priority）

---

## 下一步

完成本阶段后，继续：

[参考] [Phase-11-Scene-Integration-Tests-REVISED.md](Phase-11-Scene-Integration-Tests-REVISED.md) — 场景测试设计（GdUnit4）
