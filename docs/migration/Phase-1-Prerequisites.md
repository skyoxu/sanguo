# Phase 1: 环境准备与工具安装

> 状态: 准备阶段
> 预估工时: 1-2 天
> 风险等级: 低
> 前置条件: Windows 11 + 管理员权限

---

## 目标

搭建 Godot 4.5 + C# 开发环境，安装必要的工具链和验证环境可用性。

---

## 工具清单

### 核心开发工具

#### 1. Godot Engine 4.5 (.NET版本)

**下载地址**: https://godotengine.org/download/windows/

**版本要求**: Godot 4.5.x (.NET 版本，而非 Standard 版本)

**安装步骤**:
```powershell
# 1. 下载 Godot_v4.5.x-stable_mono_win64.zip
# 2. 解压到 C:\Tools\Godot45\
# 3. 添加到系统 PATH
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Tools\Godot45",
    [EnvironmentVariableTarget]::User
)

# 4. 验证安装
godot --version
# 预期输出: 4.5.x.stable.mono.official
```

**验证清单**:
- [ ] `godot --version` 显示正确版本
- [ ] `godot --headless --version` headless 模式可用
- [ ] Godot Editor 可正常启动
- [ ] C# 项目模板可创建（Editor → New Project → C#）

#### 2. .NET 8 SDK

**下载地址**: https://dotnet.microsoft.com/download/dotnet/8.0

**版本要求**: .NET 8.0.x SDK (LTS)

**安装步骤**:
```powershell
# 1. 使用 winget 安装（推荐）
winget install Microsoft.DotNet.SDK.8

# 2. 或下载安装包手动安装
# https://dotnet.microsoft.com/download/dotnet/8.0

# 3. 验证安装
dotnet --version
# 预期输出: 8.0.x

dotnet --list-sdks
# 应包含 8.0.x 版本
```

**验证清单**:
- [ ] `dotnet --version` 显示 8.0.x
- [ ] `dotnet new list` 显示 C# 项目模板
- [ ] `dotnet build` 可编译示例项目
- [ ] `dotnet test` 可运行测试

#### 3. Python 3.11+

**用途**: CI 脚本、质量门禁工具

**安装步骤**:
```powershell
# 使用 winget 安装
winget install Python.Python.3.11

# 验证安装
py -3 --version
python --version

# 安装必要的包
py -3 -m pip install --upgrade pip
py -3 -m pip install pyyaml requests jsonschema
```

**验证清单**:
- [ ] `py -3 --version` 显示 3.11.x
- [ ] `pip list` 显示已安装 pyyaml, requests, jsonschema

### 开发辅助工具

#### 4. Visual Studio 2022 或 Rider

**推荐**: JetBrains Rider (Godot 集成更好) 或 Visual Studio 2022 Community

**VS 2022 安装**:
```powershell
# 必需工作负载
- .NET 桌面开发
- .NET Core 跨平台开发
- C# 开发工具

# 推荐组件
- ReSharper (代码质量分析)
- Visual Studio Tools for Godot (扩展)
```

**Rider 安装**:
```powershell
winget install JetBrains.Rider

# 安装 Godot 插件
# Rider → Settings → Plugins → Marketplace → 搜索 "Godot"
```

**验证清单**:
- [ ] IDE 可打开 .csproj 项目
- [ ] C# 智能提示正常工作
- [ ] 可调试 Godot C# 脚本

#### 5. Git + Git LFS

**安装步骤**:
```powershell
# 安装 Git
winget install Git.Git

# 安装 Git LFS (大文件支持)
git lfs install

# 配置 Git
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global core.autocrlf input
git config --global core.quotepath false
```

**验证清单**:
- [ ] `git --version` 显示 2.40+
- [ ] `git lfs --version` 正常输出
- [ ] Git 配置正确（`git config --list`）

### 质量工具

#### 6. SonarQube Scanner

**下载地址**: https://docs.sonarqube.org/latest/analyzing-source-code/scanners/sonarscanner-for-dotnet/

