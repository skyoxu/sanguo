---
title: 10 i18n ops release v2
status: base-SSoT
adr_refs: [ADR-0001, ADR-0002, ADR-0003, ADR-0005, ADR-0008, ADR-0011]
placeholders: unknown-app, Unknown Product, ${ORG}, ${REPO}, ${RELEASE_CDN}, dev-team, dev-project, production, dev, 0.0.0, ${PRODUCT_DOWNLOAD_URL}
derived_from: 10-i18n-ops-release-v2.md
last_generated: 2025-08-21
---

> 目标：在 optimized 基础上补齐 **通道矩阵（Dev/Staging/Prod）**、**签名/公证失败的降级与告警**、**更新回退策略** 与 **i18n 发布前质量门禁**，确保工程闭环。

## 0.1 发布上下文视图（C4 Context）

```mermaid
C4Context
    title Release Operations Context for Unknown Product
    Person(admin, "Release Admin", "管理发布流程和监控")
    Person(user, "End User", "接收自动更新")
    System(app, "Unknown Product (Electron App)", "桌面应用程序")
    System_Ext(cdn, "${RELEASE_CDN}", "发布分发网络")
    System_Ext(sentry, "dev-team", "监控与健康指标")
    System_Ext(notary, "Apple Notary Service", "macOS公证服务")
    System_Ext(signing, "Code Signing Authority", "代码签名服务")

    Rel(admin, app, "执行发布流程", "CI/CD")
    Rel(app, cdn, "上传构建产物", "HTTPS")
    Rel(user, cdn, "下载更新", "HTTPS")
    Rel(app, sentry, "上报健康指标", "Crash-Free/Adoption")
    Rel(app, notary, "提交公证", "notarytool")
    Rel(app, signing, "代码签名", "SignTool/codesign")
```

## 0.2 发布容器视图（C4 Container）

```mermaid
C4Container
    title Unknown Product Release Containers
    Container(main, "Main Process", "Node.js", "发布更新逻辑")
    Container(renderer, "Renderer Process", "React", "用户更新提示")
    Container(updater, "Auto Updater", "electron-updater", "自动更新引擎")
    Container(notifier, "Health Reporter", "TypeScript", "健康指标上报")
    ContainerDb(metadata, "Release Metadata", "JSON", "版本信息存储")
    System_Ext(cdn, "${RELEASE_CDN}", "分发服务")

    Rel(main, updater, "检查更新", "IPC")
    Rel(updater, cdn, "获取latest.yml", "HTTPS")
    Rel(main, renderer, "显示更新状态", "contextBridge")
    Rel(notifier, cdn, "上报指标", "POST /health")
    Rel(updater, metadata, "缓存版本信息", "File I/O")
```

## A) 通道矩阵与放量策略

```ts
export interface RolloutGate {
  metric: 'crashFreeUsers' | 'crashFreeSessions' | 'adoptionRate';
  threshold: number;
  waitMs: number;
  action: 'block' | 'warn' | 'rollback';
}
export const CHANNELS = {
  dev: {
    url: '${RELEASE_CDN}/dev',
    gates: [
      { metric: 'adoptionRate', threshold: 0.1, waitMs: 0, action: 'warn' },
    ],
  },
  staging: {
    url: '${RELEASE_CDN}/staging',
    gates: [
      {
        metric: 'crashFreeUsers',
        threshold: 99.0,
        waitMs: 3600000,
        action: 'block',
      },
    ],
  },
  prod: {
    url: '${RELEASE_CDN}/prod',
    gates: [
      {
        metric: 'crashFreeUsers',
        threshold: 99.5,
        waitMs: 3600000,
        action: 'rollback',
      },
    ],
  },
} as const;
```

## B) 签名/公证失败的降级与可观测

```ts
export interface SigNotarizeResult {
  platform: 'win' | 'mac';
  step: 'sign' | 'notarize' | 'staple' | 'verify';
  ok: boolean;
  msg?: string;
}
export function onSigNotarizeFailure(r: SigNotarizeResult) {
  /* 上报 Sentry & 触发告警（与 03 章一致） */
}
```

