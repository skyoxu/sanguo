# Phase 5: Godot 适配层设计

> 状态: 实施阶段
> 预估工时: 5-8 天
> 风险等级: 中
> 前置条件: Phase 1-4 完成

---

## 目标

实现 Godot API 适配层，将 Game.Core 的端口接口与 Godot Engine 连接，确保纯逻辑与引擎解耦。

---

## 适配器清单

### 核心适配器（必需）

- [ ] GodotTimeAdapter (ITime)
- [ ] GodotInputAdapter (IInput)
- [ ] GodotResourceLoader (IResourceLoader)
- [ ] GodotAudioPlayer (IAudioPlayer)
- [ ] SqliteDataStore (IDataStore)
- [ ] GodotLogger (ILogger)

### ServiceLocator (依赖注入容器)

- [ ] ServiceLocator.cs Autoload
- [ ] 启动时注册所有适配器
- [ ] 提供全局单例访问

---

## 1. ITime 适配器

### 接口定义 (Game.Core/Ports/ITime.cs)

```csharp
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

    /// <summary>
    /// 获取自启动以来的时间（秒）
    /// </summary>
    double GetElapsedTime();
}
```

### Godot 适配器 (Game.Godot/Adapters/GodotTimeAdapter.cs)

```csharp
using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

/// <summary>
/// Godot 时间适配器
/// </summary>
public class GodotTimeAdapter : ITime
{
    private double _lastFrameTime;

    public GodotTimeAdapter()
    {
        _lastFrameTime = Time.GetTicksMsec() / 1000.0;
    }

    public double GetTimestamp()
    {
        return Time.GetUnixTimeFromSystem();
    }

    public double GetDeltaTime()
    {
        // 使用当前 FPS 估算 delta（Headless/运行时均适用）
        var fps = Engine.GetFramesPerSecond();
        return fps > 0 ? 1.0 / fps : 0.0;
    }

    public double GetElapsedTime()
    {
        return Time.GetTicksMsec() / 1000.0;
    }
}
```

### 契约测试 (Game.Core.Tests/Adapters/ITimeContractTests.cs)

```csharp
using FluentAssertions;
using Game.Core.Ports;
using Xunit;

namespace Game.Core.Tests.Adapters;

/// <summary>
/// ITime 契约测试（适配器必须通过）
/// </summary>
public abstract class ITimeContractTests
{
    protected abstract ITime CreateTimeAdapter();

    [Fact]
    public void GetTimestamp_ShouldReturnReasonableValue()
    {
        // Arrange
        var time = CreateTimeAdapter();
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

        // Act
        var timestamp = time.GetTimestamp();

        // Assert（误差允许 ±10 秒）
        timestamp.Should().BeCloseTo(now, 10);
    }

    [Fact]
    public void GetDeltaTime_ShouldBePositive()
    {
        // Arrange
        var time = CreateTimeAdapter();

        // Act
        var delta = time.GetDeltaTime();

        // Assert（60 FPS = 0.016s，容忍 0~0.1s）
        delta.Should().BeInRange(0, 0.1);
    }

    [Fact]
    public void GetElapsedTime_ShouldMonotonicallyIncrease()
    {
        // Arrange
        var time = CreateTimeAdapter();

        // Act
        var elapsed1 = time.GetElapsedTime();
        System.Threading.Thread.Sleep(100);
        var elapsed2 = time.GetElapsedTime();

        // Assert
        elapsed2.Should().BeGreaterThan(elapsed1);
    }
}

/// <summary>
/// FakeTime 契约测试
/// </summary>
public class FakeTimeContractTests : ITimeContractTests
{
    protected override ITime CreateTimeAdapter()
    {
        return new FakeTime();
    }
}
```

---

## 2. IInput 适配器

### 接口定义 (Game.Core/Ports/IInput.cs)