**安装步骤**:
```powershell
# 方法1: 使用 .NET Tool 安装（推荐）
dotnet tool install --global dotnet-sonarscanner

# 验证
dotnet sonarscanner --version

# 方法2: 下载独立版
# 解压到 C:\Tools\sonar-scanner\
# 添加到 PATH
```

**验证清单**:
- [ ] `dotnet sonarscanner --version` 正常输出
- [ ] 可连接到 SonarQube 服务器（如已有）

#### 7. 测试与覆盖率工具

**安装步骤**:
```powershell
# xUnit 测试框架（项目级安装，此处仅验证）
dotnet new xunit -n TestProject
cd TestProject
dotnet add package FluentAssertions
dotnet add package NSubstitute
dotnet add package coverlet.collector

# 清理测试项目
cd ..
Remove-Item -Recurse TestProject

# 安装全局报告工具
dotnet tool install --global dotnet-reportgenerator-globaltool
```

**验证清单**:
- [ ] `dotnet test` 可运行 xUnit 测试
- [ ] `reportgenerator --version` 正常输出
- [ ] coverlet 可生成覆盖率报告

#### 8. jscpd (代码重复检测)

**安装步骤**:
```powershell
# 安装 Node.js (如未安装)
winget install OpenJS.NodeJS.LTS

# 安装 jscpd
npm install -g jscpd

# 验证
jscpd --version
```

**验证清单**:
- [ ] `jscpd --version` 正常输出
- [ ] 可扫描 .cs 文件

### 观测性工具

#### 9. Sentry CLI

**安装步骤**:
```powershell
# 安装 Sentry CLI
npm install -g @sentry/cli

# 配置（需要 Sentry 账号和 Auth Token）
sentry-cli --version

# 登录（可选，后续配置）
sentry-cli login
```

**验证清单**:
- [ ] `sentry-cli --version` 正常输出
- [ ] 可连接到 Sentry 服务器（如已有）

---

## Godot Export Templates 安装

**用途**: 用于构建 Windows .exe 发布包

**安装步骤**:

1. **自动安装（推荐）**:
```powershell
# 在 Godot Editor 中
# Editor → Manage Export Templates → Download and Install
```

2. **手动安装**:
```powershell
# 1. 下载 Godot_v4.5.x-stable_mono_export_templates.tpz
# 2. 解压到 %APPDATA%\Godot\export_templates\4.5.x.stable.mono\
# 3. 验证目录结构
dir $env:APPDATA\Godot\export_templates\4.5.x.stable.mono\
```

**验证清单**:
- [ ] Godot Editor → Export → 显示 Windows Desktop 可用
- [ ] 可成功导出一个空项目为 .exe

---

## 项目仓库准备

### 创建新分支

```powershell
# 切换到 vitegame 仓库
cd C:\buildgame\vitegame

# 创建迁移分支（基于当前 main）
git checkout -b migration/godot-csharp
git push -u origin migration/godot-csharp

# 创建 migration 文档目录
mkdir -p docs/migration

# 创建 ADR 预留编号
# ADR-0018 到 ADR-0022 预留给 Godot 迁移
```

### 目录结构规划

```
vitegame/                      # 保持现有结构不变
├── docs/
│   ├── migration/             # 新增：迁移文档
│   │   ├── MIGRATION_INDEX.md
│   │   ├── Phase-1-Prerequisites.md
│   │   └── ...
│   └── adr/                   # 将新增 ADR-0018~0022
│
godotgame/                     # 新建：Godot 项目根目录
├── project.godot              # Godot 项目配置
├── Game.Core/                 # C# 纯逻辑库
│   ├── Game.Core.csproj
│   └── ...
├── Game.Core.Tests/           # xUnit 单元测试
│   ├── Game.Core.Tests.csproj
│   └── ...
├── Game.Godot/                # Godot 场景与脚本
│   ├── Scenes/
│   ├── Scripts/
│   ├── Autoloads/
│   └── ...
├── Game.Godot.Tests/          # GdUnit4 场景测试
│   └── ...
└── export_presets.cfg         # 导出配置
```

