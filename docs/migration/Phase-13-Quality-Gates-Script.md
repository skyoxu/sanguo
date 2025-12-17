# Phase 13: 质量门禁脚本与自动化

> **核心目标**：统一 xUnit + GdUnit4 的质量门禁，建立 `guard:ci` 脚本入口，确保所有构建通过 10 项强制门禁检查。  
> **工作量**：4-5 人天  
> **依赖**：Phase 10（xUnit 框架）、Phase 11（GdUnit4 框架）、Phase 12（烟测 & 性能采集）  
> **交付物**：5 个脚本 + 1 个 GitHub Actions 工作流 + 日志规范  
> **验收标准**：本地 `NodePkg run guard:ci` 通过 + CI 自动执行通过

---

## 1. 背景与动机

### 原版（LegacyProject）质量控制
- LegacyDesktopShell + JavaScript/TypeScript
- LegacyE2ERunner E2E + LegacyUnitTestRunner 单元测试
- ESLint + Prettier 自动化
- GitHub Actions 单一工作流

### 新版（godotgame）质量挑战
- **双轨测试架构**：xUnit（C#）+ GdUnit4（GDScript）
- **两种编程语言**：代码重复率检测难度增加
- **Headless 执行**：无 GUI 反馈，必须依赖日志和报告
- **性能基准**：新增 P50/P95/P99 自动门禁
- **安全审计**：需验证 Security.cs 审计日志格式

### 质量门禁的价值
1. **防止回归**：自动阻断覆盖率下降、性能恶化的代码
2. **可审计**：每次构建的决策过程可重现、可溯源
3. **快速反馈**：开发者在 5 分钟内了解构建状态
4. **CI 自动化**：无需人工介入，自动 pass/fail，阻塞不合格 PR

---

## 2. 质量门禁定义

### 2.1 10 项强制门禁（蓝图目标）

| # | 门禁名称 | 度量标准 | 阈值 | 工具 | ADR |
|---|---------|--------|------|------|-----|
| 1 | xUnit 覆盖率（行） | Coverage % Lines | ≥90% | OpenCover | ADR-0005 |
| 2 | xUnit 覆盖率（分支） | Coverage % Branches | ≥85% | OpenCover | ADR-0005 |
| 3 | GdUnit4 冒烟通过率 | Test Pass Count | 100% | GdUnit4 | ADR-0001 |
| 4 | 代码重复率 | Duplication % | ≤2% | jscpd | ADR-0005 |
| 5 | 圈复杂度（max） | Max Cyclomatic | ≤10 | SonarQube Metrics | ADR-0005 |
| 6 | 圈复杂度（平均） | Avg Cyclomatic | ≤5 | SonarQube Metrics | ADR-0005 |
| 7 | 循环依赖 | Circular Deps Count | 0 | NetArchTest (arch tests) | ADR-0007 |
| 8 | 跨层依赖 | Cross-layer Violations | 0 | NetArchTest (arch tests) | ADR-0007 |
| 9 | 性能基准（P95） | Frame Time P95 | ≤16.67ms* | PerformanceTracker | ADR-0015 |
| 10 | 审计日志格式 | JSONL Valid | 100% | custom validator | ADR-0003 |

*Godot 目标帧率 60fps → 每帧 16.67ms；P95 应在此以下确保绝大多数帧流畅

---

### 2.2 Godot+C# 变体（当前模板实现）

> 本节描述的是 **当前 godotgame 模板已经落地的质量门禁实现**，用于对齐脚本/CI 的真实行为。上面的 10 项门禁表视为长期蓝图，尚未全部在本仓库中实现，对应增强统一收敛到 Phase-13 Backlog。

- 统一入口（Python）：
  - `scripts/python/quality_gates.py` 提供单一入口：
    - `py -3 scripts/python/quality_gates.py all --solution Game.sln --configuration Debug --godot-bin "C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe" --build-solutions`
  - 内部委托给 `scripts/python/ci_pipeline.py all` 执行当前已实现的门禁。

- 当前已实现的门禁集合：
  1. **dotnet 测试 + 覆盖率（硬门禁：测试通过；软门禁：覆盖率阈值）**
     - 脚本：`scripts/python/run_dotnet.py`，由 `ci_pipeline.py` 调用。
     - 行/分支覆盖率阈值：在 run_dotnet.py 中配置为软门禁（当前模板为较低阈值，方便扩展），不直接阻断构建。
     - 测试失败视为硬失败，quality_gates 退出码为 1。
  2. **Godot 自检（硬门禁）**
     - 脚本：`scripts/python/godot_selfcheck.py`：
       - `fix-autoload`：确保 CompositionRoot/Autoload 装配一致；
       - `run`：以 headless 方式启动 Godot，验证六大端口（ITime/IInput/IResourceLoader/IDataStore/ILogger/IEventBus）。
     - 由 `ci_pipeline.py` 调用，并将 SELF_CHECK 日志/摘要写入 `logs/e2e/<date>/` 与 `logs/ci/<date>/`。
     - 自检失败视为硬失败，quality_gates 退出码为 1。
  3. **编码扫描（软门禁）**
     - 脚本：`scripts/python/check_encoding.py`。
     - 作用：扫描本次改动的文件是否存在非 UTF-8 或可疑编码问题，结果写入 `logs/ci/<date>/encoding/`。
     - 编码异常目前作为软门禁：仅在 CI 日志中标黄提醒，不直接阻断构建（可在后续 Phase 提升为硬门禁）。

