---
ADR-ID: ADR-0005
title: 质量门禁与测试策略（多层自动化）
status: Accepted
decision-time: '2025-08-17'
deciders: [架构团队, QA团队, DevOps团队]
archRefs: [CH01, CH03, CH07, CH09]
verification:
  - path: tests/e2e/smoke.electron.spec.ts
    assert: Electron 应用可启动且 preload API 可用
  - path: scripts/quality_gates.mjs
    assert: 单元测试覆盖率达标，阈值为硬编码且不可绕过
  - path: scripts/perf/assert-p95.mjs
    assert: 关键交互 P95/事件处理 P95 达到设定阈值
  - path: scripts/release-health-gate.mjs
    assert: Release Health 阈值通过方可继续
impact-scope:
  [tests/, scripts/quality_gates.mjs, playwright.config.ts, vitest.config.ts]
tech-tags: [playwright, vitest, testing, quality-gates, ci-cd, coverage]
depends-on: [ADR-0002, ADR-0003]
depended-by: [ADR-0008]
test-coverage: tests/meta/quality-gates.spec.ts
monitoring-metrics:
  [test_coverage, test_success_rate, build_time, gate_pass_rate]
executable-deliverables:
  - scripts/quality_gates.mjs
  - tests/e2e/smoke.electron.spec.ts
  - vitest.config.ts
  - playwright.config.ts
supersedes: []
---

# ADR-0005: 质量门禁与测试策略

## Context

AI 驱动开发需要"能跑 → 能用 → 不退化"的自动门禁护栏。为保证功能正确性、性能与稳定性，需要在 Windows-only CI 环境下以硬编码阈值执行多层测试与质量检查，并统一日志落盘 `logs/` 便于取证。

**重要术语澄清**：

- **Release Health Gate（见 ADR-0003）**：基于 Sentry Crash-Free 指标的发布健康门禁，监控崩溃率与会话质量，属于可观测性范畴。
- **Gameplay Telemetry Gate（已移除）**：曾基于游戏内自定义埋点事件（first_build、first_wave、median_session_duration 等）的可玩度门禁，依赖本地事件存储与导出脚本聚合。该实现已于 2025 年完全移除，原因包括离线场景复杂性、隐私合规成本、维护负担。替代方案为 T2 Playable E2E（交互式可玩度测试）+ 性能基线 Gate（P95 阈值），提供更直接的功能与性能验证。

## Decision

### 核心原则：质量检查统一入口

**覆盖率门槛由全局 `guard:ci` 统一约束**：所有代码质量检查（覆盖率、重复度、复杂度、依赖守卫）通过单一入口 `npm run guard:ci` 执行，避免质量检查分散到多个专用工作流（如 doc-sync、security-audit 等）。

- **统一执行点**：`npm run guard:ci` = `typecheck && lint && test:unit && guard:dup && guard:complexity && guard:deps && test:e2e`
- **硬编码质量阈值**（在 `scripts/quality_gates.mjs` 中强制，不可绕过）：
  - **覆盖率**：Lines ≥ 90%、Branches ≥ 85%、Functions ≥ 88%、Statements ≥ 90%
  - **E2E 通过率**：≥ 95%，关键路径 100% 通过
  - **性能预算**：应用启动时间、内存、CPU 使用等 P95 指标达标（详见门禁脚本）
- **测试金字塔**：Vitest（单元/契约）+ Playwright×Electron（E2E/安全/性能冒烟）

**职责分离原则**：专用工作流（Phase 7 AI 代码审查、Phase 10 文档同步验证）仅负责其特定领域验证，**不重复执行**覆盖率等通用质量检查。

