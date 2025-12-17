# 架构完整性检查清单（Godot 模板）

本清单用于人工快速自检“文档口径是否与模板一致”。自动化校验以脚本输出为准（见下文“自动化检查”）。

## 1) 实施状态检查（按 ADR）

### 安全基线（ADR-0019）

- [ ] 仅允许 `res://`（只读）与 `user://`（读写）
- [ ] 外链/网络仅 HTTPS + 主机白名单；`GD_OFFLINE_MODE=1` 时拒绝出网并审计
- [ ] OS.execute 默认禁用或开发态显式开启并审计
- [ ] 安全相关失败会写入 `security-audit.jsonl`（logs/）

### 可观测与 Release Health（ADR-0003）

- [ ] Release 工作流 Step Summary 输出 `Sentry: secrets_detected=... upload_executed=...`
- [ ] 运行时结构化日志可回溯（user://logs 与 logs/**）

### 事件与契约（ADR-0004 + ADR-0020）

- [ ] Contracts SSoT 在 `Game.Core/Contracts/**`（不在 Game.Godot/Scenes/scripts）
- [ ] 事件命名遵循 `${DOMAIN_PREFIX}.<entity>.<action>`
- [ ] Overlay 08 文档引用的 Contracts 路径真实存在（validate_contracts.py）

### 质量门禁（ADR-0005）

- [ ] 单入口：`scripts/ci/quality_gate.ps1` 或 `scripts/python/quality_gates.py`
- [ ] dotnet 单测与引擎自检可稳定通过并产出 logs/**
- [ ] 性能门禁（如启用）以 ADR-0015 口径为准

## 2) Base 文档完整性（docs/architecture/base）

- [ ] `01-introduction-and-goals-v2.md`
- [ ] `02-security-baseline-godot-v2.md`（正文为 Godot 安全基线）
- [ ] `03-observability-sentry-logging-v2.md`
- [ ] `04-system-context-c4-event-flows-v2.md`
- [ ] `05-data-models-and-storage-ports-v2.md`
- [ ] `06-runtime-view-loops-state-machines-error-paths-v2.md`
- [ ] `07-dev-build-and-gates-v2.md`
- [ ] `08-crosscutting-and-feature-slices.base.md`（模板）
- [ ] `09-performance-and-capacity-v2.md`
- [ ] `10-i18n-ops-release-v2.md`
- [ ] `11-risks-and-technical-debt-v2.md`
- [ ] `12-glossary-v2.md`

## 3) 自动化检查（Windows）

- Base 清洁度：`pwsh -File scripts/ci/verify_base_clean.ps1`
- 编码/疑似乱码：`py -3 scripts/python/check_encoding.py --root docs`
- 旧栈术语取证：`py -3 scripts/python/scan_doc_stack_terms.py --root docs`
- 契约引用校验：`py -3 scripts/python/validate_contracts.py`
- 一键门禁：`pwsh -File scripts/ci/quality_gate.ps1 -GodotBin "$env:GODOT_BIN"`