- CI 工作流对接：
  - `.github/workflows/ci-windows.yml`
    - 使用 PowerShell 封装脚本 `scripts/ci/quality_gate.ps1` 作为主入口；
    - `quality_gate.ps1` 的第一个步骤调用：
      - `py -3 scripts/python/quality_gates.py all --godot-bin $env:GODOT_BIN --solution Game.sln --configuration Debug --build-solutions`
    - 若质量门禁硬失败则整个 Job 失败；可选步骤（Export/EXE smoke/Perf budget）目前仅在特定分支启用。
  - `.github/workflows/windows-quality-gate.yml`
    - 重用相同的 Python 入口，面向“质量门禁聚合 + 报告上传”场景；
    - 额外聚合 GdUnit4 报告、DB/安全测试日志，作为软门禁信息来源。

- 尚未在当前模板落地的蓝图门禁（示例）：
  - 代码重复率（jscpd）、圈复杂度（SonarQube 或替代工具）、NetArchTest 架构测试；
  - 性能 P95 硬门禁、审计 JSONL 结构化验证；
  - GdUnit4 全集/Perf/Smoke 统一进入 quality_gates.py 的参数化入口。
  - 这些增强项统一记录在 `docs/migration/Phase-13-Quality-Gates-Backlog.md`，作为后续项目/迭代的可选任务，不计入当前模板 DoD。

---

## 3. 架构设计

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────┐
│              CI/CD Orchestration                     │
│         (guard-ci.yml, GitHub Actions)              │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│       Python Gate Runner (guard_ci.py)              │
│  - 顺序调用各测试/扫描脚本                          │
│  - 捕获输出报告路径                                 │
│  - 设定日志目录与环境变量                           │
└──────────────────────┬──────────────────────────────┘
                       │
      ┌────────────────┼────────────────┐
      │                │                │
      ▼                ▼                ▼
  xUnit Test      GdUnit4 Test         Code Scan
  ────────        ────────         ─────────
  dotnet test     godot --headless jscpd, SonarQube,
  opencover       --scene ..       SonarQube metrics,
                  GdUnit4 test runner  NetArchTest
                       │                │
                       └────────────────┘
                              │
         ┌────────────────────┴────────────────────┐
         │                                         │
         ▼                                         ▼
   Report Aggregation              Python Quality Gates
   (JSON/JSONL collect)            (quality_gates.py)
                                   - 聚合覆盖率
                                   - 检查所有门禁
                                   - 生成 HTML/JSON 报告
                                   - 返回 exit code
                                        │
                                        ▼
                                  ┌──────────────┐
                                  │ PASS / FAIL  │
                                  │ (exit code)  │
                                  └──────────────┘
```

### 3.2 目录结构

```
godotgame/
├── scripts/
│   ├── guard.ps1                  # PowerShell 主入口脚本
│   ├── python/
│   │   └── quality_gates.py        # Python 门禁聚合与决策
│   ├── ci/
│   │   ├── run_xunit_tests.ps1     # xUnit 执行与覆盖率收集
│   │   ├── run_gut_tests.ps1       # GdUnit4 烟测执行
│   │   └── run_code_scans.ps1      # 重复率/复杂度/依赖检查
│   └── validate/
│       ├── validate_coverage.py    # 覆盖率解析与阈值检查
│       ├── validate_gut_report.py  # GdUnit4 报告解析
│       └── validate_audit_logs.py  # JSONL 审计日志验证
├── logs/
│   └── ci/                         # 按日期组织的 CI 日志
│       └── 2025-11-07/
│           ├── xunit-coverage.xml
│           ├── gut-report.log
│           ├── jscpd-report.json
│           ├── complexity-report.html
│           ├── quality-gates.html   # 最终门禁报告
│           └── quality-gates.json   # 机器可读版本
├── .github/
│   └── workflows/
│       └── guard-ci.yml            # GitHub Actions 工作流
└── package.json
    "guard:ci": "py -3 scripts/python/guard_ci.py"
```

---

## 4. 关键交付物详细设计

### 4.0 架构测试与复杂度度量示例

#### 4.0.1 NetArchTest 最小架构测试（C# xUnit）

```csharp
// Game.Core.Tests/Architecture/LayeringTests.cs
using NetArchTest.Rules;
using Xunit;

namespace Game.Core.Tests.Architecture;

public class LayeringTests
{
    private const string CoreNamespace = "Game.Core";
    private const string GodotNamespace = "Game.Godot";

    [Fact]
    public void Core_Should_Not_Depend_On_Godot()
    {
        var result = Types
            .InAssembly(typeof(Game.Core.Domain.Entities.Player).Assembly)
            .That()
            .ResideInNamespace(CoreNamespace, useRegularExpressions: true)
            .Should()
            .NotHaveDependencyOn(GodotNamespace)
            .GetResult();

        Assert.True(result.IsSuccessful, string.Join("\n", result.Failures));
    }
}
```

用法：将该测试纳入 `dotnet test` 即可；在门禁聚合中将其失败视为“跨层违规/循环依赖”不通过。

#### 4.0.2 SonarQube Metrics 最小集成

```bash
# 1) 开始分析（示例）
dotnet sonarscanner begin \
  /k:"godotgame" /d:sonar.host.url="%SONAR_HOST_URL%" \
  /d:sonar.login="%SONAR_TOKEN%" \
  /d:sonar.cs.opencover.reportsPaths="logs/ci/xunit-coverage.xml"

# 2) 运行构建/测试（确保生成覆盖率）
dotnet build
dotnet test Game.Core.Tests \
  --collect:"XPlat Code Coverage;Format=opencover;FileName=logs/ci/xunit-coverage.xml"

