# Phase 3: Godot 项目结构设计

> 状态: 设计阶段
> 预估工时: 1 天
> 风险等级: 低
> 前置条件: Phase 1-2 完成

---

## 目标

建立 Godot 4.5 + C# 项目的标准目录结构，遵循端口适配器模式，支持 TDD 开发。

---

## 项目根目录结构

```
godotgame/                              # 新项目根目录
├── .git/                               # Git 仓库
├── .gitignore                          # Git 忽略规则
├── .gitattributes                      # Git 文件属性
├── project.godot                       # Godot 项目配置文件
├── export_presets.cfg                  # 导出预设配置
├── icon.svg                            # 项目图标
├── Game.sln                            # Visual Studio 解决方案
│
├── Game.Core/                          # 纯 C# 领域层（不依赖 Godot）
│   ├── Game.Core.csproj
│   ├── Domain/
│   │   ├── Entities/
│   │   ├── ValueObjects/
│   │   └── Services/
│   ├── Ports/                          # 接口定义
│   └── Utilities/
│
├── Game.Core.Tests/                    # xUnit 单元测试
│   ├── Game.Core.Tests.csproj
│   ├── Domain/
│   ├── Fakes/                          # Fake 实现（测试用）
│   └── TestHelpers/
│
├── Game.Godot/                         # Godot 场景与脚本
│   ├── .godot/                         # Godot 缓存（Git 忽略）
│   ├── Scenes/                         # 场景文件 (.tscn)
│   ├── Scripts/                        # C# 脚本（薄层控制器）
│   ├── Autoloads/                      # 全局单例
│   ├── Adapters/                       # Godot API 适配层
│   ├── Resources/                      # 资源定义 (.tres)
│   ├── Themes/                         # UI 主题
│   └── Assets/                         # 美术资产
│       ├── Textures/
│       ├── Fonts/
│       ├── Audio/
│       └── Models/
│
├── Game.Godot.Tests/                   # GdUnit4 场景测试
│   ├── Scenes/
│   ├── Scripts/
│   └── E2E/
│
├── docs/                               # 项目文档
│   ├── adr/                            # ADR 记录
│   ├── architecture/                   # 架构文档
│   ├── contracts/                      # 契约文档
│   │   └── signals/                    # Signal 契约
│   └── migration/                      # 迁移文档（本系列）
│
├── scripts/                            # 构建与工具脚本
│   ├── ci/                             # CI/CD 脚本
│   ├── python/                         # Python 工具
│   └── godot/                          # Godot 辅助脚本
│
├── logs/                               # 日志输出目录（Git 忽略）
│   ├── ci/
│   ├── security/
│   └── performance/
│
└── TestResults/                        # 测试结果（Git 忽略）
    ├── coverage/
    └── gdunit4/
```

---

## Game.Core 项目详细结构

```
Game.Core/
├── Game.Core.csproj
│
├── Domain/
│   ├── Entities/                       # 领域实体（有标识的可变对象）
│   │   ├── Player.cs
│   │   ├── Enemy.cs
│   │   ├── Item.cs
│   │   └── GameSession.cs
│   │
│   ├── ValueObjects/                   # 值对象（不可变）
│   │   ├── Position.cs
│   │   ├── Vector2D.cs
│   │   ├── Health.cs
│   │   ├── Damage.cs
│   │   ├── Score.cs
│   │   └── ItemQuantity.cs
│   │
│   ├── Services/                       # 领域服务（跨实体逻辑）
│   │   ├── CombatService.cs
│   │   ├── InventoryService.cs
│   │   ├── ScoreService.cs
│   │   └── CollisionService.cs
│   │
│   └── Events/                         # 领域事件（可选）
│       ├── PlayerHealthChanged.cs
│       └── EnemyDefeated.cs
│
├── Ports/                              # 端口接口（依赖倒置）
│   ├── ITime.cs                        # 时间服务
│   ├── IInput.cs                       # 输入服务
│   ├── IResourceLoader.cs              # 资源加载
│   ├── IDataStore.cs                   # 数据存储
│   ├── IAudioPlayer.cs                 # 音频播放
│   └── ILogger.cs                      # 日志服务
│
└── Utilities/                          # 工具类（纯函数）
    ├── MathHelper.cs
    ├── RandomHelper.cs
    └── StringHelper.cs
```

**Game.Core.csproj 示例**:

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <LangVersion>latest</LangVersion>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
  </PropertyGroup>

  <!-- 禁止引用 Godot 相关包 -->
  <ItemGroup>
    <PackageReference Include="System.Text.Json" Version="8.0.0" />
  </ItemGroup>