**执行步骤**:
```powershell
# 在 vitegame 同级创建 godotgame
cd C:\buildgame
mkdir godotgame
cd godotgame

# 初始化 Git（暂不关联远程仓库）
git init

# 创建 .gitignore
@"
# Godot
.godot/
.mono/
data_*/

# .NET
bin/
obj/
*.csproj.user

# Coverage
coverage/
TestResults/

# Logs
logs/
"@ | Out-File -Encoding utf8 .gitignore

# 创建 .gitattributes
@"
*.cs text eol=lf
*.gd text eol=lf
*.tscn text eol=lf
*.tres text eol=lf
*.cfg text eol=lf
"@ | Out-File -Encoding utf8 .gitattributes
```

---

## 环境验证脚本

创建一键验证脚本：

```powershell
# scripts/verify-environment.ps1

$errors = @()

# 检查 Godot
try {
    $godotVersion = godot --version 2>&1
    if ($godotVersion -notmatch "4\.5") {
        $errors += "Godot 版本不正确: $godotVersion"
    }
} catch {
    $errors += "Godot 未安装或不在 PATH 中"
}

# 检查 .NET
try {
    $dotnetVersion = dotnet --version
    if ($dotnetVersion -notmatch "^8\.") {
        $errors += ".NET 版本不正确: $dotnetVersion"
    }
} catch {
    $errors += ".NET SDK 未安装"
}

# 检查 Python
try {
    $pythonVersion = py -3 --version 2>&1
    if ($pythonVersion -notmatch "3\.(11|12)") {
        $errors += "Python 版本不正确: $pythonVersion"
    }
} catch {
    $errors += "Python 3.11+ 未安装"
}

# 检查 Git
try {
    $gitVersion = git --version
} catch {
    $errors += "Git 未安装"
}

# 检查 jscpd
try {
    $jscpdVersion = jscpd --version 2>&1
} catch {
    $errors += "jscpd 未安装"
}

# 检查 dotnet-sonarscanner
try {
    $sonarVersion = dotnet sonarscanner --version 2>&1
} catch {
    $errors += "dotnet-sonarscanner 未安装"
}

# 输出结果
if ($errors.Count -eq 0) {
    Write-Host "所有环境检查通过" -ForegroundColor Green
    exit 0
} else {
    Write-Host "环境检查失败：" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    exit 1
}
```

**运行验证**:
```powershell
pwsh scripts/verify-environment.ps1

# Python 等效（推荐）：scripts/verify_environment.py
py -3 scripts/verify_environment.py
```

---

## 常见问题

### Q1: Godot 启动报错 "Mono/.NET is not available"

**解决方案**:
- 确认下载的是 `.NET` 版本（文件名含 `mono`）
- 安装 .NET 8 SDK
- 重启 Godot Editor

### Q2: dotnet test 找不到测试

**解决方案**:
```powershell
# 清理并重新构建
dotnet clean
dotnet restore
dotnet build
dotnet test --no-build
```

### Q3: Git 提交中文乱码

**解决方案**:
```powershell
git config --global core.quotepath false
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
```

### Q4: Godot Export Templates 下载失败

**解决方案**:
- 手动下载 .tpz 文件
- 使用代理或镜像站点
- 解压到正确的目录（见上文）

---

## 完成标准

- [ ] 所有工具安装完成并通过验证
- [ ] `verify-environment.ps1` 脚本执行成功（或 `verify_environment.py`）
- [ ] Godot Editor 可正常创建 C# 项目
- [ ] dotnet test 可运行 xUnit 测试
- [ ] Godot Export Templates 可导出 Windows .exe
- [ ] Git 分支 `migration/godot-csharp` 已创建
- [ ] 目录结构 `godotgame/` 已初始化

---

## 下一步

完成本阶段后，继续：

➡️ [Phase-2-ADR-Updates.md](Phase-2-ADR-Updates.md) — ADR 更新与新增