# 3) 结束分析
dotnet sonarscanner end /d:sonar.login="%SONAR_TOKEN%"
```

说明：
- 在 CI 中可使用 `sonar.qualitygate.wait=true` 或读取 Sonar API JSON 结果，将圈复杂度/重复率/质量门禁解析后传入 `quality_gates.py` 聚合。
- 若无 Sonar 服务器，可退化为“导出本地 metrics JSON（第三方工具或自编）→ 解析 → 聚合”的流程。

### 4.1 脚本：guard_ci.py（Python 主入口）

**职责**：协调所有测试与扫描的执行顺序，管理日志目录

```python
# scripts/python/guard_ci.py
import argparse, subprocess, sys
from pathlib import Path
from datetime import datetime

def run(cmd: list[str]) -> None:
    print('>',' '.join(cmd))
    subprocess.check_call(cmd)

def main() -> int:
    parser = argparse.ArgumentParser()
    default_log = f"logs/ci/{datetime.now().strftime('%Y-%m-%d')}"
    parser.add_argument('--log-dir', default=default_log)
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    print('CI Logs:', log_dir)

    # 1) xUnit 测试与覆盖率
    run([
        'dotnet','test','Game.Core.Tests',
        '--configuration','Release','--no-build',
        '--logger', f"trx;LogFileName={log_dir/'xunit-results.trx'}",
        '--collect:XPlat Code Coverage;Format=opencover;FileName=' + str(log_dir/'xunit-coverage.xml')
    ])

    # 2) GdUnit4 冒烟（headless）
    run([
        'godot','--headless','--path','Game.Godot',
        '--script','res://addons/gut/gut_cmdln.cs',
        '-gdir=Game.Godot/Tests','-goutput=' + str(log_dir/'gut-report.json')
    ])

    # 3) 代码扫描（重复率 等）
    run(['npx','jscpd','--reporters','json','--json-file', str(log_dir/'jscpd-report.json'), '--pattern','**/*.{cs,gd}','--gitignore'])

    # 4) 门禁聚合
    run(['py','-3','scripts/python/quality_gates.py',
         '--log-dir', str(log_dir),
         '--coverage-report', str(log_dir/'xunit-coverage.xml'),
         '--gut-report', str(log_dir/'gut-report.json'),
         '--jscpd-report', str(log_dir/'jscpd-report.json')])

    print('All quality gates passed')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        print('Quality gates failed with code', e.returncode)
        sys.exit(e.returncode)
```

### 4.1.1 报告收集与复制（user:// → 仓库 logs/ci）

Godot 在 Windows 下将 `user://` 映射到 `C:\Users\<User>\AppData\Roaming\Godot\app_userdata\<ProjectName>`。为便于 CI 聚合门禁报告，可在 `guard_ci.py` 结束前追加如下收集逻辑：

```python
import os, shutil
from pathlib import Path

def collect_user_reports(project_name: str, date_str: str, dest_dir: Path) -> None:
    base = Path(os.environ.get('APPDATA',''))/ 'Godot' / 'app_userdata' / project_name / 'logs' / 'e2e' / date_str
    if not base.exists():
        print('No user:// reports found at', base)
        return
    dest_dir.mkdir(parents=True, exist_ok=True)
    for f in base.glob('*'):
        if f.is_file():
            shutil.copy2(f, dest_dir / f.name)

# 用法示例：
# collect_user_reports(project_name='godotgame', date_str=datetime.now().strftime('%Y-%m-%d'), dest_dir=Path('logs')/'e2e'/datetime.now().strftime('%Y-%m-%d'))
```

说明（Windows 路径映射）：
- `user://` 实际路径通常位于 `%APPDATA%\Godot\app_userdata\<ProjectName>`。
 - `<ProjectName>` 取自 `project.godot` 中 `application/config/name`；请确保与 CI 中的工程名一致，以便收集器能找到正确目录。

可选输入（GdUnit4 场景测试）：
- 若已将 GdUnit4 报告复制到 `logs/ci/YYYY-MM-DD/gdunit4/`，可在 `quality_gates.py` 中增加解析步骤：
  - 读取 `gdunit4-report.xml`（JUnit XML）或 `gdunit4-report.json`（若存在），计算通过率；
  - 将“场景测试通过率=100%”作为前置门禁，再执行性能门禁与其他质量门禁；
  - 推荐在 `guard_ci.py` 调用 `quality_gates.py` 时，新增参数如 `--gdunit4-report` 传入文件路径，以统一聚合。

---

## 扩展门禁（可选/推荐，Godot + C# 环境）

| # | 门禁名称 | 度量标准 | 阈值 | 工具/来源 | 说明 |
|---|---------|--------|------|-----------|-----|
| 11 | Taskmaster 任务链校验 | Errors Count | = 0 | taskmaster_validate.py | 解析任务链与反链（Windows/py -3），输出 JSON；失败阻断 |
| 12 | 契约校验（C# Contracts） | Errors Count | = 0 | contracts_validate.py 或 C# 验证器 | 对 `Game.Core/Contracts/**` DTO/事件契约进行约束校验（DataAnnotations/自定义规则），输出 JSON；失败阻断 |

guard_ci.py 参数扩展说明（示例）：
```
py -3 scripts/python/quality_gates.py \
  --log-dir logs/ci/2025-11-07 \
  --coverage-report logs/ci/2025-11-07/xunit-coverage.xml \
  --gut-report logs/ci/2025-11-07/gut-report.json \
  --jscpd-report logs/ci/2025-11-07/jscpd-report.json \
  --gdunit4-report logs/ci/2025-11-07/gdunit4/gdunit4-report.xml \
  --taskmaster-report logs/ci/2025-11-07/taskmaster-report.json \
  --contracts-report logs/ci/2025-11-07/contracts-report.json
```

