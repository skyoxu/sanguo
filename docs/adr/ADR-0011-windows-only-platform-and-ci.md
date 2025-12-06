---
ADR-ID: ADR-0011
title: 平台与 CI 策略（Windows-only）
status: Accepted
decision-time: '2025-09-10'
deciders: [架构团队, DevOps团队]
archRefs: [CH01, CH03, CH07, CH09, CH10]
depends-on: [ADR-0005, ADR-0008]
supersedes: [ADR-0009]
impact-scope:
  - .github/workflows/
  - scripts/ci/**
  - scripts/release/**
  - build/**
verification:
  - path: .github/workflows/validate-workflows.yml
    assert: 所有 Job 在 windows-latest + pwsh 下运行；Bash 仅步骤级声明
  - path: scripts/ci/workflow-shell-guard.mjs
    assert: 校验 defaults.run.shell= pwsh 且无未声明的 POSIX 语法误用
  - path: .github/workflows/ci.yml
    assert: 关键 Job 明确 runs-on: windows-latest
monitoring-metrics:
  - ci_compliance_rate
  - gate_pass_rate
---

# ADR-0011: 平台与 CI 策略（Windows-only）

## Context

项目仅支持 Windows 平台。为降低脚本语法分歧与运行器差异带来的失败率，统一 CI 运行环境与 Shell 策略，简化发布/回滚链路；同步废止跨平台策略（ADR-0009）。

## Decision

- 平台范围：Windows-only（运行时与分发）；跨平台目标废止。
- CI 运行器：默认 `runs-on: windows-latest`。
- Shell 策略：Job 级统一 `defaults.run.shell: pwsh`；不得在未声明 `shell: bash` 的情况下使用 POSIX 语法。
- 例外管理：确需 Bash 的第三方 Action 可步骤级 `shell: bash`，并在 PR 说明中标注原因；不得隐式依赖 Bash 默认。
- 控制流：通知与旁路步骤使用步骤级 `if:` 与必要的 `continue-on-error`，替代脚本内判空。
- 守卫：在工作流校验任务中扫描 `.github/workflows`，发现未声明 Bash 却使用 POSIX `if [ ... ]` 或随意 `shell: bash` 即失败；该 Job 作为分支保护的必需检查。
- 日志：所有 CI/脚本输出写入 `logs/YYYYMMDD/<module>/` 以便取证与审计。

## Consequences

- 优点：统一语法/环境，降低 CI 失败率与脚本歧义；发布与回滚路径收敛。
- 代价：不再验证 macOS/Linux；未来若恢复跨平台，需要撤销本 ADR 并恢复 OS 矩阵。

## Alternatives

- 继续维持多 OS 矩阵（与 Windows-only 目标冲突）。
- 在 Windows runner 上默认使用 Bash（与团队 PowerShell 技栈与系统工具链冲突）。

## Compliance Checklist

- [ ] 所有 Windows Job 顶层 `defaults.run.shell: pwsh`。
- [ ] Bash 片段显式步骤 `shell: bash` 且在步骤/注释中记录理由。
- [ ] 回滚与通知步骤：使用 `if:` 判空；失败不拖垮主流程（必要时 `continue-on-error`）。
- [ ] `validate-workflows` 校验通过，并纳入分支保护。