```csharp
namespace Game.Core.Ports;

public interface IInput
{
    bool IsActionPressed(string action);
    bool IsActionJustPressed(string action);
    bool IsActionJustReleased(string action);
    Vector2D GetAxis(string negativeX, string positiveX, string negativeY, string positiveY);
    Vector2D GetMousePosition();
}

/// <summary>
/// 2D 向量（Game.Core 值对象）
/// </summary>
public record Vector2D(double X, double Y)
{
    public static Vector2D Zero => new(0, 0);

    public Vector2D Normalized()
    {
        var length = Math.Sqrt(X * X + Y * Y);
        return length > 0 ? new(X / length, Y / length) : Zero;
    }
}
```

### Godot 适配器 (Game.Godot/Adapters/GodotInputAdapter.cs)

```csharp
using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

public class GodotInputAdapter : IInput
{
    public bool IsActionPressed(string action)
    {
        return Input.IsActionPressed(action);
    }

    public bool IsActionJustPressed(string action)
    {
        return Input.IsActionJustPressed(action);
    }

    public bool IsActionJustReleased(string action)
    {
        return Input.IsActionJustReleased(action);
    }

    public Vector2D GetAxis(string negativeX, string positiveX, string negativeY, string positiveY)
    {
        var x = Input.GetAxis(negativeX, positiveX);
        var y = Input.GetAxis(negativeY, positiveY);
        return new Vector2D(x, y);
    }

    public Vector2D GetMousePosition()
    {
        var pos = Input.GetMousePosition();
        return new Vector2D(pos.X, pos.Y);
    }
}
```

### Fake 实现 (Game.Core.Tests/Fakes/FakeInput.cs)

```csharp
using Game.Core.Ports;

namespace Game.Core.Tests.Fakes;

public class FakeInput : IInput
{
    private readonly Dictionary<string, bool> _pressedActions = new();
    private readonly Dictionary<string, bool> _justPressedActions = new();
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
        return false; // 简化实现
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
}
```

---

## 3. IResourceLoader 适配器

### 接口定义 (Game.Core/Ports/IResourceLoader.cs)

```csharp
namespace Game.Core.Ports;

public interface IResourceLoader
{
    T Load<T>(string path) where T : class;
    bool Exists(string path);
    string[] ListFiles(string directory, string pattern = "*");
}
```

### Godot 适配器 (Game.Godot/Adapters/GodotResourceLoader.cs)

```csharp
using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

public class GodotResourceLoader : IResourceLoader
{
    public T Load<T>(string path) where T : class
    {
        var resource = ResourceLoader.Load(path);

        if (resource is T typedResource)
        {
            return typedResource;
        }

        throw new InvalidCastException($"Resource at {path} is not of type {typeof(T).Name}");
    }

    public bool Exists(string path)
    {
        return ResourceLoader.Exists(path);
    }

    public string[] ListFiles(string directory, string pattern = "*")
    {
        var dir = DirAccess.Open(directory);
        if (dir == null)
        {
            return Array.Empty<string>();
        }

        var files = new List<string>();
        dir.ListDirBegin();

        string fileName = dir.GetNext();
        while (!string.IsNullOrEmpty(fileName))
        {
            if (!dir.CurrentIsDir() && MatchesPattern(fileName, pattern))
            {
                files.Add($"{directory}/{fileName}");
            }
            fileName = dir.GetNext();
        }

        dir.ListDirEnd();
        return files.ToArray();
    }

    private static bool MatchesPattern(string fileName, string pattern)
    {
        if (pattern == "*") return true;

        // 简单通配符支持（可扩展为正则）
        if (pattern.StartsWith("*."))
        {
            var extension = pattern.Substring(1);
            return fileName.EndsWith(extension, StringComparison.OrdinalIgnoreCase);
        }

        return fileName.Equals(pattern, StringComparison.OrdinalIgnoreCase);
    }
}
```

---

## 4. IAudioPlayer 适配器

### 接口定义 (Game.Core/Ports/IAudioPlayer.cs)