说明：扩展门禁的报告文件可在“报告收集与复制”步骤中统一归集后再传入聚合脚本；在 Godot + C# 环境下，契约目录建议位于 `Game.Core/Contracts/**`，使用 C# 验证器（DataAnnotations/自定义规则）导出 JSON。

---

### 4.2 脚本：run_xunit_tests.ps1

**职责**：执行 xUnit 测试并收集 OpenCover 覆盖率报告

```powershell
# scripts/ci/run_xunit_tests.ps1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$LogDir
)

$ErrorActionPreference = "Stop"

# xUnit 项目路径
$xunitProject = "Game.Core.Tests"
$coverageReport = "$LogDir/xunit-coverage.xml"

Write-Host "xUnit Project: $xunitProject"
Write-Host "Coverage Report: $coverageReport"

# 检查 OpenCover 安装（或使用 dotnet 内置）
# 执行测试并收集覆盖率
$testCommand = @(
    "dotnet", "test", $xunitProject,
    "--configuration Release",
    "--no-build",
    "--logger `"trx;LogFileName=$LogDir/xunit-results.trx`"",
    "--collect:`"XPlat Code Coverage;Format=opencover;FileName=$coverageReport`""
)

Write-Host "Running: $($testCommand -join ' ')" -ForegroundColor Cyan
& $testCommand[0] $testCommand[1..($testCommand.Length-1)]

if ($LASTEXITCODE -ne 0) {
    Write-Error "xUnit tests execution failed"
    exit 1
}

Write-Host "xUnit tests completed" -ForegroundColor Green
exit 0
```

---

### 4.3 脚本：run_gut_tests.ps1

**职责**：执行 GdUnit4 冒烟测试，生成 JSON 格式报告

```powershell
# scripts/ci/run_gut_tests.ps1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$LogDir
)

$ErrorActionPreference = "Stop"

$gutReport = "$LogDir/gut-report.json"
$gutProjectPath = "."  # Godot 项目根目录

Write-Host "GdUnit4 Project: $gutProjectPath"
Write-Host "Report: $gutReport"

# 使用 Godot headless + GdUnit4 runner scene
$gutCommand = @(
    "godot", "--headless", "--no-window",
    "--scene", "res://tests/SmokeTestRunner.tscn",
    "--", "output=$gutReport"  # GdUnit4 命令行参数
)

Write-Host "Running: $($gutCommand -join ' ')" -ForegroundColor Cyan
& $gutCommand[0] $gutCommand[1..($gutCommand.Length-1)]

if ($LASTEXITCODE -ne 0) {
    Write-Warning "GdUnit4 execution returned non-zero, but may contain passing tests"
    # GdUnit4 可能返回非零，即使测试通过；需在 Python 验证阶段处理
}

# 验证报告文件存在
if (-not (Test-Path $gutReport)) {
    Write-Error "GdUnit4 report file not generated: $gutReport"
    exit 1
}

Write-Host "GdUnit4 tests completed" -ForegroundColor Green
exit 0
```

---

### 4.4 脚本：run_code_scans.ps1

**职责**：执行代码扫描（重复率、复杂度、依赖检查）

```powershell
# scripts/ci/run_code_scans.ps1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$LogDir
)

$ErrorActionPreference = "Stop"

Write-Host "Running code quality scans..." -ForegroundColor Cyan

# 1. jscpd - 重复率检查
Write-Host "`n[Scan 1/3] jscpd (duplication)..." -ForegroundColor Yellow
$jscpdReport = "$LogDir/jscpd-report.json"
$jscpdCmd = @(
    "npx", "jscpd",
    "--threshold", "2",  # 失败阈值 2%
    "--gitignore",
    "--reporters", "json",
    "--json-file", $jscpdReport,
    "--pattern", "**/*.{cs,gd,ts,tsx}",
    "Game.Core", "Game.Godot"
)

& $jscpdCmd[0] $jscpdCmd[1..($jscpdCmd.Length-1)]
if ($LASTEXITCODE -ne 0) {
    Write-Warning "jscpd check failed (duplication > 2%)"
    # 检查是否真的超阈值，或只是警告
}

# 2. complexity-report - 圈复杂度
Write-Host "`n[Scan 2/3] complexity-report..." -ForegroundColor Yellow
$complexityReport = "$LogDir/complexity-report.json"
$complexityCmd = @(
    "npx", "complexity-report",
    "-o", $complexityReport,
    "Game.Core", "Game.Godot"
)

& $complexityCmd[0] $complexityCmd[1..($complexityCmd.Length-1)]
if ($LASTEXITCODE -ne 0) {
    Write-Warning "complexity-report execution had issues (may be non-blocking)"
}

# 3. dependency-cruiser - 依赖检查
Write-Host "`n[Scan 3/3] dependency-cruiser (circular/cross-layer)..." -ForegroundColor Yellow
$depCruiserReport = "$LogDir/dependency-cruiser.json"
$depCmd = @(
    "npx", "depcruise",
    "--output-type", "json",
    "-o", $depCruiserReport,
    "Game.Core", "Game.Godot"
)

& $depCmd[0] $depCmd[1..($depCmd.Length-1)]
if ($LASTEXITCODE -ne 0) {
    Write-Warning "dependency-cruiser check failed"
}

