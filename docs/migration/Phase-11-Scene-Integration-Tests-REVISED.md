# Phase 11: 场景集成测试（GdUnit4 + xUnit 双轨）

**阶段目标**: 建立完整的 Godot 场景集成测试框架，采用 **GdUnit4**（Godot 原生）+ **xUnit**（C# 领域逻辑）双轨方案，避免重型 GdUnit4 依赖

**工作量**: 8-10 人天  
**风险等级**: 低（GdUnit4 轻量，xUnit 社区成熟）  
**依赖**: Phase 8（场景设计）、Phase 10（xUnit 单元测试）  
**后续依赖**: Phase 12（E2E Headless 冒烟测试）

---

## 11.1 框架选型与架构

### 11.1.1 为什么选 GdUnit4 而非 GdUnit4

| 对比项 | GdUnit4 | GdUnit4 |
|--------|-----|---------|
| **学习曲线** | 低（Godot 原生） | 高（独立框架） |
| **Headless 支持** | 原生支持 | 需额外配置 |
| **CI 适配** | Headless 友好 | 需要额外驱动 |
| **GDScript 友好** | 完全原生 | C# 适配不如 GDScript |
| **依赖管理** | 零外部依赖 | 需手动 clone |
| **性能** | 轻量快速 | 较重 |

**结论**: 采用 GdUnit4 作为场景级测试主力，xUnit 负责 Game.Core 领域逻辑

### 11.1.2 双轨测试架构

```
┌─────────────────────────────────────────────────────────┐
│                    Quality Gates                         │
├─────────────────────────────────────────────────────────┤
│ xUnit (Game.Core)     │      GdUnit4 (Game.Godot Scenes)   │
│ ─────────────────     │      ──────────────────────     │
│ • 域逻辑（红绿灯）     │ • 场景加载/初始化             │
│ • 100% 独立 Godot     │ • Signal 连通性               │
│ • 覆盖率 ≥90% 行      │ • 节点交互模拟                │
│ • 运行时 <5秒         │ • 场景转换验证                │
│ • Headless 原生      │ • Headless 原生              │
└─────────────────────────────────────────────────────────┘
```

---

## 11.2 GdUnit4 框架集成与设置

### 11.2.1 安装 GdUnit4

**Python 安装脚本（推荐）** (`scripts/install_gut.py`):

```python
import sys
from pathlib import Path
import subprocess

def main(project_root: str) -> int:
    root = Path(project_root)
    addons = root / 'addons'
    addons.mkdir(parents=True, exist_ok=True)
    gut = addons / 'gut'
    if not gut.exists():
        print('Cloning GdUnit4...')
        subprocess.check_call(['git', 'clone', 'https://github.com/bitwes/Gut.git', str(gut)])
    else:
        print('Updating GdUnit4...')
        subprocess.check_call(['git', '-C', str(gut), 'pull'])
    plugin = gut / 'plugin.cfg'
    if plugin.exists():
        print('GdUnit4 installed successfully at', gut)
        return 0
    print('GdUnit4 installation failed: plugin.cfg not found')
    return 1

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: py -3 scripts/install_gut.py <ProjectRoot>')
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
```

运行示例（Windows）：

```
py -3 scripts/install_gut.py C:\buildgame\godotgame
```

### 11.2.2 项目配置

**project.godot 配置**：

```ini
[addons]

gut/enabled=true
gut/runner_scene=res://addons/gut/runner.tscn

[gut]

# GdUnit4 配置
print_tests=true
print_summary=true
tests_like_name_containing=Test
```

### 11.2.3 GdUnit4 基础测试类

**GdUnit4 基类** (`Game.Godot/Tests/GutTestBase.cs`):

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

## 11.3 主场景集成测试（GdUnit4）

### 11.3.1 MainScene 测试

**测试文件** (`Game.Godot/Tests/Scenes/MainSceneTest.cs`):

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

## 11.4 游戏场景集成测试（GdUnit4）

### 11.4.1 GameScene 测试

**测试文件** (`Game.Godot/Tests/Scenes/GameSceneTest.cs`):

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

## 11.5 Signal 系统测试（GdUnit4）