```csharp
namespace Game.Core.Ports;

public interface IAudioPlayer
{
    void PlaySound(string soundPath, float volume = 1.0f);
    void PlayMusic(string musicPath, float volume = 1.0f, bool loop = true);
    void StopMusic();
    void SetMasterVolume(float volume);
}
```

### Godot 适配器 (Game.Godot/Adapters/GodotAudioPlayer.cs)

```csharp
using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

public class GodotAudioPlayer : IAudioPlayer
{
    private AudioStreamPlayer? _musicPlayer;

    public void PlaySound(string soundPath, float volume = 1.0f)
    {
        var sound = ResourceLoader.Load<AudioStream>(soundPath);
        if (sound == null)
        {
            GD.PrintErr($"Sound not found: {soundPath}");
            return;
        }

        var player = new AudioStreamPlayer
        {
            Stream = sound,
            VolumeDb = Mathf.LinearToDb(volume),
            Autoplay = true
        };

        // 添加到场景树并在播放完成后自动移除
        player.Finished += () => player.QueueFree();
        GetTree().Root.AddChild(player);
    }

    public void PlayMusic(string musicPath, float volume = 1.0f, bool loop = true)
    {
        StopMusic();

        var music = ResourceLoader.Load<AudioStream>(musicPath);
        if (music == null)
        {
            GD.PrintErr($"Music not found: {musicPath}");
            return;
        }

        _musicPlayer = new AudioStreamPlayer
        {
            Stream = music,
            VolumeDb = Mathf.LinearToDb(volume),
            Autoplay = true
        };

        if (music is AudioStreamOggVorbis oggMusic)
        {
            oggMusic.Loop = loop;
        }

        GetTree().Root.AddChild(_musicPlayer);
    }

    public void StopMusic()
    {
        if (_musicPlayer != null)
        {
            _musicPlayer.Stop();
            _musicPlayer.QueueFree();
            _musicPlayer = null;
        }
    }

    public void SetMasterVolume(float volume)
    {
        var busIndex = AudioServer.GetBusIndex("Master");
        AudioServer.SetBusVolumeDb(busIndex, Mathf.LinearToDb(volume));
    }

    private SceneTree GetTree()
    {
        return (SceneTree)Engine.GetMainLoop();
    }
}
```

---

## 5. IDataStore 适配器 (SQLite)

### 接口定义 (Game.Core/Ports/IDataStore.cs)

```csharp
namespace Game.Core.Ports;

public interface IDataStore
{
    void Open(string dbPath);
    void Close();
    void Execute(string sql, params object[] parameters);
    T? QuerySingle<T>(string sql, params object[] parameters) where T : class;
    List<T> Query<T>(string sql, params object[] parameters) where T : class;
}
```

### Godot SQLite 适配器 (Game.Godot/Adapters/SqliteDataStore.cs)

```csharp
using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

/// <summary>
/// 使用 godot-sqlite 插件的适配器
/// 文档: https://github.com/2shady4u/godot-sqlite
/// </summary>
public class SqliteDataStore : IDataStore
{
    private SQLite? _db;

    public void Open(string dbPath)
    {
        _db = new SQLite();
        _db.Path = dbPath;

        if (!_db.OpenDb())
        {
            throw new InvalidOperationException($"Failed to open database: {dbPath}");
        }
    }

    public void Close()
    {
        _db?.CloseDb();
        _db = null;
    }

    public void Execute(string sql, params object[] parameters)
    {
        if (_db == null)
            throw new InvalidOperationException("Database not opened");

        var success = _db.Query(sql);
        if (!success)
        {
            throw new InvalidOperationException($"SQL execution failed: {sql}");
        }
    }

    public T? QuerySingle<T>(string sql, params object[] parameters) where T : class
    {
        var results = Query<T>(sql, parameters);
        return results.FirstOrDefault();
    }

    public List<T> Query<T>(string sql, params object[] parameters) where T : class
    {
        if (_db == null)
            throw new InvalidOperationException("Database not opened");

        _db.Query(sql);
        var results = new List<T>();

        for (int i = 0; i < _db.QueryResult.Length; i++)
        {
            var row = _db.QueryResult[i].As<Godot.Collections.Dictionary>();
            var instance = MapToObject<T>(row);
            if (instance != null)
            {
                results.Add(instance);
            }
        }

        return results;
    }

    private T? MapToObject<T>(Godot.Collections.Dictionary row) where T : class
    {
        // 简化实现：使用反射映射（生产环境建议优化）
        var instance = Activator.CreateInstance<T>();
        var properties = typeof(T).GetProperties();

        foreach (var prop in properties)
        {
            if (row.ContainsKey(prop.Name))
            {
                var value = row[prop.Name];
                prop.SetValue(instance, Convert.ChangeType(value, prop.PropertyType));
            }
        }

        return instance;
    }
}
```

