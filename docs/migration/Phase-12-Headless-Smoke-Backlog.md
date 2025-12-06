# Phase 12 Backlog — Headless Smoke / 无界面冒烟

> 状态：Backlog（非当前模板 DoD，可按需渐进启用）

本文件用于记录 Phase 12（Headless Smoke Tests）中，当前模板阶段**尚未完全收口**但已有
明确方向的增强项，避免零散脚本与期望分离，同时为后续项目提供可选优化清单。

关联口径：
- 迁移文档：docs/migration/Phase-12-Headless-Smoke-Tests.md
- 日志规范：AGENTS.md / docs/testing-framework.md（logs/ci/** 结构）
- 运行脚本：scripts/ci/smoke_headless.ps1 · scripts/ci/smoke_exe.ps1 · scripts/ci/export_windows.ps1

---

## B1：Python 版 Headless Smoke 封装

- 现状：
  - 当前 Headless 冒烟由 PowerShell 脚本 `scripts/ci/smoke_headless.ps1` 驱动：
    - 参数：`-GodotBin`、`-Scene`（默认 Main.tscn）、`-TimeoutSec`、`-ProjectPath`；
    - 日志输出：`logs/ci/<ts>/smoke/headless.*.log`；
    - 判定逻辑：优先 `[TEMPLATE_SMOKE_READY]` → 其次 `[DB] opened` → 否则任意输出视为通过。
  - CI 中的 dry run 工作流（`.github/workflows/windows-smoke-dry-run.yml`）已调用该脚本，
    且你在项目中偏好“Python 脚本优先”。

- 目标：
  - 提供一个 Python 入口（例如 `scripts/python/smoke_headless.py`），实现与当前 PowerShell 脚本
    等价的功能：
    - 调用 Godot Headless 启动指定场景；
    - 采集 stdout/stderr 并写入 `logs/ci/<date>/smoke/**`；
    - 实现与现有完全一致的判定逻辑。

- Backlog 任务：
  1. 新增 `scripts/python/smoke_headless.py`，封装：
     - 参数：`--godot-bin`、`--scene`、`--timeout-sec`、`--project-path`；
     - 日志：创建 `logs/ci/<YYYYMMDD-HHmmss>/smoke/`，输出 `headless.out.log`、`headless.err.log`、`headless.log`；
     - 判定：完全复用现有 PowerShell 版本的逻辑（见 B2），但可通过 exit code 暴露到 CI；
  2. 在 Phase-12 文档中加入 Python 版本示例命令，同时保留 PowerShell 版本作为 Windows CI 的备选；
  3. 可选：在 `ci-windows.yml` / `windows-quality-gate.yml` 中，用 Python 版本替代直接调用 PowerShell，
     统一 CI 脚本风格。

- 优先级：P1（对你“Python 优先”的偏好有实际价值，改动对现有流程风险较低）。

---

## B2：收紧 Smoke 判定条件（Marker 优先）

- 现状：
  - `scripts/ci/smoke_headless.ps1` 当前的判定逻辑为：
    1. 日志中包含 `[TEMPLATE_SMOKE_READY]` → SMOKE PASS（marker）；
    2. 否则若包含 `[DB] opened` → SMOKE PASS（db opened）；
    3. 否则只要有任意输出 → SMOKE PASS（any output）；
    4. 无输出时仅记录警告并 `exit 0`，视为“模板级宽松判定”。
  - 该逻辑适合模板初期，但对后续实际项目来说偏松，可能掩盖启动问题（例如仅打印错误日志也算“有输出”）。

- 目标：
  - 在不破坏模板易用性的前提下，允许为某些分支/项目收紧 smoke 判定：
    - 强制要求看到 `[TEMPLATE_SMOKE_READY]` 或特定 marker 才记为 PASS（推荐配置）；
    - 仅“任意输出”不再作为默认 PASS 条件，而是改为“inconclusive/警告”。
  - 文档与脚本统一以 `[TEMPLATE_SMOKE_READY]` 作为首选 Smoke 通过标记，以 `[DB] opened` 作为第二优先级回退信号。

- Backlog 任务：
  1. 为 PowerShell/Python smoke 脚本增加一个可选参数（例如 `-Strict` 或 `--strict`）：
     - 非 strict：保留现有宽松逻辑，适用于模板初期和本地开发；
     - strict：要求 `[TEMPLATE_SMOKE_READY]` 或 `[DB] opened`，否则返回非零 exit code；
  2. 在 Phase-12 文档中说明 strict 模式适用场景（例如：某条受保护分支、预发布流水线）；
  3. 在 CI 配置中为 strict 模式预留注释示例，便于未来项目切换。

- 优先级：P1（提高 “smoke” 信号的可靠性，但需要谨慎 rollout，避免影响现有宽松模板体验）。

---

## 使用说明

- 对于基于本模板的项目：
  - 早期可以继续使用现有 PowerShell smoke 脚本和宽松判定逻辑，重点利用 Phase 11 的 GdUnit4 集成测试
    做业务级验证；
  - 当项目进入稳定期或需要更严格守门时，可按本 Backlog 中的 B1/B2 实施增强。
- 对于模板本身：
  - 当前 Phase 12 已具备“导入即跑”的 Headless Smoke 能力与 EXE 冒烟脚本，本 Backlog 主要记录
    “Python 化封装”和“判定条件收紧”这两类渐进优化，避免形成隐性技术债。