### 11.5.1 EventBus 测试

**测试文件** (`Game.Godot/Tests/Systems/EventBusTest.cs`):

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

## 11.6 完整流程集成测试（GdUnit4）

### 11.6.1 端到端场景流程

**测试文件** (`Game.Godot/Tests/Scenes/FullFlowTest.cs`):

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

## 11.7 xUnit 领域逻辑补充测试

**重要**: Game.Core 中的纯逻辑由 **Phase 10** 的 xUnit 负责，这里仅补充 Godot 适配层测试。

### 11.7.1 适配层契约测试

**测试文件** (`Game.Core.Tests/Adapters/GodotTimeAdapterTests.cs`):

```csharp
using Xunit;
using FluentAssertions;
using System;
using Moq;

public class GodotTimeAdapterTests
{
    [Fact]
    public void GetCurrentTime_ShouldReturnValidTimestamp()
    {
        // Arrange
        var adapter = new GodotTimeAdapter();
        
        // Act
        var before = DateTime.UtcNow;
        var time = adapter.GetCurrentTime();
        var after = DateTime.UtcNow;
        
        // Assert
        time.Should().BeGreaterThanOrEqualTo(before);
        time.Should().BeLessThanOrEqualTo(after);
    }
    
    [Fact]
    public void GetDeltaTime_ShouldReturnPositiveValue()
    {
        // Arrange
        var adapter = new GodotTimeAdapter();
        
        // Act
        var delta = adapter.GetDeltaTime();
        
        // Assert
        delta.Should().BeGreaterThanOrEqualTo(0);
    }
}
```

---

## 11.8 Headless 测试运行脚本

### 11.8.1 GdUnit4 Headless 测试运行

**PowerShell 脚本** (`scripts/run-gut-tests.ps1`):

```powershell
param(
    [string]$ProjectRoot = "C:\buildgame\godotgame",
    [switch]$Headless = $true,
    [string]$TestFilter = ""
)

Write-Host "运行 GdUnit4 场景集成测试..." -ForegroundColor Green

$godotExe = "godot"
$projectPath = $ProjectRoot

# 构建 Godot 命令
$godotArgs = @(
    "--path", $projectPath,
    "-s", "addons/gut/runner.py"
)

# 如果指定了测试过滤器
if ($TestFilter) {
    $godotArgs += "-p", $TestFilter
}

# Headless 模式
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

exit $lastExitCode
```

### 11.8.2 xUnit 测试运行

**PowerShell 脚本** (`scripts/run-xunit-tests.ps1`):

```powershell
param(
    [string]$ProjectRoot = "C:\buildgame\godotgame",
    [string]$Configuration = "Debug"
)

Write-Host "运行 xUnit 单元测试..." -ForegroundColor Green

$coreTestsPath = Join-Path $ProjectRoot "Game.Core.Tests"

# 运行测试并收集覆盖率
Write-Host "执行: dotnet test --configuration $Configuration --collect:""XPlat Code Coverage""" -ForegroundColor Gray

Push-Location $coreTestsPath
dotnet test --configuration $Configuration --collect:"XPlat Code Coverage"
$testExitCode = $LASTEXITCODE
Pop-Location

if ($testExitCode -eq 0) {
    Write-Host "PASS: xUnit 测试通过" -ForegroundColor Green
} else {
    Write-Host "FAIL: xUnit 测试失败" -ForegroundColor Red
}

exit $testExitCode
```

---

## 11.9 CI 集成工作流

**GitHub Actions** (`.github/workflows/scene-integration-tests.yml`):

```yaml
name: Scene Integration Tests (GdUnit4 + xUnit)

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  xunit-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: 设置 .NET
        uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '8.0'
      
      - name: 运行 xUnit 测试
        run: .\scripts\run-xunit-tests.ps1
      
      - name: 上传覆盖率
        uses: codecov/codecov-action@v3
        with:
          files: ./Game.Core.Tests/coverage.xml

  gut-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: 安装 Godot 4.5
        run: |
          # Godot 安装逻辑（根据项目配置）
          Write-Host "Godot 安装步骤"
      
      - name: 安装 GdUnit4
        run: .\scripts\install-gut.ps1
      
      - name: 运行 GdUnit4 测试
        run: .\scripts\run-gut-tests.ps1 -Headless
      
      - name: 上传 GdUnit4 报告
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: gut-reports
          path: ./addons/gut/reports/
```