---

## 6. ILogger 适配器

### 接口定义 (Game.Core/Ports/ILogger.cs)

```csharp
namespace Game.Core.Ports;

public interface ILogger
{
    void LogDebug(string message);
    void LogInfo(string message);
    void LogWarning(string message);
    void LogError(string message, Exception? exception = null);
}
```

### Godot 适配器 (Game.Godot/Adapters/GodotLogger.cs)

```csharp
using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

public class GodotLogger : ILogger
{
    private readonly string _category;

    public GodotLogger(string category = "Game")
    {
        _category = category;
    }

    public void LogDebug(string message)
    {
        GD.Print($"[{_category}] DEBUG: {message}");
    }

    public void LogInfo(string message)
    {
        GD.Print($"[{_category}] INFO: {message}");
    }

    public void LogWarning(string message)
    {
        GD.PushWarning($"[{_category}] WARNING: {message}");
    }

    public void LogError(string message, Exception? exception = null)
    {
        var fullMessage = exception != null
            ? $"[{_category}] ERROR: {message}\n{exception}"
            : $"[{_category}] ERROR: {message}";

        GD.PushError(fullMessage);
    }
}
```

---

## 7. ServiceLocator (依赖注入容器)

### Autoload 实现 (Game.Godot/Autoloads/ServiceLocator.cs)

```csharp
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
    public static ServiceLocator Instance { get; private set; } = null!;

    // 适配器实例
    public ITime Time { get; private set; } = null!;
    public IInput InputService { get; private set; } = null!;
    public IResourceLoader ResourceLoader { get; private set; } = null!;
    public IAudioPlayer AudioPlayer { get; private set; } = null!;
    public IDataStore DataStore { get; private set; } = null!;
    public ILogger Logger { get; private set; } = null!;

    public override void _Ready()
    {
        Instance = this;

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

### 注册到 project.godot

```ini
[autoload]

ServiceLocator="*res://Autoloads/ServiceLocator.cs"
Security="*res://Autoloads/Security.cs"
Observability="*res://Autoloads/Observability.cs"
```

---

## 8. 使用示例

### 在场景脚本中使用 (Game.Godot/Scripts/PlayerController.cs)

```csharp
using Godot;
using Game.Core.Domain.Entities;
using Game.Godot.Autoloads;

namespace Game.Godot.Scripts;

public partial class PlayerController : Node2D
{
    private Player _player = null!;

    public override void _Ready()
    {
        // 从 ServiceLocator 获取依赖
        var time = ServiceLocator.Instance.Time;
        var logger = ServiceLocator.Instance.Logger;

        _player = new Player(time);
        logger.LogInfo("Player initialized");
    }