</Project>
```

---

## Game.Core.Tests 项目结构

```
Game.Core.Tests/
├── Game.Core.Tests.csproj
│
├── Domain/
│   ├── Entities/
│   │   ├── PlayerTests.cs
│   │   ├── EnemyTests.cs
│   │   └── ItemTests.cs
│   │
│   ├── Services/
│   │   ├── CombatServiceTests.cs
│   │   ├── InventoryServiceTests.cs
│   │   └── ScoreServiceTests.cs
│   │
│   └── ValueObjects/
│       ├── HealthTests.cs
│       └── DamageTests.cs
│
├── Fakes/                              # Fake 实现（测试用）
│   ├── FakeTime.cs
│   ├── FakeInput.cs
│   ├── FakeDataStore.cs
│   └── FakeLogger.cs
│
└── TestHelpers/
    ├── TestDataBuilder.cs              # 测试数据构建器
    └── AssertionExtensions.cs          # 自定义断言
```

**Game.Core.Tests.csproj 示例**:

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="xunit" Version="2.6.0" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.5.0" />
    <PackageReference Include="FluentAssertions" Version="6.12.0" />
    <PackageReference Include="NSubstitute" Version="5.1.0" />
    <PackageReference Include="coverlet.collector" Version="6.0.0" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.8.0" />
  </ItemGroup>

  <ItemGroup>
    <ProjectReference Include="..\Game.Core\Game.Core.csproj" />
  </ItemGroup>

</Project>
```

---

## Game.Godot 项目结构

```
Game.Godot/
├── project.godot                       # Godot 项目配置
├── export_presets.cfg                  # 导出配置
│
├── Scenes/                             # 场景文件
│   ├── Main.tscn                       # 主场景
│   ├── UI/
│   │   ├── MainMenu.tscn
│   │   ├── HUD.tscn
│   │   └── SettingsMenu.tscn
│   ├── Game/
│   │   ├── Player.tscn
│   │   ├── Enemy.tscn
│   │   └── Item.tscn
│   └── Levels/
│       ├── Level1.tscn
│       └── Level2.tscn
│
├── Scripts/                            # C# 脚本（薄层控制器）
│   ├── PlayerController.cs             # Node 生命周期 + Signal 转发
│   ├── EnemyController.cs
│   ├── UIController.cs
│   └── CameraController.cs
│
├── Autoloads/                          # 全局单例（自动加载）
│   ├── ServiceLocator.cs               # DI 容器
│   ├── Security.cs                     # 安全封装（GDScript）
│   ├── Observability.cs                # Sentry + 日志
│   └── EventBus.cs                     # 全局事件总线
│
├── Adapters/                           # Godot API 适配层
│   ├── GodotTimeAdapter.cs
│   ├── GodotInputAdapter.cs
│   ├── GodotResourceLoader.cs
│   ├── GodotAudioPlayer.cs
│   ├── SqliteDataStore.cs
│   └── GodotLogger.cs
│
├── Resources/                          # 资源定义文件
│   ├── player_stats.tres
│   └── enemy_config.tres
│
├── Themes/                             # UI 主题
│   ├── default_theme.tres
│   └── button_styles.tres
│
└── Assets/                             # 美术资产
    ├── Textures/
    │   ├── player.png
    │   └── enemy.png
    ├── Fonts/
    │   └── main_font.ttf
    ├── Audio/
    │   ├── bgm.ogg
    │   └── sfx_hit.wav
    └── Shaders/
        └── outline.gdshader
```

---

## Godot 项目配置文件

### project.godot

```ini
; Engine configuration file.

config_version=5

[application]

config/name="Game"
run/main_scene="res://Scenes/Main.tscn"
config/features=PackedStringArray("4.5", "C#", "Forward Plus")
config/icon="res://icon.svg"

[autoload]

ServiceLocator="*res://Autoloads/ServiceLocator.cs"
Security="*res://Autoloads/Security.cs"
Observability="*res://Autoloads/Observability.cs"
EventBus="*res://Autoloads/EventBus.cs"

[display]

window/size/viewport_width=1280
window/size/viewport_height=720
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"

[dotnet]

project/assembly_name="Game.Godot"

[file_customization]

folder_colors={
"res://Adapters/": "blue",
"res://Autoloads/": "yellow",
"res://Scenes/": "green",
"res://Scripts/": "purple"
}

[input]

move_up={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":87,"key_label":0,"unicode":119,"echo":false,"script":null)
]
}

[physics]

2d/default_gravity=980.0
```

### export_presets.cfg