- **Phase 7: AI 辅助代码审查门禁（AI-Assisted Code Review Gate）**：
  - **工作流**：ESLint → violations.json → AI 语义分析 → code-review.json → PR 评论
  - **阻塞条件**：Critical 级别问题数量 > 0 时阻止 PR 合并
  - **安全规则覆盖**：
    - ESLint 安全插件（eslint-plugin-security, eslint-plugin-no-unsanitized 等 5+ 规则）
    - 自定义 Electron 安全规则（no-node-integration, no-context-isolation-false, validate-ipc-params）
  - **AI 分析配置**：
    - 最小分析级别：medium severity
    - 上下文代码行数：±5 lines
    - 最大分析数量：50 个违规（成本控制）
    - 批次大小：10 个违规/批次
  - **输出格式**：
    - violations.json - 结构化 ESLint 违规数据（按严重性与类别分组）
    - code-review.json - AI 语义分析结果（包含误报过滤、修复建议、ADR 引用）
  - **PR 集成**：自动发布 PR 评论，包含严重性徽章、代码上下文、ADR 合规检查、修复建议
  - **实现位置**：
    - 工作流：`.github/workflows/ai-code-review.yml`
    - 脚本：`scripts/ci/ai-semantic-review.mjs`, `scripts/ci/lint-to-json.mjs`
    - PR 集成：`scripts/pr-integration.mjs` (扩展 PRCommentGenerator 类)
    - npm 脚本：`phase7:review` (完整工作流), `ai:review` (仅 AI 分析)
  - **相关 ADR**：ADR-0002 (Electron 安全基线), ADR-0004 (事件总线与契约)
- **Phase 10: 文档同步验证门禁（Documentation Sync Validation Gate）**：
  - **目标**：自动检测代码-文档不一致，强制契约变更同步文档更新
  - **职责边界（关键原则）**：
    - **doc-sync 工作流专注领域**：文档一致性验证（ADR 引用、契约-文档同步、testid 覆盖、Electron 安全配置）
    - **明确不负责代码质量检查**：doc-sync 工作流**不运行** `vitest --coverage`、`jscpd`、`complexity-report` 等代码质量工具
    - **覆盖率由 guard:ci 统一约束**：单元测试覆盖率（≥90% lines, ≥85% branches）、代码重复度、复杂度、依赖守卫等质量检查，统一在全局 `npm run guard:ci` 中执行，确保单一入口、避免重复检查
  - **验证规则（4 层）**：
    1. **ADR 引用一致性（MEDIUM 严重性）**：PR 引用的 ADR 必须存在且与变更相关，非阻塞
    2. **契约变更 → 08 章文档同步（HIGH 严重性）**：`src/shared/contracts/**` 变更必须同步更新对应 `docs/architecture/overlays/<PRD-ID>/08/**` 文档，阻塞合并
    3. **data-testid 覆盖（LOW 严重性）**：新增 data-testid 应有对应 Playwright 测试，非阻塞
    4. **Electron 安全配置同步（HIGH 严重性）**：`electron/main.ts` 或 `electron/preload.ts` 变更必须同步更新 `docs/adr/ADR-0002-electron-security.md`，阻塞合并
  - **阻塞逻辑**：仅 HIGH 严重性问题阻止 PR 合并，MEDIUM/LOW 问题仅警告
  - **工作流**：
    - 个别检查器 → `validate-doc-sync.mjs` 聚合 → `generate-doc-sync-report.mjs` → PR 评论
    - 使用 AST 解析（@babel/parser）检测 data-testid 属性
    - 使用 git diff 检测文件变更并匹配文档同步规则
  - **输出格式**：
    - adr-validation.json - ADR 引用检查结果
    - contract-sync.json - 契约-文档同步检查结果
    - testid-coverage.json - data-testid 覆盖检查结果
    - doc-sync-validation.json - 聚合验证结果（包含阻塞状态）
    - doc-sync-report.json - Markdown 格式 PR 评论
  - **PR 集成**：扩展 `scripts/pr-integration.mjs` 中的 PRCommentGenerator 类，添加 `generateDocSyncComment()` 方法
  - **实现位置**：
    - 工作流：`.github/workflows/pr-doc-sync.yml`
    - 检查器：`scripts/ci/check-adr-refs.mjs`, `scripts/ci/check-contract-docs.mjs`, `scripts/ci/check-testid-coverage.mjs`
    - 聚合器：`scripts/ci/validate-doc-sync.mjs`
    - 报告生成：`scripts/ci/generate-doc-sync-report.mjs`
    - PR 集成：`scripts/pr-integration.mjs` (generateDocSyncComment)
  - **测试覆盖**：
    - 单元测试：`tests/unit/scripts/ci/check-*.test.mjs`, `tests/unit/scripts/ci/validate-doc-sync.test.mjs`
    - E2E 测试：`tests/e2e/ci/doc-sync-workflow.spec.ts`
  - **相关 ADR**：ADR-0002 (Electron 安全基线), ADR-0004 (事件总线与契约)