---

## 11.10 完成清单

- [ ] 安装并配置 GdUnit4 框架
- [ ] 编写 MainScene GdUnit4 测试（≥4 个测试）
- [ ] 编写 GameScene GdUnit4 测试（≥5 个测试）
- [ ] 编写 EventBus GdUnit4 测试（≥4 个测试）
- [ ] 编写端到端流程 GdUnit4 测试
- [ ] 编写适配层 xUnit 测试
- [ ] 验证所有 GdUnit4 测试通过（100% 通过率）
- [ ] 验证所有 xUnit 测试通过（覆盖率 ≥90%）
- [ ] 集成到 CI 流程
- [ ] 生成测试报告（GdUnit4 + xUnit）

**完成标志**:

```bash
# GdUnit4 测试
.\scripts\run-gut-tests.ps1 -Headless
# 输出：PASS GdUnit4 测试通过

# xUnit 测试
.\scripts\run-xunit-tests.ps1
# 输出：PASS xUnit 测试通过
# 覆盖率: ≥90% 行 / ≥85% 分支
```

---

## 11.11 改进点总结

**相对原 Phase 11 的改进点**：
1. GdUnit4 替代 GdUnit4（更轻量、更 Godot 原生）
2. Headless 支持天生一等公民
3. 双轨框架清晰分工（xUnit 逻辑 + GdUnit4 场景）
4. CI 成本更低，速度更快
5. 融合 cifix1.txt 的建议

---

## 11.12 后续 Phase

**Phase 12: Headless 冒烟测试**
- 启动/退出稳定性测试
- 外链白名单验证
- 信号流程基准测试


---

## 附录：Python 等效（xUnit 最小示例）

为便于无需 PowerShell 即可在 Windows 上运行 xUnit 并收集覆盖率，提供以下最小 Python 示例：

```python
# scripts/run_xunit_tests.py
import subprocess, pathlib

def main() -> int:
    log = pathlib.Path('logs/ci')
    log.mkdir(parents=True, exist_ok=True)
    cmd = [
        'dotnet','test','Game.Core.Tests',
        '--configuration','Release','--no-build',
        '--logger', f"trx;LogFileName={log/'xunit-results.trx'}",
        '--collect:XPlat Code Coverage;Format=opencover;FileName=' + str(log/'xunit-coverage.xml')
    ]
    print('>', ' '.join(cmd))
    subprocess.check_call(cmd)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
```


---

## 附录：GdUnit4 C# 场景测试等效示例

以下示例将原 GUT（GDScript）测试逐段替换为 C# 场景测试写法。