```ini
[preset.0]

name="Windows Desktop"
platform="Windows Desktop"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="build/Game.exe"
encryption_include_filters=""
encryption_exclude_filters=""
encrypt_pck=false
encrypt_directory=false

[preset.0.options]

custom_template/debug=""
custom_template/release=""
debug/export_console_wrapper=1
binary_format/embed_pck=false
texture_format/bptc=true
texture_format/s3tc=true
texture_format/etc=false
texture_format/etc2=false
binary_format/architecture="x86_64"
codesign/enable=false
codesign/timestamp=true
codesign/timestamp_server_url=""
codesign/digest_algorithm=1
codesign/description=""
codesign/custom_options=PackedStringArray()
application/modify_resources=true
application/icon=""
application/console_wrapper_icon=""
application/icon_interpolation=4
application/file_version=""
application/product_version=""
application/company_name=""
application/product_name="Game"
application/file_description=""
application/copyright=""
application/trademarks=""
application/export_angle=0
ssh_remote_deploy/enabled=false
ssh_remote_deploy/host="user@host_ip"
ssh_remote_deploy/port="22"
ssh_remote_deploy/extra_args_ssh=""
ssh_remote_deploy/extra_args_scp=""
ssh_remote_deploy/run_script="Expand-Archive -LiteralPath '{temp_dir}\\{archive_name}' -DestinationPath '{temp_dir}'
$action = New-ScheduledTaskAction -Execute '{temp_dir}\\{exe_name}' -Argument '{cmd_args}'
$trigger = New-ScheduledTaskTrigger -Once -At 00:00
$settings = New-ScheduledTaskSettingsSet
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings
Register-ScheduledTask godot_remote_debug -InputObject $task -Force:$true
Start-ScheduledTask -TaskName godot_remote_debug
while (Get-ScheduledTask -TaskName godot_remote_debug | ? State -eq running) { Start-Sleep -Milliseconds 100 }
Unregister-ScheduledTask -TaskName godot_remote_debug -Confirm:$false -ErrorAction:SilentlyContinue"
ssh_remote_deploy/cleanup_script="Stop-ScheduledTask -TaskName godot_remote_debug -ErrorAction:SilentlyContinue
Unregister-ScheduledTask -TaskName godot_remote_debug -Confirm:$false -ErrorAction:SilentlyContinue
Remove-Item -Recurse -Force '{temp_dir}'"
```

---

## Game.Godot.Tests 项目结构

```
Game.Godot.Tests/
├── addons/
│   └── gdUnit4/                        # GdUnit4 插件
│
├── Scenes/
│   ├── MainSceneTest.cs
│   ├── PlayerTest.cs
│   └── UITest.cs
│
├── Scripts/
│   ├── SignalTest.cs
│   └── AdapterTest.cs
│
└── E2E/
    ├── E2ERunner.tscn                  # E2E 测试运行器场景
    ├── E2ERunner.cs                    # E2E 测试脚本
    └── SmokeTests.cs                   # 冒烟测试
```

---

## Visual Studio 解决方案结构

**Game.sln**:

```
Microsoft Visual Studio Solution File, Format Version 12.00
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "Game.Core", "Game.Core\Game.Core.csproj", "{GUID-1}"
EndProject
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "Game.Core.Tests", "Game.Core.Tests\Game.Core.Tests.csproj", "{GUID-2}"
EndProject
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "Game.Godot", "Game.Godot\Game.Godot.csproj", "{GUID-3}"
EndProject
Global
    GlobalSection(SolutionConfigurationPlatforms) = preSolution
        Debug|Any CPU = Debug|Any CPU
        Release|Any CPU = Release|Any CPU
    EndGlobalSection
    GlobalSection(ProjectConfigurationPlatforms) = postSolution
        {GUID-1}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
        {GUID-1}.Release|Any CPU.ActiveCfg = Release|Any CPU
        {GUID-2}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
        {GUID-2}.Release|Any CPU.ActiveCfg = Release|Any CPU
        {GUID-3}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
        {GUID-3}.Release|Any CPU.ActiveCfg = Release|Any CPU
    EndGlobalSection
EndGlobal
```

---

## .gitignore

```gitignore
# Godot
.godot/
.mono/
data_*/
*.translation

# .NET
bin/
obj/
*.csproj.user
*.suo
*.cache
*.dll
*.exe
*.pdb

# Test & Coverage
TestResults/
coverage/
*.coverage
*.coveragexml

# Logs
logs/
*.log

# IDE
.vs/
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Build
build/
dist/
*.pck
```

---

## .gitattributes