    public override void _Process(double delta)
    {
        var input = ServiceLocator.Instance.InputService;

        // 获取输入轴
        var movement = input.GetAxis("move_left", "move_right", "move_up", "move_down");

        if (movement.X != 0 || movement.Y != 0)
        {
            _player.Move(movement.X * delta * 100, movement.Y * delta * 100);
            Position = new Vector2((float)_player.Position.X, (float)_player.Position.Y);
        }
    }
}
```

---

## 9. 契约测试强制执行

### 抽象契约测试基类 (Game.Core.Tests/Adapters/ContractTestBase.cs)

```csharp
namespace Game.Core.Tests.Adapters;

/// <summary>
/// 所有适配器契约测试的基类
/// </summary>
public abstract class ContractTestBase<TInterface>
{
    protected abstract TInterface CreateAdapter();

    /// <summary>
    /// 验证适配器不为 null
    /// </summary>
    [Fact]
    public void Adapter_ShouldNotBeNull()
    {
        var adapter = CreateAdapter();
        adapter.Should().NotBeNull();
    }
}
```

### IInput 契约测试 (Game.Core.Tests/Adapters/IInputContractTests.cs)

```csharp
using FluentAssertions;
using Game.Core.Ports;
using Xunit;

namespace Game.Core.Tests.Adapters;

public abstract class IInputContractTests : ContractTestBase<IInput>
{
    [Fact]
    public void IsActionPressed_WithUnknownAction_ShouldReturnFalse()
    {
        var input = CreateAdapter();
        var result = input.IsActionPressed("unknown_action_xyz");
        result.Should().BeFalse();
    }

    [Fact]
    public void GetAxis_ShouldReturnNormalizedVector()
    {
        var input = CreateAdapter();
        var axis = input.GetAxis("left", "right", "up", "down");

        // 轴值应在 [-1, 1] 范围内
        axis.X.Should().BeInRange(-1.0, 1.0);
        axis.Y.Should().BeInRange(-1.0, 1.0);
    }
}

public class FakeInputContractTests : IInputContractTests
{
    protected override IInput CreateAdapter()
    {
        return new FakeInput();
    }
}
```

---

## 10. CI 门禁：适配器契约测试

### 添加到 CI 管道 (.github/workflows/tests.yml)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  adapter-contracts:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup .NET 8
        uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '8.0.x'

      - name: Restore dependencies
        run: dotnet restore Game.Core.Tests/Game.Core.Tests.csproj

      - name: Run Adapter Contract Tests
        run: |
          dotnet test Game.Core.Tests/Game.Core.Tests.csproj `
            --filter "FullyQualifiedName~ContractTests" `
            --no-restore `
            --verbosity normal

      - name: Check Contract Coverage
        run: |
          $testResults = dotnet test Game.Core.Tests/Game.Core.Tests.csproj `
            --filter "FullyQualifiedName~ContractTests" `
            --collect:"XPlat Code Coverage" `
            --results-directory ./TestResults

          # 验证所有适配器接口都有契约测试
          $interfaces = @("ITime", "IInput", "IResourceLoader", "IAudioPlayer", "IDataStore", "ILogger")
          foreach ($interface in $interfaces) {
            $testFile = "Game.Core.Tests/Adapters/${interface}ContractTests.cs"
            if (-not (Test-Path $testFile)) {
              Write-Error "Missing contract tests for $interface"
              exit 1
            }
          }
```

---

## 完成标准

- [ ] 所有 6 个核心适配器已实现（Time/Input/ResourceLoader/AudioPlayer/DataStore/Logger）
- [ ] ServiceLocator Autoload 已创建并注册
- [ ] 每个适配器都有对应的抽象契约测试
- [ ] FakeXXX 测试实现通过契约测试
- [ ] `dotnet test --filter ContractTests` 全部通过
- [ ] ServiceLocator 可在场景脚本中正常使用
- [ ] 数据库连接与查询功能正常
- [ ] 音频播放功能正常（Sound/Music）

---

## 下一步

完成本阶段后，继续：

➡️ [Phase-6-Data-Storage.md](Phase-6-Data-Storage.md) — SQLite 数据层迁移
