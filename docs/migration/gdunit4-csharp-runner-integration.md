# GdUnit4 C# Runner 接入指南（Windows）

> 目标：在 Windows 环境下以 C# 方式执行 Godot 场景级测试，规范命令行参数、报告文件命名与 CI 工件收集。

---

## 1. 前置条件

- Windows 11
- Godot 4.5（.NET 版本），可通过 `godot --version` 验证
- 工程目录：`Game.Godot/`（包含 `project.godot`）
- 已安装 GdUnit4 插件（addons/gdunit4/ 存在）

目录假定：

```
Game.Godot/
  project.godot
  addons/
    gdunit4/
      runners/GdUnit4CmdLnRunner.gd
  Tests/
    Scenes/...
    Signals/...
```

---

## 2. 命令行执行

基础命令：

```
godot --headless --path Game.Godot \
  --script res://addons/gdunit4/runners/GdUnit4CmdLnRunner.gd \
  --gdunit-headless=yes --repeat=1
```

说明：
- `--headless`：无界面运行（CI 必备）
- `--path`：Godot 工程根路径
- `--script`：命令行 Runner 入口脚本（GdUnit4 提供）
- `--gdunit-headless=yes`：以 Headless 模式执行测试
- `--repeat=1`：重复次数（可根据需要调整）

注：命令行参数以 GdUnit4 文档为准；若需要筛选目录/用例，可在 `Tests/` 下分层组织并通过 Runner 内部约定执行。

---

## 3. 报告命名与输出规范

- 本地/CI 统一输出目录：`logs/ci/YYYY-MM-DD/gdunit4/`
- 文件命名建议：
  - `gdunit4-report.xml`（若采集 JUnit XML）
  - `gdunit4-report.json`（若采集 JSON）
  - `gdunit4-console.log`（命令行原始输出）

说明：GdUnit4 默认在 `addons/gdunit4/reports/` 生成报告。建议在测试结束后将报告复制到 `logs/ci/YYYY-MM-DD/gdunit4/`，统一命名后交由门禁聚合。

---

## 4. Python 执行与收集（推荐）

最小执行脚本：

```python
# scripts/run_gdunit4_tests.py
import subprocess, sys, shutil
from pathlib import Path
from datetime import datetime

PROJECT = Path('Game.Godot')
RUNNER  = 'res://addons/gdunit4/runners/GdUnit4CmdLnRunner.gd'

def run() -> None:
    cmd = [
        'godot','--headless','--path', str(PROJECT),
        '--script', RUNNER,
        '--gdunit-headless=yes','--repeat=1'
    ]
    print('>', ' '.join(cmd))
    subprocess.check_call(cmd)

def collect() -> None:
    # 源：GdUnit4 默认报告目录
    src = PROJECT / 'addons' / 'gdunit4' / 'reports'
    if not src.exists():
        print('no reports at', src); return
    date = datetime.now().strftime('%Y-%m-%d')
    dest = Path('logs') / 'ci' / date / 'gdunit4'
    dest.mkdir(parents=True, exist_ok=True)
    for f in src.glob('*'):
        if f.is_file():
            name = {
                'report.xml' : 'gdunit4-report.xml',
                'report.json': 'gdunit4-report.json',
            }.get(f.name, f.name)
            shutil.copy2(f, dest / name)
    # 可选：保存控制台输出
    # 将子进程 stdout 重定向到 logs/ci/.../gdunit4-console.log 即可

if __name__ == '__main__':
    try:
        run(); collect()
    except subprocess.CalledProcessError as e:
        print('GdUnit4 tests failed:', e, file=sys.stderr)
        sys.exit(e.returncode)
```

---

## 5. CI 工件收集（GitHub Actions 示意）

Windows Runner 示例（仅关键片段）：

```yaml
jobs:
  gdunit4-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run GdUnit4 (headless)
        run: |
          py -3 scripts\run_gdunit4_tests.py

      - name: Upload test artifacts
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: gdunit4-reports
          path: logs/ci/**/gdunit4/*
```

说明：
- 建议在 CI 中将 `logs/ci/YYYY-MM-DD/gdunit4/` 作为统一工件目录，便于后续门禁聚合（Phase-13）。
- 若需要与其他测试（xUnit/性能/安全）报告汇总，请在后续步骤合并为 `quality-gates.json/html`。

---

## 6. 常见问题

- 找不到 Runner 脚本：
  - 确认 `addons/gdunit4/runners/GdUnit4CmdLnRunner.gd` 存在
  - 确认路径以 Godot 工程为基准（`--path Game.Godot`）
- 报告目录为空：
  - 检查 GdUnit4 配置是否启用了报告生成
  - 确认测试确实执行（非零发现）
- 用例定位与过滤：
  - 推荐按目录划分模块，将不同模块的测试放入 `Tests/Scenes/`、`Tests/Signals/` 等，以 Runner 缺省策略批量执行

---

## 7. 与 C# 场景测试的一致性建议

- 以 C# 实现测试节点（Godot 脚本）时：
  - 使用 `GD.Load<PackedScene>()` + `Instantiate()` + `AddChild()` 装配场景
  - 使用 `EmitSignal`/`Connect`/`ToSignal` 模式验证交互
  - 将断言失败表现为抛出异常，Runner 捕获并计入失败
- 报告生成统一落盘到 `logs/ci/YYYY-MM-DD/gdunit4/`，文件名稳定，以便下游聚合

