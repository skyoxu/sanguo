---
title: 11 risks and technical debt v2
status: base-SSoT
adr_refs: [ADR-0003, ADR-0005, ADR-0019, ADR-0015]
placeholders: Unknown Product, ${PRD_ID}, ${DOMAIN_PREFIX}
last_generated: 2025-12-16
---

# 11 风险与技术债（Base）

本章为 Base 提供一个最小的风险登记与技术债收敛口径，避免“问题存在但不可追溯”。具体业务风险写入 Overlay 08；Base 仅保留模板与执行规则。

## 1) 风险登记（Risk Register）

| ID | 风险 | 影响 | 概率 | 触发信号 | 缓解策略 | 证据/工件 |
| --- | --- | --- | --- | --- | --- | --- |
| R-SEC-01 | 安全策略回退导致越权访问 | 高 | 中 | 安全烟测失败/审计异常 | 强制走 ADR-0019 口径；拒绝默认放行 | `logs/ci/**/security-audit.jsonl` |
| R-PERF-01 | 帧时间回归未被发现 | 中 | 中 | `[PERF] p95_ms` 超阈 | 启用 `check_perf_budget.ps1`（阈值见 ADR-0015） | `logs/ci/**/headless.log` |
| R-CI-01 | CI 偶发失败不可定位 | 中 | 中 | 重跑通过/日志缺失 | 所有门禁必须产出 logs/** 工件 | `logs/ci/<YYYY-MM-DD>/` |
| R-OBS-01 | Release/Sentry 配置缺失导致无法回溯 | 中 | 中 | Step Summary 缺失或 secrets_detected=false | 保留软门禁与摘要输出（ADR-0003） | Step Summary + `logs/ci/**` |

## 2) 技术债约定（Debt Contract）

### 2.1 允许的技术债形式

仅允许使用统一格式记录技术债（便于 grep 与回链）：

- `TODO(owner=<name> due=<YYYY-MM-DD> issue=<url>): <short action>`

### 2.2 技术债必须包含

- Owner（负责人）
- Due（预期收敛日期）
- Issue/链接（可追溯）
- 回迁计划（短句即可）

## 3) 验收清单（合并前）

- [ ] 风险变更（安全/性能/发布健康）已引用对应 ADR
- [ ] 所有门禁/测试产物落盘 `logs/**`
- [ ] 新增的技术债符合统一 TODO 格式并具备 owner/due/issue

