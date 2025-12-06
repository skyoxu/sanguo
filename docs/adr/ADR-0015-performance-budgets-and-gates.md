# ADR-0015: 性能预算与门禁统一（Accepted）

Date: 2025-09-12
Updated: 2025-10-26 (Phase 8: Performance Regression Automation)
Status: Accepted
Deciders: Core Maintainers
Approver: Architecture Team
Supersedes: None
Related: build gates, E2E perf, release health, Phase 8 Automation

## Context

现状存在多处性能预算与门禁定义（脚本/测试/文档），容易出现口径不一致；首屏受 Phaser 依赖影响，交互路径偶发抖动，CI 难以稳定阻断回归。

## Decision

1. 预算与阈值

- 交互 P95：dev 200ms / staging 150ms / prod 100ms。
- 冷启动 P95：按 `DEFAULT_LATENCY_BUDGET.assetLoad.cold`（3s 基线），后续随产品阶段收紧。
- Bundle（gzip）：`phaser` ≤ 500kB、`react-vendor` ≤ 150kB、initial 合计 ≤ 400kB。

2. 门禁统一

- `guard:bundle` 唯一指向 `scripts/ci/bundle-budget-gate.mjs`（gzip 预算）。
- E2E 性能用例以 P95 采样，使用双 rAF 与预热稳定采样；在 CI 环境按 `SENTRY_ENVIRONMENT` 或 `NODE_ENV` 选择阈值。
- 两周软门→硬门：初期以警告（不 fail），两周后改为硬门（fail job）。

3. 首屏策略

- 通过 `React.lazy`、动态导入，将 Phaser 与场景从 initial 中剥离；首屏仅渲染骨架/按钮。
- 后续逐步移除源码内顶层 `import 'phaser'`（场景/管理器）改为运行时加载。

4. 观测与 Release Health

- 对冷启动/交互/场景切换上报 transaction/span；CI 对比上一基线，若 Crash‑Free 或性能低于阈值则阻断。

## Consequences

- 统一的门禁脚本与阈值，减少配置漂移；PR 可附可视化报告与 P95 摘要作为证据。
- 首屏体积与冷启时延可预期下降；交互 P95 更稳定，避免假阴/假阳。
- 需要补充 ADR/CI 文档与环境变量说明。

## Alternatives

- 继续使用多脚本/多阈值（否，漂移风险高）。
- 仅以平均值断言（否，无法覆盖尾部抖动）。

## Notes

- 本 ADR 落地后观察两周，再将软门切换为硬门；必要时设相对基线偏移阈值（±10%）。

---

## Phase 8: Performance Regression Automation (2025-10-26)

### 自动化工具与工作流

1. **Lighthouse CI 集成**
   - 配置文件: `.lighthouserc.json`
   - 对比脚本: `scripts/ci/compare-lighthouse.mjs`
   - GitHub Actions: `.github/workflows/pr-performance-lighthouse.yml`
   - **阈值**:
     - Performance: ≥90 (regression threshold: -5 points)
     - Accessibility: ≥95 (regression threshold: -3 points)
     - Best Practices: ≥85 (regression threshold: -5 points)
     - SEO: ≥90 (regression threshold: -5 points)

2. **Bundle Size 回归检测**
   - 对比脚本: `scripts/ci/compare-bundle-size.mjs`
   - GitHub Actions: `.github/workflows/pr-performance-bundle.yml`
   - **阈值**:
     - 总大小: ≤2MB (regression threshold: +10%)
     - 基准对比: main 分支作为 baseline

3. **First Contentful Paint (FCP) P95 测试**
   - E2E 测试: `tests/e2e/performance/first-paint.spec.ts`
   - 采样策略（Electron 环境附注）：
     - 复用单个 Electron 应用实例，按轮次 `page.reload()`，避免多次重启带来的额外噪声与不稳定。
     - 每轮在业务就绪信号后执行两帧 `requestAnimationFrame` 预热，再读取 `Performance API` 的 `first-contentful-paint`。
     - 默认降采样为 5 次（可通过 `FP_RUNS` 覆盖）。
   - 门禁策略：
     - CI 默认“软门禁”（Soft Gate）——仅记录与告警，不 fail（`FP_SOFT_GATE=1` 或 `PERF_GATE_MODE=soft`）。
     - 预发/生产使用硬门禁（Hard Gate）——未达阈值直接 fail（`FP_SOFT_GATE=0` 或 `PERF_GATE_MODE=hard`）。
   - 环境阈值（未显式指定 `FP_P95_THRESHOLD_MS` 时按以下选择）：
     - dev：≤400ms
     - staging（预发）：≤300ms
     - production：≤200ms（保持本 ADR 既定基线）
   - 工具：Playwright + Performance API
   - 配置开关：
     - `FP_P95_THRESHOLD_MS`：覆盖阈值；
     - `FP_RUNS`：覆盖采样次数（默认 5）；
     - `FP_SOFT_GATE`/`PERF_GATE_MODE`：软/硬门禁开关（`soft|hard`）。

4. **PR 评论集成**
   - 集成脚本: `scripts/pr-integration.mjs`
   - 功能: 合并 Lighthouse、Bundle、FCP 数据生成统一 PR 评论
   - 阻断逻辑:
     - Performance/Accessibility 未达标 → 阻断合并
     - Bundle 超过 2MB 或回归 >10% → 阻断合并
     - FCP P95 >200ms → 阻断合并

### NPM Scripts

```json
{
  "lighthouse:ci": "lhci autorun --config=.lighthouserc.json",
  "lighthouse:compare": "node scripts/ci/compare-lighthouse.mjs",
  "perf:lighthouse": "npm run build && npm run lighthouse:ci",
  "perf:bundle": "node scripts/ci/compare-bundle-size.mjs",
  "perf:fcp": "playwright test tests/e2e/performance/first-paint.spec.ts --reporter=line",
  "phase8:lighthouse": "npm run build && npm run lighthouse:ci && npm run lighthouse:compare",
  "phase8:all": "npm run phase8:lighthouse && npm run perf:bundle && npm run perf:fcp"
}
```

### CI 环境要求

- Windows-2022 runner (与项目开发环境一致)
- Node.js 22
- PowerShell 7 (pwsh)
- 需要 `npm run build` 生成 dist/ 目录

### 报告输出

所有性能回归检测生成 JSON 报告:

- `lighthouse-regression.json` - Lighthouse 分数对比
- `bundle-regression.json` - Bundle 大小对比
- `fcp-performance.json` - FCP P95 统计

### 工作流触发条件

所有性能工作流在以下条件触发:

- PR 打开、同步、重新打开
- 影响文件: `src/**/*.{ts,tsx}`, `electron/**/*.{ts,js,cjs}`, `index.html`, `vite.config.ts`, `package.json`, `package-lock.json`

### 实施计划参考

详见: `docs/implementation-plans/Phase-8-Performance-Regression-Implementation-Plan.md`
