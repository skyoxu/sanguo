# Phase 11: 鍦烘櫙闆嗘垚娴嬭瘯锛圙dUnit4 + xUnit 鍙岃建锛?

**闃舵鐩爣**: 寤虹珛瀹屾暣鐨?Godot 鍦烘櫙闆嗘垚娴嬭瘯妗嗘灦锛岄噰鐢?**GdUnit4**锛圙odot 鍘熺敓锛? **xUnit**锛圕# 棰嗗煙閫昏緫锛夊弻杞ㄦ柟妗堬紝閬垮厤閲嶅瀷 GdUnit4 渚濊禆

**宸ヤ綔閲?*: 8-10 浜哄ぉ  
**椋庨櫓绛夌骇**: 浣庯紙GdUnit4 杞婚噺锛寈Unit 绀惧尯鎴愮啛锛? 
**渚濊禆**: Phase 8锛堝満鏅璁★級銆丳hase 10锛坸Unit 鍗曞厓娴嬭瘯锛? 
**鍚庣画渚濊禆**: Phase 12锛圗2E Headless 鍐掔儫娴嬭瘯锛?

---

## 11.1 妗嗘灦閫夊瀷涓庢灦鏋?

### 11.1.1 涓轰粈涔堥€?GdUnit4 鑰岄潪 GdUnit4

| 瀵规瘮椤?| GdUnit4 | GdUnit4 |
|--------|-----|---------|
| **瀛︿範鏇茬嚎** | 浣庯紙Godot 鍘熺敓锛?| 楂橈紙鐙珛妗嗘灦锛?|
| **Headless 鏀寔** | 鍘熺敓鏀寔 | 闇€棰濆閰嶇疆 |
| **CI 閫傞厤** | Headless 鍙嬪ソ | 闇€瑕侀澶栭┍鍔?|
| **GDScript 鍙嬪ソ** | 瀹屽叏鍘熺敓 | C# 閫傞厤涓嶅 GDScript |
| **渚濊禆绠＄悊** | 闆跺閮ㄤ緷璧?| 闇€鎵嬪姩 clone |
| **鎬ц兘** | 杞婚噺蹇€?| 杈冮噸 |