### A. MainSceneTests.cs — 场景初始化与 UI 可见性
```csharp
// Game.Godot.Tests/Scenes/MainSceneTests.cs
using Godot;
using System.Threading.Tasks;

public partial class MainSceneTests : Node
{
    public override async void _Ready()
    {
        await Test_SceneReady_InitializesUi();
        await Test_PlayButton_Emits_GameStartRequested();
        await Test_SettingsButton_Shows_SettingsPanel();
        await Test_BackButton_Hides_SettingsPanel();
        GetTree().Quit();
    }

    private async Task<Node> LoadSceneAsync(string path)
    {
        var scene = GD.Load<PackedScene>(path);
        if (scene == null) throw new System.Exception($"Scene not found: {path}");
        var instance = scene.Instantiate();
        AddChild(instance);
        await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        return instance;
    }

    public async Task Test_SceneReady_InitializesUi()
    {
        var main = await LoadSceneAsync("res://Game.Godot/Scenes/MainScene.tscn");
        var mainMenu = main.GetNode<Control>("UI/MainMenu");
        var playBtn = main.GetNode<Button>("UI/MainMenu/PlayButton");
        var settingsBtn = main.GetNode<Button>("UI/MainMenu/SettingsButton");
        if (!mainMenu.Visible || !playBtn.Visible || !settingsBtn.Visible)
            throw new System.Exception("Main menu or buttons not visible");
        main.QueueFree();
    }

    public async Task Test_PlayButton_Emits_GameStartRequested()
    {
        var main = await LoadSceneAsync("res://Game.Godot/Scenes/MainScene.tscn");
        bool received = false;
        main.Connect("game_start_requested", new Callable(this, nameof(OnGameStartRequested)));
        void OnGameStartRequested() => received = true;
        var playBtn = main.GetNode<Button>("UI/MainMenu/PlayButton");
        playBtn.EmitSignal(Button.SignalName.Pressed);
        await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        if (!received) throw new System.Exception("game_start_requested not emitted");
        main.QueueFree();
    }

    public async Task Test_SettingsButton_Shows_SettingsPanel()
    {
        var main = await LoadSceneAsync("res://Game.Godot/Scenes/MainScene.tscn");
        var settingsBtn = main.GetNode<Button>("UI/MainMenu/SettingsButton");
        var settingsPanel = main.GetNode<Control>("UI/SettingsPanel");
        settingsBtn.EmitSignal(Button.SignalName.Pressed);
        await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        if (!settingsPanel.Visible) throw new System.Exception("Settings panel not visible");
        main.QueueFree();
    }

    public async Task Test_BackButton_Hides_SettingsPanel()
    {
        var main = await LoadSceneAsync("res://Game.Godot/Scenes/MainScene.tscn");
        var settingsBtn = main.GetNode<Button>("UI/MainMenu/SettingsButton");
        var settingsPanel = main.GetNode<Control>("UI/SettingsPanel");
        var backBtn = settingsPanel.GetNode<Button>("BackButton");
        settingsBtn.EmitSignal(Button.SignalName.Pressed);
        await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        backBtn.EmitSignal(Button.SignalName.Pressed);
        await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        if (settingsPanel.Visible) throw new System.Exception("Settings panel not hidden");
        main.QueueFree();
    }
}
```

### B. GameSceneTests.cs — 场景稳定性与若干帧运行
```csharp
// Game.Godot.Tests/Scenes/GameSceneTests.cs
using Godot;
using System.Threading.Tasks;

public partial class GameSceneTests : Node
{
    public override async void _Ready()
    {
        await Test_GameScene_Stability_RunsSeveralFrames();
        GetTree().Quit();
    }

    public async Task Test_GameScene_Stability_RunsSeveralFrames()
    {
        var scene = GD.Load<PackedScene>("res://Game.Godot/Scenes/GameScene.tscn");
        if (scene == null) throw new System.Exception("GameScene not found");
        var inst = scene.Instantiate();
        AddChild(inst);
        for (int i = 0; i < 10; i++)
            await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        if (!inst.IsInsideTree()) throw new System.Exception("GameScene not inside tree");
        inst.QueueFree();
    }
}
```

### C. SignalsTests.cs — 信号连通性验证
```csharp
// Game.Godot.Tests/Signals/SignalsTests.cs
using Godot;
using System.Threading.Tasks;

public partial class SignalsTests : Node
{
    public override async void _Ready()
    {
        await Test_SignalConnectivity_ThroughEventBus();
        GetTree().Quit();
    }

    public async Task Test_SignalConnectivity_ThroughEventBus()
    {
        var main = GD.Load<PackedScene>("res://Game.Godot/Scenes/MainScene.tscn").Instantiate();
        AddChild(main);
        bool received = false;
        main.Connect("game_start_requested", new Callable(this, nameof(OnGameStartRequested)));
        void OnGameStartRequested() => received = true;
        var playBtn = main.GetNode<Button>("UI/MainMenu/PlayButton");
        playBtn.EmitSignal(Button.SignalName.Pressed);
        await ToSignal(GetTree(), SceneTree.SignalName.ProcessFrame);
        if (!received) throw new System.Exception("Signal not received");
        main.QueueFree();
    }
}
```


> 参考 Runner 接入指南：见 docs/migration/gdunit4-csharp-runner-integration.md。