```gitattributes
# Text files
*.cs text eol=lf
*.gd text eol=lf
*.tscn text eol=lf
*.tres text eol=lf
*.cfg text eol=lf
*.md text eol=lf
*.json text eol=lf
*.xml text eol=lf

# Binary files
*.png binary
*.jpg binary
*.ogg binary
*.wav binary
*.ttf binary
*.otf binary
```

---

## 初始化脚本

创建 PowerShell 脚本自动化项目初始化：

**scripts/init-godot-project.ps1**:

```powershell
# 项目初始化脚本

param(
    [string]$ProjectRoot = "C:\buildgame\sanguo"
)

Write-Host "开始初始化 Godot 项目..." -ForegroundColor Green

# 创建目录结构
$directories = @(
    "Game.Core/Domain/Entities",
    "Game.Core/Domain/ValueObjects",
    "Game.Core/Domain/Services",
    "Game.Core/Ports",
    "Game.Core/Utilities",
    "Game.Core.Tests/Domain/Entities",
    "Game.Core.Tests/Domain/Services",
    "Game.Core.Tests/Fakes",
    "Game.Core.Tests/TestHelpers",
    "Game.Godot/Scenes/UI",
    "Game.Godot/Scenes/Game",
    "Game.Godot/Scenes/Levels",
    "Game.Godot/Scripts",
    "Game.Godot/Autoloads",
    "Game.Godot/Adapters",
    "Game.Godot/Resources",
    "Game.Godot/Themes",
    "Game.Godot/Assets/Textures",
    "Game.Godot/Assets/Fonts",
    "Game.Godot/Assets/Audio",
    "Game.Godot.Tests/Scenes",
    "Game.Godot.Tests/Scripts",
    "Game.Godot.Tests/E2E",
    "docs/adr",
    "docs/architecture",
    "docs/contracts/signals",
    "docs/migration",
    "scripts/ci",
    "scripts/python",
    "scripts/godot",
    "logs/ci",
    "logs/security",
    "logs/performance"
)

foreach ($dir in $directories) {
    $fullPath = Join-Path $ProjectRoot $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "创建目录: $dir" -ForegroundColor Gray
    }
}

# 创建 .NET 项目
Write-Host "`n创建 .NET 项目..." -ForegroundColor Green

Push-Location $ProjectRoot

# Game.Core
if (-not (Test-Path "Game.Core/Game.Core.csproj")) {
    dotnet new classlib -n Game.Core -o Game.Core -f net8.0
    Write-Host "创建 Game.Core 项目" -ForegroundColor Gray
}

# Game.Core.Tests
if (-not (Test-Path "Game.Core.Tests/Game.Core.Tests.csproj")) {
    dotnet new xunit -n Game.Core.Tests -o Game.Core.Tests -f net8.0
    dotnet add Game.Core.Tests reference Game.Core
    dotnet add Game.Core.Tests package FluentAssertions
    dotnet add Game.Core.Tests package NSubstitute
    dotnet add Game.Core.Tests package coverlet.collector
    Write-Host "创建 Game.Core.Tests 项目" -ForegroundColor Gray
}

# 创建解决方案
if (-not (Test-Path "Game.sln")) {
    dotnet new sln -n Game
    dotnet sln add Game.Core/Game.Core.csproj
    dotnet sln add Game.Core.Tests/Game.Core.Tests.csproj
    Write-Host "创建 Visual Studio 解决方案" -ForegroundColor Gray
}

Pop-Location

Write-Host "`nGodot 项目初始化完成" -ForegroundColor Green
Write-Host "`n下一步：" -ForegroundColor Yellow
Write-Host "1. 使用 Godot Editor 打开 $ProjectRoot" -ForegroundColor White
Write-Host "2. 在 Godot 中创建 C# 项目（会生成 Game.Godot.csproj）" -ForegroundColor White
Write-Host "3. 将 Game.Godot.csproj 添加到 Game.sln" -ForegroundColor White
```

**执行初始化**:

```powershell
pwsh scripts/init-godot-project.ps1 -ProjectRoot "C:\buildgame\sanguo"
```

---

## 完成标准

- [ ] 目录结构已创建
- [ ] Game.Core 项目已初始化
- [ ] Game.Core.Tests 项目已初始化
- [ ] Game.sln 解决方案已创建
- [ ] .gitignore 和 .gitattributes 已配置
- [ ] Godot Editor 可打开项目
- [ ] Game.Godot.csproj 已生成（Godot 自动创建）
- [ ] `dotnet build` 编译通过
- [ ] `dotnet test` 运行通过（初始测试为空）

---

## 下一步

完成本阶段后，继续：

➡️ [Phase-4-Domain-Layer.md](Phase-4-Domain-Layer.md) — 纯 C# 领域层迁移