**缁撹**: 閲囩敤 GdUnit4 浣滀负鍦烘櫙绾ф祴璇曚富鍔涳紝xUnit 璐熻矗 Game.Core 棰嗗煙閫昏緫銆?
### Godot+C# 鍙樹綋锛圱ests.Godot + GdUnit4 6.x锛?
- 鍦烘櫙/閫傞厤灞傛祴璇曢」鐩細`Tests.Godot`锛堢嫭绔?Godot 椤圭洰锛屽寘鍚?GdUnit4 鎻掍欢锛夈€?
#### 娴嬭瘯鍒嗙被涓庝唬琛ㄧ敤渚?
| 闆嗗悎 | 鐩綍 | 璇存槑 | 浠ｈ〃鎬х敤渚?|
|------|------|------|------------|
| Adapters | `tests/Adapters/**` | Db銆丆onfig銆丗eatureFlags 绛夐€傞厤灞傝涓轰笌璺ㄩ噸鍚涔?| `tests/Adapters/test_data_store_adapter.gd` |
| Security | `tests/Security/Hard/**` | DB/Settings 璺緞瀹夊叏涓庡璁?| `tests/Security/test_db_audit_log.gd` |
| Integration | `tests/Integration/**` | ScreenNavigator銆丠UD銆丼ettings 浜嬩欢閾句笌淇″彿杩為€?| `tests/Integration/test_screen_navigation_flow.gd`銆乣tests/Integration/test_settings_event_integration.gd` |
| UI/Glue | `tests/UI/**` | MainMenu/HUD/SettingsPanel 绛?UI/Glue 琛屼负 | `tests/UI/test_main_menu_settings_button.gd`銆乣tests/UI/test_hud_updates_on_events.gd` |

#### 杩愯鏂瑰紡

- 鏈湴涓?CI 鍧囬€氳繃 Python 鑴氭湰 `scripts/python/run_gdunit.py` 椹卞姩 Godot Headless锛?  - 绀轰緥锛歚py -3 -E -X utf8 scripts/python/run_gdunit.py --prewarm --godot-bin "C:\\Godot\\Godot_v4.5.1-stable_mono_win64_console.exe" --project Tests.Godot --add tests/Adapters --add tests/Security/Hard --timeout-sec 600 --rd "logs/e2e/<date>/gdunit-reports"`銆?  - GdUnit4 鎻掍欢鍦?`Tests.Godot/addons/gdUnit4` 涓?vendored锛岀敱 `scripts/python/ensure_gdunit_plugin.py` 鍦?CI 涓厹搴曟牎楠屻€?
#### CI 闆嗘垚

- Windows CI锛堢‖闂ㄧ锛夛細鍦?`.github/workflows/ci-windows.yml` 涓皟鐢?`ci_pipeline.py` 璺?xUnit + Adapters/Security 灏忛泦锛?- Windows Quality Gate锛堣蒋闂ㄧ锛夛細鍦?`.github/workflows/windows-quality-gate.yml` 涓窇 Integration/UI/Db/A11y 灏忛泦锛屽苟涓婁紶 GdUnit4 鎶ュ憡銆?
### 11.1.2 鍙岃建娴嬭瘯鏋舵瀯

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?                   Quality Gates                         鈹?
鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?xUnit (Game.Core)     鈹?     GdUnit4 (Game.Godot Scenes)   鈹?
鈹?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€     鈹?     鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€     鈹?
鈹?鈥?鍩熼€昏緫锛堢孩缁跨伅锛?    鈹?鈥?鍦烘櫙鍔犺浇/鍒濆鍖?            鈹?
鈹?鈥?100% 鐙珛 Godot     鈹?鈥?Signal 杩為€氭€?              鈹?
鈹?鈥?瑕嗙洊鐜?鈮?0% 琛?     鈹?鈥?鑺傜偣浜や簰妯℃嫙                鈹?
鈹?鈥?杩愯鏃?<5绉?        鈹?鈥?鍦烘櫙杞崲楠岃瘉                鈹?
鈹?鈥?Headless 鍘熺敓      鈹?鈥?Headless 鍘熺敓              鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
```

---

## 11.2 GdUnit4 妗嗘灦闆嗘垚涓庤缃?

### 11.2.1 瀹夎 GdUnit4

> 璇存槑锛氬綋鍓嶄粨搴撳凡鍦?`Tests.Godot/addons/gdUnit4` 涓洿鎺ュ寘鍚?GdUnit4 鎻掍欢锛屽苟閫氳繃
> `scripts/python/ensure_gdunit_plugin.py` 鍦?CI 涓仛鍏滃簳鏍￠獙銆備笅闈㈢殑瀹夎鑴氭湰涓?Gut 鐩稿叧
> 閰嶇疆淇濈暀涓哄巻鍙茬ず渚嬶紝鐢ㄤ簬璇存槑濡備綍鍦ㄥ叾浠栭」鐩腑浠庨浂闆嗘垚娴嬭瘯妗嗘灦锛涙湰椤圭洰瀹為檯杩愯
> 鏃朵紭鍏堜娇鐢?Tests.Godot 鐜版湁缁撴瀯涓?Python runner銆?
**Python 瀹夎鑴氭湰锛堝巻鍙茬ず渚嬶級** (`scripts/install_gut.py`):

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

杩愯绀轰緥锛圵indows锛夛細

```
py -3 scripts/install_gut.py C:\buildgame\sanguo
```

### 11.2.2 椤圭洰閰嶇疆

**project.godot 閰嶇疆**锛?

```ini
[addons]

gut/enabled=true
gut/runner_scene=res://addons/gut/runner.tscn

[gut]

# GdUnit4 閰嶇疆
print_tests=true
print_summary=true
tests_like_name_containing=Test
```

### 11.2.3 GdUnit4 鍩虹娴嬭瘯绫?

**GdUnit4 鍩虹被** (`Game.Godot/Tests/GutTestBase.cs`):

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

## 11.3 涓诲満鏅泦鎴愭祴璇曪紙GdUnit4锛?

### 11.3.1 MainScene 娴嬭瘯

**娴嬭瘯鏂囦欢** (`Game.Godot/Tests/Scenes/MainSceneTest.cs`):

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

## 11.4 娓告垙鍦烘櫙闆嗘垚娴嬭瘯锛圙dUnit4锛?

### 11.4.1 GameScene 娴嬭瘯

**娴嬭瘯鏂囦欢** (`Game.Godot/Tests/Scenes/GameSceneTest.cs`):

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

## 11.5 Signal 绯荤粺娴嬭瘯锛圙dUnit4锛?

### 11.5.1 EventBus 娴嬭瘯

**娴嬭瘯鏂囦欢** (`Game.Godot/Tests/Systems/EventBusTest.cs`):

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

## 11.6 瀹屾暣娴佺▼闆嗘垚娴嬭瘯锛圙dUnit4锛?

### 11.6.1 绔埌绔満鏅祦绋?

**娴嬭瘯鏂囦欢** (`Game.Godot/Tests/Scenes/FullFlowTest.cs`):

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

## 11.7 xUnit 棰嗗煙閫昏緫琛ュ厖娴嬭瘯

**閲嶈**: Game.Core 涓殑绾€昏緫鐢?**Phase 10** 鐨?xUnit 璐熻矗锛岃繖閲屼粎琛ュ厖 Godot 閫傞厤灞傛祴璇曘€?

### 11.7.1 閫傞厤灞傚绾︽祴璇?

**娴嬭瘯鏂囦欢** (`Game.Core.Tests/Adapters/GodotTimeAdapterTests.cs`):

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

## 11.8 Headless 娴嬭瘯杩愯鑴氭湰

### 11.8.1 GdUnit4 Headless 娴嬭瘯杩愯

**PowerShell 鑴氭湰** (`scripts/run-gut-tests.ps1`):

```powershell
param(
    [string]$ProjectRoot = "C:\buildgame\sanguo",
    [switch]$Headless = $true,
    [string]$TestFilter = ""
)

Write-Host "杩愯 GdUnit4 鍦烘櫙闆嗘垚娴嬭瘯..." -ForegroundColor Green

$godotExe = "godot"
$projectPath = $ProjectRoot

# 鏋勫缓 Godot 鍛戒护
$godotArgs = @(
    "--path", $projectPath,
    "-s", "addons/gut/runner.py"
)

# 濡傛灉鎸囧畾浜嗘祴璇曡繃婊ゅ櫒
if ($TestFilter) {
    $godotArgs += "-p", $TestFilter
}

# Headless 妯″紡
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

exit $lastExitCode
```

### 11.8.2 xUnit 娴嬭瘯杩愯

**PowerShell 鑴氭湰** (`scripts/run-xunit-tests.ps1`):

```powershell
param(
    [string]$ProjectRoot = "C:\buildgame\sanguo",
    [string]$Configuration = "Debug"
)

Write-Host "杩愯 xUnit 鍗曞厓娴嬭瘯..." -ForegroundColor Green

$coreTestsPath = Join-Path $ProjectRoot "Game.Core.Tests"

# 杩愯娴嬭瘯骞舵敹闆嗚鐩栫巼
Write-Host "鎵ц: dotnet test --configuration $Configuration --collect:""XPlat Code Coverage""" -ForegroundColor Gray

Push-Location $coreTestsPath
dotnet test --configuration $Configuration --collect:"XPlat Code Coverage"
$testExitCode = $LASTEXITCODE
Pop-Location

if ($testExitCode -eq 0) {
    Write-Host "PASS: xUnit 娴嬭瘯閫氳繃" -ForegroundColor Green
} else {
    Write-Host "FAIL: xUnit 娴嬭瘯澶辫触" -ForegroundColor Red
}

exit $testExitCode
```

---

## 11.9 CI 闆嗘垚宸ヤ綔娴?
### 11.9.1 褰撳墠 Windows CI 宸ヤ綔娴侊紙Godot+C# 鍙樹綋锛?
- **Windows CI锛堢‖闂ㄧ锛?*锛歚.github/workflows/ci-windows.yml`
  - 浣跨敤 `scripts/python/ci_pipeline.py` 璺戯細
    - Game.Core xUnit 鍗曞厓娴嬭瘯锛堝惈 coverlet 瑕嗙洊鐜囷級锛?    - Tests.Godot 涓殑 Adapters/Security GdUnit4 灏忛泦锛堥€氳繃 `run_gdunit.py`锛夛紱
    - 缂栫爜鎵弿绛夊熀纭€闂ㄧ銆?- **Windows Quality Gate锛堣蒋闂ㄧ锛?*锛歚.github/workflows/windows-quality-gate.yml`
  - 鍚屾牱閫氳繃 `ci_pipeline.py`/`run_gdunit.py` 璺?Integration/UI/Db/A11y 闆嗘垚娴嬭瘯锛?    骞跺皢 GdUnit4 鎶ュ憡涓婁紶鍒?`logs/e2e/<run_id>/gdunit-reports/**` 浣滀负宸ヤ欢銆?- 浠ヤ笂宸ヤ綔娴佸潎涓?Windows-only锛屼娇鐢?Python 鑰屼笉鏄?PowerShell 鑴氭湰浣滀负缁熶竴鍏ュ彛銆?
### 11.9.2 绀轰緥宸ヤ綔娴侊紙鍘嗗彶鏂规锛?
> 涓嬪垪鍩轰簬 `scene-integration-tests.yml`銆乣run-gut-tests.ps1`/`run-xunit-tests.ps1` 鐨勯厤缃?> 淇濈暀涓烘蹇电ず渚嬶紝鐢ㄤ簬璇存槑濡備綍鍦ㄥ叾浠栭」鐩腑缁勫悎 xUnit + GdUnit4銆傚綋鍓嶄粨搴撳疄闄呬娇鐢ㄧ殑
> 鏄笂鏂囨墍杩扮殑 `ci-windows.yml` 涓?`windows-quality-gate.yml`銆?
**GitHub Actions锛堢ず鎰忥級** (`.github/workflows/scene-integration-tests.yml`):

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
      
      - name: 璁剧疆 .NET
        uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '8.0'
      
      - name: 杩愯 xUnit 娴嬭瘯
        run: .\scripts\run-xunit-tests.ps1
      
      - name: 涓婁紶瑕嗙洊鐜?
        uses: codecov/codecov-action@v3
        with:
          files: ./Game.Core.Tests/coverage.xml

  gut-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: 瀹夎 Godot 4.5
        run: |
          # Godot 瀹夎閫昏緫锛堟牴鎹」鐩厤缃級
          Write-Host "Godot 瀹夎姝ラ"
      
      - name: 瀹夎 GdUnit4
        run: .\scripts\install-gut.ps1
      
      - name: 杩愯 GdUnit4 娴嬭瘯
        run: .\scripts\run-gut-tests.ps1 -Headless
      
      - name: 涓婁紶 GdUnit4 鎶ュ憡
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: gut-reports
          path: ./addons/gut/reports/
```

---

## 11.10 瀹屾垚娓呭崟

- [ ] 瀹夎骞堕厤缃?GdUnit4 妗嗘灦
- [ ] 缂栧啓 MainScene GdUnit4 娴嬭瘯锛堚墺4 涓祴璇曪級
- [ ] 缂栧啓 GameScene GdUnit4 娴嬭瘯锛堚墺5 涓祴璇曪級
- [ ] 缂栧啓 EventBus GdUnit4 娴嬭瘯锛堚墺4 涓祴璇曪級
- [ ] 缂栧啓绔埌绔祦绋?GdUnit4 娴嬭瘯
- [ ] 缂栧啓閫傞厤灞?xUnit 娴嬭瘯
- [ ] 楠岃瘉鎵€鏈?GdUnit4 娴嬭瘯閫氳繃锛?00% 閫氳繃鐜囷級
- [ ] 楠岃瘉鎵€鏈?xUnit 娴嬭瘯閫氳繃锛堣鐩栫巼 鈮?0%锛?
- [ ] 闆嗘垚鍒?CI 娴佺▼
- [ ] 鐢熸垚娴嬭瘯鎶ュ憡锛圙dUnit4 + xUnit锛?

**瀹屾垚鏍囧織**:

```bash
# GdUnit4 娴嬭瘯
.\scripts\run-gut-tests.ps1 -Headless
# 杈撳嚭锛歅ASS GdUnit4 娴嬭瘯閫氳繃

# xUnit 娴嬭瘯
.\scripts\run-xunit-tests.ps1
# 杈撳嚭锛歅ASS xUnit 娴嬭瘯閫氳繃
# 瑕嗙洊鐜? 鈮?0% 琛?/ 鈮?5% 鍒嗘敮
```

---

## 11.11 鏀硅繘鐐规€荤粨

**鐩稿鍘?Phase 11 鐨勬敼杩涚偣**锛?
1. GdUnit4 鏇夸唬 GdUnit4锛堟洿杞婚噺銆佹洿 Godot 鍘熺敓锛?
2. Headless 鏀寔澶╃敓涓€绛夊叕姘?
3. 鍙岃建妗嗘灦娓呮櫚鍒嗗伐锛坸Unit 閫昏緫 + GdUnit4 鍦烘櫙锛?
4. CI 鎴愭湰鏇翠綆锛岄€熷害鏇村揩
5. 铻嶅悎 cifix1.txt 鐨勫缓璁?

---

## 11.12 鍚庣画 Phase

**Phase 12: Headless 鍐掔儫娴嬭瘯**
- 鍚姩/閫€鍑虹ǔ瀹氭€ф祴璇?
- 澶栭摼鐧藉悕鍗曢獙璇?
- 淇″彿娴佺▼鍩哄噯娴嬭瘯


---

## 闄勫綍锛歅ython 绛夋晥锛坸Unit 鏈€灏忕ず渚嬶級

涓轰究浜庢棤闇€ PowerShell 鍗冲彲鍦?Windows 涓婅繍琛?xUnit 骞舵敹闆嗚鐩栫巼锛屾彁渚涗互涓嬫渶灏?Python 绀轰緥锛?

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

## 闄勫綍锛欸dUnit4 C# 鍦烘櫙娴嬭瘯绛夋晥绀轰緥

浠ヤ笅绀轰緥灏嗗師 GUT锛圙DScript锛夋祴璇曢€愭鏇挎崲涓?C# 鍦烘櫙娴嬭瘯鍐欐硶銆?

### A. MainSceneTests.cs 鈥?鍦烘櫙鍒濆鍖栦笌 UI 鍙鎬?
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

### B. GameSceneTests.cs 鈥?鍦烘櫙绋冲畾鎬т笌鑻ュ共甯ц繍琛?
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

### C. SignalsTests.cs 鈥?淇″彿杩為€氭€ч獙璇?
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


> 鍙傝€?Runner 鎺ュ叆鎸囧崡锛氳 docs/migration/gdunit4-csharp-runner-integration.md銆?

