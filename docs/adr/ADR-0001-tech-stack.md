---
ADR-ID: ADR-0001
title: 技术栈与版本策略 - Modern Stack选型
status: Accepted
decision-time: '2025-08-17'
deciders: [架构团队, 开发团队]
archRefs: [CH01, CH07, CH09, CH11]
verification:
  - path: scripts/stack/validate-versions.mjs
    assert: Node/Electron/Chromium versions match policy window
  - path: tests/e2e/smoke.electron.spec.ts
    assert: Electron app launches via _electron.launch and first window is visible
  - path: scripts/perf/assert-drift.mjs
    assert: Interaction P95 ≤ 100ms and Event P95 ≤ 50ms with ≤10% drift vs baseline
impact-scope: [package.json, vite.config.ts, tsconfig.json, electron/, src/]
tech-tags: [electron, react, vite, typescript, tailwind, phaser]
depends-on: []
depended-by: [ADR-0002, ADR-0005, ADR-0007]
test-coverage: tests/unit/tech-stack.spec.ts
monitoring-metrics: [build_time, bundle_size, dependency_vulnerabilities]
executable-deliverables:
  - package.json
  - vite.config.ts
  - tsconfig.json
  - scripts/tech-stack-validator.mjs
supersedes: []
---

# ADR-0001: 技术栈与版本策略

## Context and Problem Statement

桌面发行、Web前端工程化与2D游戏渲染需求并存，需要建立统一的技术栈选型与版本管理策略。同时需要平衡开发效率、包体积、安全性和长期维护成本，确保技术选型能够支撑项目的长期演进。

## Decision Drivers

- 跨平台桌面应用发行需求，需要原生系统集成能力
- 复杂UI界面开发需要成熟的前端框架支持
- 2D游戏渲染需要高性能Canvas/WebGL引擎
- 开发团队需要类型安全和现代化工程工具链
- 企业级安全和稳定性要求
- 长期技术债务管理和升级路径规划

## Considered Options

- **方案A**: Electron + React + Vite + Phaser + TypeScript + Tailwind
- **方案B**: 纯Web应用 + PWA (放弃桌面原生能力)
- **方案C**: Unity + C# (游戏引擎优先，UI开发成本高)
- **方案D**: C++/Rust原生 + WebView嵌入 (开发成本极高)

## Decision Outcome

选择的方案：**方案A - Electron全栈统一技术栈**

### 核心技术栈与版本策略

| 层次       | 技术选型         | 固定版本策略                    | 升级窗口   |
| ---------- | ---------------- | ------------------------------- | ---------- |
| 桌面容器   | **Electron**     | 当前：37.x，支持窗口：36.x-39.x | 每季度评估 |
| 渲染引擎   | **Chromium**     | 跟随Electron自动更新            | 被动跟随   |
| Node运行时 | **Node.js**      | 跟随Electron绑定版本            | 被动跟随   |
| 前端框架   | **React**        | 强制v19，禁止v18及以下          | 年度大版本 |
| 构建工具   | **Vite**         | 当前：7.x，支持窗口：6.x-7.x    | 半年度评估 |
| 游戏引擎   | **Phaser**       | 当前：3.90+，支持窗口：3.80+    | 季度评估   |
| 样式框架   | **Tailwind CSS** | 强制v4，禁止v3及以下            | 年度大版本 |
| 开发语言   | **TypeScript**   | 当前：5.8+，支持窗口：5.6+      | 半年度评估 |

### 版本联动与兼容性矩阵

**Electron → Chromium → Node.js 联动关系**：

- Electron 37.x → Chromium 130.x → Node.js 22.x
- 每个Electron版本绑定特定的Chromium和Node版本
- 升级Electron时必须验证Chromium API兼容性和Node.js模块兼容性

### Positive Consequences

- 同栈统一，降低技术复杂度和学习成本
- 社区生态成熟，第三方库和工具链丰富
- 类型安全保障，减少运行时错误
- 热更新和调试体验良好
- 跨平台一致性强

### Negative Consequences

- Electron包体积较大（~100MB+）
- 安全攻击面扩大，需要严格的安全治理
- 版本升级联动复杂，需要充分测试验证
- 内存占用相对原生应用较高
- 依赖第三方更新节奏，存在被动升级风险

## Verification

- **测试验证**: tests/unit/tech-stack.spec.ts, tests/e2e/electron-integration.spec.ts
- **门禁脚本**: scripts/verify_tech_stack.mjs
- **监控指标**: build.bundle_size, runtime.memory_usage, security.electron_version
- **升级验证矩阵**: 见下表

### 升级验证矩阵

| 验证类型       | 验证范围                 | 通过标准                      | 责任方    |
| -------------- | ------------------------ | ----------------------------- | --------- |
| **Smoke测试**  | 应用启动、基础功能       | 100%核心路径通过              | 自动化    |
| **Playwright** | E2E用户流程、IPC通信     | 95%用例通过，无阻断问题       | QA + Dev  |
| **性能P95**    | 启动时间、渲染帧率、内存 | P95 < 3s/60fps/512MB          | 性能团队  |
| **Crash-Free** | 崩溃率、会话质量         | ≥99.5% Users, ≥99.8% Sessions | SRE + Dev |
| **安全扫描**   | 依赖漏洞、Electron配置   | 0 High/Critical漏洞           | 安全团队  |

## Operational Playbook

### 升级步骤

1. **评估阶段**：检查目标版本的Breaking Changes和兼容性
2. **依赖更新**：按照联动关系更新package.json
3. **代码适配**：修复API变更和TypeScript类型问题
4. **测试验证**：执行完整的升级验证矩阵
5. **渐进发布**：通过Canary/Beta渠道验证稳定性

### 回滚步骤

1. **版本回退**：恢复到previous stable版本
2. **依赖降级**：rollback package.json和lockfile
3. **配置还原**：恢复相关构建和运行时配置
4. **验证测试**：确保回滚版本功能正常
5. **问题分析**：记录升级失败原因和解决方案

### 迁移指南

- **禁用自动更新**：package.json中锁定精确版本号
- **分批验证**：优先升级开发环境，再到测试和生产
- **文档同步**：更新技术文档和开发手册
- **团队培训**：新版本特性和API变更培训

## References

- **CH章节关联**: CH01, CH07
- **相关ADR**: ADR-0002-electron-security, ADR-0005-quality-gates
- **外部文档**:
  - [Electron Release Timeline](https://www.electronjs.org/docs/tutorial/releases)
  - [React 19 Migration Guide](https://react.dev/blog/2024/04/25/react-19)
  - [Vite Migration Guide](https://vite.dev/guide/migration.html)
- **版本兼容性**: [Electron to Chromium Versions](https://atom.io/download/electron/index.json)