- CI 规范（Windows-only）：所有 Job 运行在 `windows-latest` 且 `pwsh`；Playwright 安装使用 `npx playwright install`（Windows 无需 `--with-deps`）。
- 日志规约：构建/测试/门禁日志统一落盘 `logs/YYYYMMDD/{unit|guard|e2e}/`。
- **分支保护要求（Branch Protection Rules）**：
  - **主分支强制门禁**：以下 CI 检查必须在 main 分支上配置为 Required Status Checks：
    - `Playable Smoke (T2 Gate)`：交互式可玩度测试，确保核心游戏循环可用
    - `Unit Tests (coverage)`：单元测试覆盖率门禁，确保代码质量基线
    - `AI-Assisted Code Review` **(Phase 7)**：AI 辅助代码审查，阻止 Critical 级别安全/质量问题合并
    - `Documentation Sync Validation` **(Phase 10)**：文档同步验证，阻止 HIGH 严重性文档不一致问题合并（契约变更必须同步文档更新、Electron 安全配置变更必须同步 ADR-0002）
  - **PR 软门禁策略**：以下检查在 PR 上保持 `continue-on-error: true`，用于建立基线与发现趋势，但不阻塞合并：
    - `Static Quality Soft Gate`：代码重复、复杂度、依赖守卫（jscpd/complexity-report/depcruise/madge）
    - 其他性能与可观测性指标
  - **配置位置**：GitHub 仓库设置 → Branches → Branch protection rules → "main"
  - **信号噪声优化**：通过区分硬门禁与软门禁，避免非关键问题阻塞开发流程，同时保持核心质量基线不可妥协

## Consequences

- **正向**：
  - 质量阈值不可被"调低"；多层测试覆盖端到端路径；问题可追溯
  - **统一入口设计**：通过 `guard:ci` 单一入口管理所有代码质量检查，避免检查分散到多个工作流
  - **职责清晰**：专用工作流（AI 代码审查、文档同步验证）专注其特定领域，不重复运行通用质量检查
  - **资源优化**：覆盖率检查仅在 `guard:ci` 执行一次，避免 CI 资源浪费
- **代价**：
  - 初期测试成本增大；严格门禁可能降低短期提交速度；需治理不稳定用例
  - 需确保开发者理解职责边界：覆盖率由 `guard:ci` 保障，文档同步由 `pr-doc-sync` 保障

## Verification

- 单元：覆盖率报告 + 硬编码阈值校验。
- E2E：Electron 启动冒烟、关键交互 P95、预加载安全。
- 门禁：类型检查、Lint、安全扫描、依赖与循环依赖守卫。

## References

- CH 章节：CH07、CH05
- 相关 ADR：ADR‑0002（安全）、ADR‑0003（可观测性）
- 工具：Vitest、Playwright、GitHub Actions（Windows）
- 延伸：ADR‑0017（Quality Intelligence Dashboard and Governance）— 定义统一质量快照最小 schema、隐私与阈值治理、非阻断质量洞察集成