## C) 更新回退（版本保护）

```ts
export interface RollbackPlan {
  maxAutoRollbacks: number;
  cooldownMs: number;
  channels: ReadonlyArray<keyof typeof CHANNELS>;
}
export class AutoRollback {
  private count = 0;
  constructor(private plan: RollbackPlan) {}
  async maybeRollback(metric: 'crashFreeUsers', value: number) {
    if (value < 99.5 && this.count < this.plan.maxAutoRollbacks) {
      this.count++; /* 执行回退 */
    }
  }
}
```

## D) i18n 发布门禁（Key Debt）

```ts
export interface I18nDebt {
  locale: string;
  missing: number;
  ratio: number;
  criticalMissing: string[];
}
export function detectMissingTranslations(): Promise<I18nDebt[]> {
  return Promise.resolve([]);
} // 占位

// 发布事件契约
export interface ReleaseEvent {
  type:
    | 'gamedev.release.started'
    | 'gamedev.release.completed'
    | 'gamedev.release.failed';
  version: string;
  channel: keyof typeof CHANNELS;
  timestamp: number;
}
export interface HealthEvent {
  type: 'gamedev.health.threshold_breached';
  metric: string;
  value: number;
  threshold: number;
  channel: string;
}
export interface I18nEvent {
  type: 'gamedev.i18n.validation_failed';
  locale: string;
  missingKeys: string[];
  completeness: number;
}
```

## E) CI 片段（签名/公证/健康门禁）

```yaml
# .github/workflows/release.yml（摘要）
name: Release Pipeline
on:
  push: { tags: ['v*'] }
  workflow_dispatch:
    {
      inputs:
        {
          channel:
            { required: true, type: choice, options: [dev, staging, prod] },
        },
    }

jobs:
  build:
    strategy: { matrix: { os: [windows-latest, macos-latest] } }
    steps:
      - name: Build & Package
        run: npm run build && npm run package:${{ matrix.os }}
      - name: Sign (Windows)
        if: matrix.os == 'windows-latest'
        # 推荐 Node 入口（当前代理到 PowerShell；TODO: 实现原生 Node 签名流程）
        run: node scripts/release/windows-sign.mjs
        env:
          {
            WINDOWS_CERT_FILE: '${{ secrets.WIN_CERT }}',
            WINDOWS_CERT_PASSWORD: '${{ secrets.WIN_CERT_PASS }}',
          }
      - name: Notarize (macOS)
        if: matrix.os == 'macos-latest'
        run: node scripts/release/macos-notarize.mjs
        env:
          {
            APPLE_ID: '${{ secrets.APPLE_ID }}',
            APPLE_PASSWORD: '${{ secrets.APPLE_PASSWORD }}',
          }
      - name: Health Gate
        run: node scripts/release/health-gate-check.mjs --channel=${{ github.event.inputs.channel || 'prod' }}
        env: { SENTRY_ORG: 'dev-team', SENTRY_PROJECT: 'dev-project' }
      - name: Upload to CDN
        run: node scripts/release/upload-artifacts.mjs --target=${RELEASE_CDN}/${{ github.event.inputs.channel }}
```

```bash
# scripts/release/health-gate-check.mjs（关键片段）
const thresholds = {
  dev: { crashFreeUsers: 98.0, adoptionRate: 0.1 },
  staging: { crashFreeUsers: 99.0, crashFreeSessions: 99.5 },
  prod: { crashFreeUsers: 99.5, crashFreeSessions: 99.8 }
};
```

## F) 验收清单（含回滚）

- [ ] HEALTH_GATES 生效且可触发**自动回滚**；
- [ ] 通道矩阵与阈值可通过 ENV 覆盖；
- [ ] 签名/公证失败进入降级路径并**产生告警**；
- [ ] i18n 完整度 ≥95%，**关键 keys 不得缺失**；
- [ ] 与 02/03/07 章节的策略引用**就近可见**。
