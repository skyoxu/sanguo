# Phase 13 Backlog — Quality Gates Script（质量门禁脚本增强）

> 状态：Backlog（非当前模板 DoD，供后续按需启用）
> 目的：承接 Phase-13-Quality-Gates-Script.md 中尚未在本 Godot+C# 模板落地的 10 项蓝图门禁，避免“文档超前、实现滞后”，同时为后续项目提供可选优化清单。
> 相关脚本：`scripts/python/quality_gates.py`、`scripts/python/ci_pipeline.py`、`scripts/ci/quality_gate.ps1`

---

## B1：xUnit 覆盖率阈值提升至蓝图标准

- 现状：
  - 当前模板中，`scripts/python/run_dotnet.py` 将行/分支覆盖率视为 **软门禁**：
    - 覆盖率低于阈值会在 `logs/unit/<date>/summary.json` 中标记为 warning，但不会直接导致 CI 失败；
  - 阈值也低于 Phase 13 蓝图中的 90%（行）/85%（分支），以降低模板初期使用门槛。
- 蓝图目标：
  - 行覆盖率 ≥ 90%，分支覆盖率 ≥ 85%（参见 Phase-13 表格 #1/#2，归口 ADR‑0005）。
- 后续建议：
  - 在实际项目成熟后，逐步提高 run_dotnet.py 中的覆盖率阈值；
  - 视团队接受度，将覆盖率不足从“软门禁”提升为“硬门禁”（exit code 1），或在 Quality Gate Workflow 中单独标红。
- 优先级：P1（适合作为真实业务项目的强化项，模板阶段保持软门禁即可）。

---

## B2：GdUnit4 集成门禁统一进入 quality_gates.py

- 现状：
  - GdUnit4 测试（Adapters/Security/Integration/UI/A11y 等）目前主要通过：
    - `.github/workflows/ci-windows.yml` 和 `.github/workflows/windows-quality-gate.yml` 直接调用 `scripts/python/run_gdunit.py`；
  - `quality_gates.py` 目前只委托 `ci_pipeline.py`，未直接感知 GdUnit4 结果。
- 蓝图目标：
  - 将关键 GdUnit4 集合（如 Adapters+Security 硬门禁、Integration/UI 软门禁）纳入 quality_gates.py：
    - 提供参数化入口，例如：
      - `quality_gates.py all --with-gdunit-adapters-security --with-gdunit-integration-ui`；
    - 在统一 summary 中记录各集 rc/统计信息，并参与 Quality Gate 决策。
- 后续建议：
  - 先在本地/非保护分支试验，将 Adapters+Security 小集作为硬门禁接入 quality_gates.py；
  - Integration/UI 等更易抖动的集合保持为软门禁，仅影响 `quality-gates-summary.json` 与 CI 报告，不直接阻断构建。
- 优先级：P1–P2（可提升信心，但需要结合 GdUnit4 稳定性逐步接入）。

---

## B3：代码重复率与圈复杂度门禁

- 现状：
  - Phase-13 蓝图中定义了重复率（jscpd）、圈复杂度（SonarQube Metrics）相关门禁：
    - Duplication % ≤ 2%；
    - Max Cyclomatic ≤ 10；
    - Avg Cyclomatic ≤ 5；
  - 当前 Godot+C# 模板未集成 jscpd/SonarQube/NetArchTest 等工具。
- 蓝图目标：
  - 能够在 CI 中生成重复率与复杂度报告，并将关键指标读入 quality_gates.py 进行判定。
- 后续建议（任选其一或组合）：
  - 方案 A（轻量）：使用 jscpd + 简单复杂度工具（或 Roslyn 分析器）生成 JSON 摘要，quality_gates.py 解析阈值；
  - 方案 B（重型）：集成 SonarQube（自托管或云），以 Sonar Quality Gate 结果为准；
  - 方案 C：使用 NetArchTest + 自定义指标脚本估算复杂度/依赖，结果写入 logs/ci/** 并聚合。
- 优先级：P2（对模板使用者要求较高，适合在实际项目阶段按需接入）。

---

## B4：性能 P95 与审计 JSONL 校验

- 现状：
  - Phase-7/12 已对性能与审计日志给出规范：
    - logs/perf/<date>/summary.json 中记录 P50/P95；
    - logs/ci/<date>/security-audit.jsonl 记录安全相关审计；
  - 但目前 Quality Gates 只要求“产出这些文件”，尚未对其中数值/格式做自动化门禁。
- 蓝图目标：
  - 将性能与审计纳入 quality_gates.py 的自动检查：
    - 性能门禁：P95 ≤ 16.67ms（或通过环境变量覆盖），超出视为软/硬失败；
    - 审计门禁：security-audit.jsonl 每行必须是合法 JSON，包含 {ts, action, reason, target, caller} 等字段。
- 后续建议：
  - 新增 `scripts/python/validate_perf.py` 与 `scripts/python/validate_audit_logs.py`，在 quality_gates.py 中可选调用；
  - 初期作为软门禁（只告警不阻断），待报告稳定后再考虑提升为硬门禁。
- 优先级：P2–P3（适合作为成熟项目的附加保障，模板阶段保持简单）。

---

## B5：NetArchTest 架构测试与跨层依赖门禁

- 现状：
  - Phase-13 文档中给出了 NetArchTest 的示例（Core 不得依赖 Godot 等）；
  - 当前 Game.Core.Tests 还未正式纳入这类架构测试。
- 蓝图目标：
  - 在 Game.Core.Tests 或单独的 Architecture 测试项目中增加：
    - “Core 不依赖 Godot”的约束；
    - 各层（Core/Adapters/Scenes）之间的依赖规则（Ports/Adapters 模式）。
- 后续建议：
  - 先以 xUnit 架构测试的形式集成到 dotnet test 中，让违反依赖规则的改动直接导致测试失败；
  - 再在 quality_gates.py 中将这些测试结果视为硬门禁的一部分。
- 优先级：P2（对模板用户有指导意义，但初期可留空）。

---

## 使用说明

- 对于基于本模板创建的新项目：
  - 建议在业务复杂度提升、团队对质量有更高要求时，按 B1→B2→B3/B4→B5 的顺序逐步启用；
  - 每启用一项门禁，应同步更新 Phase-13 文档与 ADR‑0005 的“验证”段落，避免“工具启用了但文档没跟上”。

- 对于模板本身：
  - 当前 Phase 13 仅要求 `quality_gates.py + ci_pipeline.py` 对 dotnet/selfcheck/encoding 三类门禁给出统一入口与清晰日志；
  - 本 Backlog 文件用来记录“蓝图中尚未落地的质量门禁”，帮助后续迭代避免把 Phase 13 再次拉得过大。

