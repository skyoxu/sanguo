---
ADR-ID: ADR-0003
title: 可观测性与 Release Health（Sentry）- Godot 口径
status: Accepted
decision-time: '2025-12-16'
deciders: [架构团队, SRE团队]
archRefs: [CH03, CH07, CH10]
verification:
  - path: scripts/python/check_sentry_secrets.py
    assert: Prints one-line summary and appends to GitHub Step Summary when available
  - path: .github/workflows/windows-release.yml
    assert: Release job always runs "Sentry sourcemap env check (soft gate)"
  - path: .github/workflows/windows-release-tag.yml
    assert: Release job always runs "Sentry sourcemap env check (soft gate)"
impact-scope: [Game.Godot/Scripts/Obs/, scripts/python/, .github/workflows/]
tech-tags: [sentry, observability, release-health, logs, windows, godot]
depends-on: [ADR-0011, ADR-0019]
depended-by: [ADR-0005, ADR-0008]
supersedes: []
---

# ADR-0003: 可观测性与 Release Health（Sentry）

## Context

模板需要一套可复用的可观测基线：让故障可回溯、发布可评估、CI 可取证。Godot 运行时与旧的 LegacyDesktopShell 工具链完全不同，因此本 ADR 以 **Godot + Windows-only** 为口径定义最小可执行方案。

## Decision

### 1) Sentry Secrets 检测（软门禁）

- Release 工作流中总是运行（`if: always()`）：
  - `py -3 scripts/python/check_sentry_secrets.py`
- 该脚本只做两件事：
  - 检测 `SENTRY_AUTH_TOKEN`、`SENTRY_ORG`、`SENTRY_PROJECT` 是否齐全
  - 输出一行：`Sentry: secrets_detected=<true|false> upload_executed=<true|false>`
- 在 GitHub Actions 中：将该行追加到 Step Summary（UTF-8），但 **不阻断构建**。

### 2) Release Health 口径（引用）

- Crash-Free 指标口径延续 Sentry Releases + Sessions（阈值与放量策略由运维侧统一口径维护）。
- 本仓库当前实现为“可审计软门禁”（是否具备 Secrets、是否执行上传逻辑），不在此 ADR 内实现强阻断的 API 拉取门禁。

### 3) 本地结构化日志（取证）

- 运行时优先写入 `user://logs/**`（JSONL/摘要文件），CI 侧产物统一写入 `logs/**`。

## Consequences

- 正向：即使 Secrets 缺失也能稳定发布/构建，并明确在 Step Summary 中给出可审计结论。
- 代价：当前不包含“基于 Sentry API 的强门禁判定”，需要由后续工作流/脚本在不破坏模板可复制性的前提下引入。