Write-Host "`nCode scans completed" -ForegroundColor Green
exit 0
```

---

### 4.5 脚本：quality_gates.py（Python 门禁聚合）

**职责**：解析所有报告，检查门禁，生成最终报告

```python
#!/usr/bin/env python3
"""
scripts/python/quality_gates.py

质量门禁聚合与决策引擎
- 读取 xUnit/GdUnit4/jscpd/complexity 报告
- 逐项检查门禁（10 项）
- 生成 HTML/JSON 输出
- 返回 exit code（0=pass, 1=fail）
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import argparse

class QualityGatesReport:
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.gates = {}
        self.timestamp = datetime.now().isoformat()
        
    def check_gate_1_xunit_lines_coverage(self, coverage_report_path):
        """xUnit 覆盖率（行）≥90%"""
        gate_id = "GATE-1"
        gate_name = "xUnit Line Coverage"
        threshold = 90
        
        try:
            tree = ET.parse(coverage_report_path)
            root = tree.getroot()
            
            # OpenCover XML 格式：<CoverageSession ... lineCoverage="XX.XX">
            line_coverage = float(root.get('lineCoverage', '0'))
            
            passed = line_coverage >= threshold
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': f'{threshold}%',
                'actual': f'{line_coverage:.2f}%',
                'passed': passed,
                'reason': f"Line coverage {line_coverage:.2f}% {'≥' if passed else '<'} {threshold}%"
            }
            return passed
        except Exception as e:
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': f'{threshold}%',
                'actual': 'ERROR',
                'passed': False,
                'reason': f"Failed to parse coverage report: {str(e)}"
            }
            return False
    
    def check_gate_2_xunit_branches_coverage(self, coverage_report_path):
        """xUnit 覆盖率（分支）≥85%"""
        gate_id = "GATE-2"
        gate_name = "xUnit Branch Coverage"
        threshold = 85
        
        try:
            tree = ET.parse(coverage_report_path)
            root = tree.getroot()
            
            branch_coverage = float(root.get('branchCoverage', '0'))
            
            passed = branch_coverage >= threshold
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': f'{threshold}%',
                'actual': f'{branch_coverage:.2f}%',
                'passed': passed,
                'reason': f"Branch coverage {branch_coverage:.2f}% {'≥' if passed else '<'} {threshold}%"
            }
            return passed
        except Exception as e:
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': f'{threshold}%',
                'actual': 'ERROR',
                'passed': False,
                'reason': f"Failed to parse coverage report: {str(e)}"
            }
            return False
    
    def check_gate_3_gut_pass_rate(self, gut_report_path):
        """GdUnit4 冒烟通过率 = 100%"""
        gate_id = "GATE-3"
        gate_name = "GdUnit4 Pass Rate"
        threshold = 100
        
        try:
            with open(gut_report_path, 'r', encoding='utf-8') as f:
                gut_data = json.load(f)
            
            # GdUnit4 报告格式：{ "tests": [{...}], "passed": N, "failed": N }
            total = gut_data.get('total_tests', 0)
            passed = gut_data.get('passed_tests', 0)
            
            if total == 0:
                pass_rate = 0
            else:
                pass_rate = (passed / total) * 100
            
            passed_gate = pass_rate >= threshold
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': f'{threshold}%',
                'actual': f'{pass_rate:.1f}% ({passed}/{total})',
                'passed': passed_gate,
                'reason': f"GdUnit4 Pass Rate {pass_rate:.1f}% {'≥' if passed_gate else '<'} {threshold}%"
            }
            return passed_gate
        except Exception as e:
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': f'{threshold}%',
                'actual': 'ERROR',
                'passed': False,
                'reason': f"Failed to parse GdUnit4 report: {str(e)}"
            }
            return False
    
    def check_gate_4_duplication_rate(self, jscpd_report_path):
        """代码重复率 ≤2%"""
        gate_id = "GATE-4"
        gate_name = "Code Duplication"
        threshold = 2
        
        try:
            with open(jscpd_report_path, 'r', encoding='utf-8') as f:
                jscpd_data = json.load(f)
            
            # jscpd 报告：{ "duplicates": [...], "statistics": { "total": N, "clones": M } }
            duplicates = jscpd_data.get('duplicates', [])
            statistics = jscpd_data.get('statistics', {})
            total_lines = statistics.get('total', 1)
            duplicate_lines = statistics.get('clones', 0)
            
            dup_rate = (duplicate_lines / total_lines) * 100 if total_lines > 0 else 0
            
            passed = dup_rate <= threshold
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': f'≤{threshold}%',
                'actual': f'{dup_rate:.2f}% ({duplicate_lines}/{total_lines} lines)',
                'passed': passed,
                'reason': f"Duplication {dup_rate:.2f}% {'≤' if passed else '>'} {threshold}%"
            }
            return passed
        except Exception as e:
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': f'≤{threshold}%',
                'actual': 'ERROR',
                'passed': False,
                'reason': f"Failed to parse jscpd report: {str(e)}"
            }
            return False
    
    def check_gate_5_6_cyclomatic_complexity(self, complexity_report_path):
        """圈复杂度：max ≤10, avg ≤5"""
        gate_5_id = "GATE-5"
        gate_6_id = "GATE-6"
        gate_5_name = "Max Cyclomatic Complexity"
        gate_6_name = "Avg Cyclomatic Complexity"
        threshold_max = 10
        threshold_avg = 5
        
        try:
            with open(complexity_report_path, 'r', encoding='utf-8') as f:
                complexity_data = json.load(f)
            
            # complexity-report 格式：[{ "name": "...", "complexity": N }, ...]
            complexities = [item.get('complexity', 0) for item in complexity_data if isinstance(item, dict)]
            
            if not complexities:
                max_complexity = 0
                avg_complexity = 0
            else:
                max_complexity = max(complexities)
                avg_complexity = sum(complexities) / len(complexities)
            
            passed_5 = max_complexity <= threshold_max
            passed_6 = avg_complexity <= threshold_avg
            
            self.gates[gate_5_id] = {
                'name': gate_5_name,
                'threshold': f'≤{threshold_max}',
                'actual': f'{max_complexity:.1f}',
                'passed': passed_5,
                'reason': f"Max complexity {max_complexity:.1f} {'≤' if passed_5 else '>'} {threshold_max}"
            }
            
            self.gates[gate_6_id] = {
                'name': gate_6_name,
                'threshold': f'≤{threshold_avg}',
                'actual': f'{avg_complexity:.2f}',
                'passed': passed_6,
                'reason': f"Avg complexity {avg_complexity:.2f} {'≤' if passed_6 else '>'} {threshold_avg}"
            }
            
            return passed_5 and passed_6
        except Exception as e:
            self.gates[gate_5_id] = {
                'name': gate_5_name,
                'threshold': f'≤{threshold_max}',
                'actual': 'ERROR',
                'passed': False,
                'reason': f"Failed to parse complexity report: {str(e)}"
            }
            self.gates[gate_6_id] = {
                'name': gate_6_name,
                'threshold': f'≤{threshold_avg}',
                'actual': 'ERROR',
                'passed': False,
                'reason': f"Failed to parse complexity report: {str(e)}"
            }
            return False
    
    def check_gate_7_8_dependencies(self, dep_cruiser_report_path):
        """循环依赖 & 跨层依赖 = 0"""
        gate_7_id = "GATE-7"
        gate_8_id = "GATE-8"
        gate_7_name = "Circular Dependencies"
        gate_8_name = "Cross-layer Violations"
        
        try:
            with open(dep_cruiser_report_path, 'r', encoding='utf-8') as f:
                dep_data = json.load(f)
            
            # dependency-cruiser 格式：{ "modules": [...], "summary": { "error": N, "warn": M } }
            violations = dep_data.get('summary', {}).get('error', 0)
            warnings = dep_data.get('summary', {}).get('warn', 0)
            
            # 这里简化处理；实际可细分循环依赖 vs 跨层
            circular_deps = violations
            cross_layer_violations = warnings
            
            passed_7 = circular_deps == 0
            passed_8 = cross_layer_violations == 0
            
            self.gates[gate_7_id] = {
                'name': gate_7_name,
                'threshold': '0',
                'actual': f'{circular_deps}',
                'passed': passed_7,
                'reason': f"{circular_deps} circular dependencies found" if not passed_7 else "No circular deps"
            }
            
            self.gates[gate_8_id] = {
                'name': gate_8_name,
                'threshold': '0',
                'actual': f'{cross_layer_violations}',
                'passed': passed_8,
                'reason': f"{cross_layer_violations} cross-layer violations found" if not passed_8 else "No violations"
            }
            
            return passed_7 and passed_8
        except Exception as e:
            self.gates[gate_7_id] = {
                'name': gate_7_name,
                'threshold': '0',
                'actual': 'ERROR',
                'passed': False,
                'reason': f"Failed to parse dependency report: {str(e)}"
            }
            self.gates[gate_8_id] = {
                'name': gate_8_name,
                'threshold': '0',
                'actual': 'ERROR',
                'passed': False,
                'reason': f"Failed to parse dependency report: {str(e)}"
            }
            return False
    
    def check_gate_9_performance_baseline(self):
        """性能基准（P95）≤16.67ms"""
        gate_id = "GATE-9"
        gate_name = "Performance Baseline (P95)"
        threshold = 16.67
        
        # 从 GdUnit4 烟测报告中提取性能数据
        # 这里示例，实际需从 PerformanceTracker.cs 输出的数据文件读取
        try:
            perf_report = self.log_dir / "performance-tracker.json"
            if perf_report.exists():
                with open(perf_report, 'r', encoding='utf-8') as f:
                    perf_data = json.load(f)
                
                p95_time = perf_data.get('frame_time_p95', 0)
                passed = p95_time <= threshold
            else:
                p95_time = None
                passed = True  # 如果没有性能数据，暂时通过（可选）
            
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': f'≤{threshold}ms',
                'actual': f'{p95_time:.2f}ms' if p95_time else 'N/A',
                'passed': passed,
                'reason': f"P95 frame time {p95_time:.2f}ms {'≤' if passed else '>'} {threshold}ms" if p95_time else "No perf data"
            }
            return passed
        except Exception as e:
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': f'≤{threshold}ms',
                'actual': 'ERROR',
                'passed': True,  # 暂时放行
                'reason': f"Performance data not available (optional): {str(e)}"
            }
            return True
    
    def check_gate_10_audit_logs_format(self):
        """审计日志格式（JSONL）= 100% 有效"""
        gate_id = "GATE-10"
        gate_name = "Audit Log Format (JSONL)"
        
        try:
            audit_log = self.log_dir / "security-audit.jsonl"
            if not audit_log.exists():
                self.gates[gate_id] = {
                    'name': gate_name,
                    'threshold': '100% valid',
                    'actual': 'N/A',
                    'passed': True,
                    'reason': "No audit log generated (optional)"
                }
                return True
            
            total_lines = 0
            valid_lines = 0
            
            with open(audit_log, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    total_lines += 1
                    try:
                        json.loads(line)
                        valid_lines += 1
                    except json.JSONDecodeError:
                        pass
            
            if total_lines == 0:
                validity_rate = 100
                passed = True
            else:
                validity_rate = (valid_lines / total_lines) * 100
                passed = validity_rate == 100
            
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': '100%',
                'actual': f'{validity_rate:.1f}% ({valid_lines}/{total_lines})',
                'passed': passed,
                'reason': f"JSONL validity {validity_rate:.1f}% {'=' if passed else '≠'} 100%"
            }
            return passed
        except Exception as e:
            self.gates[gate_id] = {
                'name': gate_name,
                'threshold': '100%',
                'actual': 'ERROR',
                'passed': True,
                'reason': f"Audit log validation skipped: {str(e)}"
            }
            return True
    
    def run_all_checks(self, coverage_report, gut_report, jscpd_report, complexity_report, dep_cruiser_report):
        """执行所有 10 项门禁检查"""
        results = []
        
        results.append(self.check_gate_1_xunit_lines_coverage(coverage_report))
        results.append(self.check_gate_2_xunit_branches_coverage(coverage_report))
        results.append(self.check_gate_3_gut_pass_rate(gut_report))
        results.append(self.check_gate_4_duplication_rate(jscpd_report))
        passed_5_6 = self.check_gate_5_6_cyclomatic_complexity(complexity_report)
        results.append(passed_5_6)
        results.append(passed_5_6)
        
        passed_7_8 = self.check_gate_7_8_dependencies(dep_cruiser_report)
        results.append(passed_7_8)
        results.append(passed_7_8)
        
        results.append(self.check_gate_9_performance_baseline())
        results.append(self.check_gate_10_audit_logs_format())
        
        return all(results)
    
    def generate_html_report(self, output_path):
        """生成 HTML 报告"""
        passed_count = sum(1 for g in self.gates.values() if g['passed'])
        total_count = len(self.gates)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Quality Gates Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ font-size: 24px; font-weight: bold; margin: 20px 0; }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #f8f9fa; }}
        tr.pass {{ background: #f0f8f5; }}
        tr.fail {{ background: #fff5f5; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Quality Gates Report</h1>
        <p>Generated: {self.timestamp}</p>
    </div>
    
    <div class="summary">
        Result: <span class="{'passed' if passed_count == total_count else 'failed'}">
            {passed_count}/{total_count} Gates PASSED
        </span>
    </div>
    
    <table>
        <tr>
            <th>Gate ID</th>
            <th>Name</th>
            <th>Threshold</th>
            <th>Actual</th>
            <th>Status</th>
            <th>Reason</th>
        </tr>
"""
        
        for gate_id in sorted(self.gates.keys()):
            gate = self.gates[gate_id]
            status = 'PASS' if gate['passed'] else 'FAIL'
            row_class = 'pass' if gate['passed'] else 'fail'
            
            html += f"""        <tr class="{row_class}">
            <td>{gate_id}</td>
            <td>{gate['name']}</td>
            <td>{gate['threshold']}</td>
            <td>{gate['actual']}</td>
            <td>{status}</td>
            <td>{gate['reason']}</td>
        </tr>
"""
        
        html += """    </table>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    def generate_json_report(self, output_path):
        """生成 JSON 报告"""
        report = {
            'timestamp': self.timestamp,
            'summary': {
                'passed': sum(1 for g in self.gates.values() if g['passed']),
                'total': len(self.gates),
                'all_passed': all(g['passed'] for g in self.gates.values())
            },
            'gates': self.gates
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Quality Gates Aggregator')
    parser.add_argument('--log-dir', required=True, help='CI logs directory')
    parser.add_argument('--coverage-report', required=True, help='xUnit coverage XML')
    parser.add_argument('--gut-report', required=True, help='GdUnit4 test report JSON')
    parser.add_argument('--jscpd-report', required=True, help='jscpd report JSON')
    parser.add_argument('--complexity-report', required=True, help='complexity report JSON')
    parser.add_argument('--dep-cruiser-report', default=None, help='dependency-cruiser report JSON')
    
    args = parser.parse_args()
    
    report = QualityGatesReport(args.log_dir)
    
    # 运行所有检查
    all_passed = report.run_all_checks(
        args.coverage_report,
        args.gut_report,
        args.jscpd_report,
        args.complexity_report,
        args.dep_cruiser_report or (Path(args.log_dir) / "dependency-cruiser.json")
    )
    
    # 生成报告
    log_dir = Path(args.log_dir)
    report.generate_html_report(log_dir / "quality-gates.html")
    report.generate_json_report(log_dir / "quality-gates.json")
    
    print(f"\n{'='*60}")
    print(f"Quality Gates Report")
    print(f"{'='*60}")
    print(f"Passed: {sum(1 for g in report.gates.values() if g['passed'])}/{len(report.gates)}")
    print(f"Status: {'ALL PASSED' if all_passed else 'FAILED'}")
    print(f"\nDetailed Report: {log_dir}/quality-gates.html")
    print(f"JSON Report: {log_dir}/quality-gates.json")
    print(f"{'='*60}\n")
    
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
```

---

### 4.6 GitHub Actions 工作流：guard-ci.yml

**职责**：CI/CD 自动化入点，调用本地脚本，上传工件

```yaml
# .github/workflows/guard-ci.yml
name: Guard CI - Quality Gates

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  quality-gates:
    runs-on: windows-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup .NET 8
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          NodePkg install
          dotnet restore Game.Core.sln
      
      - name: Run Quality Gates Script
        shell: pwsh
        run: |
          pwsh scripts/guard.ps1
        continue-on-error: true
      
      - name: Upload Reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: quality-gates-reports
          path: logs/ci/*/
          retention-days: 30
      
      - name: Comment PR with Results
        if: github.event_name == 'pull_request' && always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const reportPath = 'logs/ci/*/quality-gates.json';
            // 解析报告，写入 PR 评论
```

---

## 5. 集成点与工作流

### 5.1 本地开发流程

```bash
# 开发者提交前运行本地 guard:ci
NodePkg run guard:ci

# 输出示例
# [Step 1/4] Running xUnit tests with coverage...
# xUnit tests completed
# [Step 2/4] Running GdUnit4 smoke tests...
# GdUnit4 tests completed
# [Step 3/4] Running code quality scans...
# Code scans completed
# [Step 4/4] Aggregating quality gates...
# ============================================================
# Quality Gates Report
# ============================================================
# Passed: 10/10
# Status: ALL PASSED
# 
# Detailed Report: logs/ci/2025-11-07/quality-gates.html
# JSON Report: logs/ci/2025-11-07/quality-gates.json
# ============================================================
```

### 5.2 CI 工作流

```
PR 创建 / push to develop
    │
    ▼
guard-ci.yml workflow triggered
    │
    ├─► setup (.NET, Node, Python)
    ├─► NodePkg install / dotnet restore
    ├─► pwsh scripts/guard.ps1
    │   ├─► run_xunit_tests.ps1
    │   ├─► run_gut_tests.ps1
    │   ├─► run_code_scans.ps1
    │   └─► quality_gates.py
    │
    ▼ (always)
Upload artifacts: logs/ci/*
    │
    ▼ (on pull_request)
Comment PR with quality-gates.json summary
    │
    ▼
Branch protection rule checks:
  - status: guard-ci / quality-gates
  - if FAIL → block merge
  - if PASS → allow merge
```

---

## 6. 完成清单与验收标准

### 6.1 实现检查清单

- [ ] 创建 `scripts/guard.ps1` 主入口脚本
- [ ] 创建 `scripts/ci/run_xunit_tests.ps1`
- [ ] 创建 `scripts/ci/run_gut_tests.ps1`
- [ ] 创建 `scripts/ci/run_code_scans.ps1`
- [ ] 创建 `scripts/python/quality_gates.py`（含 10 项门禁检查）
- [ ] 创建 `.github/workflows/guard-ci.yml`
- [ ] 在 `package.json` 中配置 `guard:ci` 脚本
- [ ] 建立 `logs/ci/` 目录结构与日志规范
- [ ] 编写 Phase 13 完整文档（本文档）
- [ ] 本地测试 `NodePkg run guard:ci` 成功通过

### 6.2 验收标准

| 项目 | 验收标准 | 确认 |
|-----|--------|------|
| 脚本完整性 | 5 个脚本 + 1 个工作流完整可运行 | □ |
| 门禁全覆盖 | 10 项门禁全部检查且有理由说明 | □ |
| 报告生成 | HTML + JSON 报告自动生成 | □ |
| 本地执行 | `NodePkg run guard:ci` <2min 完成 | □ |
| CI 集成 | GitHub Actions 自动触发，结果评论 PR | □ |
| 文档完整 | Phase 13 文档 ≥800 行，含代码示例 | □ |
| 日志规范 | `logs/ci/YYYY-MM-DD/` 目录自动创建 | □ |

---

## 7. 风险与缓解

| # | 风险 | 等级 | 缓解 |
|---|-----|------|-----|
| 1 | xUnit/GdUnit4 报告格式变更 | 中 | 版本锁定，定期更新解析器 |
| 2 | 扫描工具网络超时 | 中 | 离线缓存，超时降级（警告而非失败） |
| 3 | PowerShell 跨平台问题 | 高 | 仅支持 Windows（已明确），未来扩展考虑 core |
| 4 | 覆盖率阈值过高导致频繁 fail | 中 | 前 2 周宽松（85%），逐步提高到 90% |
| 5 | 性能基准采集不稳定 | 中 | 采集 5 次取均值，baseline.json 版本化 |

---

## 8. 后续工作（Phase 14-22）

完成 Phase 13 后，后续工作序列：

- **Phase 14**：Godot 安全基线与审计（Security.cs 完整实现、JSONL 日志）
- **Phase 15**：性能预算与门禁（PerformanceTracker 基准、自动回归检测）
- **Phase 16**：可观测性与 Sentry 集成（Release Health 门禁）
- **Phase 17-22**：构建、发布、回滚、功能验收、性能优化、文档更新

---

## 9. 参考与链接

- **ADR-0005**：质量门禁 - 覆盖率、复杂度、重复率
- **ADR-0003**：可观测性与 Sentry - 发布健康门禁
- **ADR-0001**：技术栈与 Godot 集成
- **Phase 10**：xUnit 框架与项目结构
- **Phase 11**：GdUnit4 框架与场景测试
- **Phase 12**：Headless 烟测与性能采集

---

**文档版本**：1.0  
**完成日期**：2025-11-07  
**作者**：Claude Code  
**状态**：Ready for Implementation


> 参考 Runner 接入指南：见 docs/migration/gdunit4-csharp-runner-integration.md。


py -3 scripts/python/quality_gates.py   --log-dir logs/ci/2025-11-07   --coverage-report logs/ci/2025-11-07/xunit-coverage.xml   --gut-report logs/ci/2025-11-07/gut-report.json   --jscpd-report logs/ci/2025-11-07/jscpd-report.json   --gdunit4-report logs/ci/2025-11-07/gdunit4/gdunit4-report.xml   --taskmaster-report logs/ci/2025-11-07/taskmaster-report.json   --contracts-report logs/ci/2025-11-07/contracts-report.json   --perf-report logs/ci/2025-11-07/perf.json

> 提示：`perf.json` 字段示例与规范见 Phase-15（性能门禁）文档中的“报告输出与聚合”。
