---
ADR-ID: ADR-0008
title: 部署与发布策略（Windows-only）- Electron Builder + GitHub Releases
status: Accepted
decision-time: '2025-08-17'
deciders: [架构团队, DevOps团队, 安全团队]
archRefs: [CH03, CH07, CH10]
verification:
  - path: scripts/release/updater-config-check.mjs
    assert: electron-updater configured with correct channel and provider
  - path: scripts/release/signing-verify.mjs
    assert: Windows Authenticode 代码签名验证通过（仅 Windows）
  - path: scripts/release/rollout.mjs
    assert: Rollout gates on Release Health and supports pause/rollback
impact-scope:
  - build/
  - electron-builder.json
  - .github/workflows/（Windows-only runners）
  - scripts/release.mjs
tech-tags:
  - electron-builder
  - github-releases
  - deployment
  - ci-cd
  - auto-update
depends-on:
  - ADR-0005
depended-by: []
test-coverage: tests/unit/adr-0008.spec.ts
monitoring-metrics:
  - implementation_coverage
  - compliance_rate
executable-deliverables:
  - electron-builder.json（仅 Windows 目标）
  - .github/workflows/release.yml（windows-latest + pwsh）
  - scripts/release-automation.mjs
supersedes: []
---

# ADR-0008: 部署发布与自动更新策略（Windows-only）

注：本 ADR 收敛为 Windows-only。文档中原有跨平台（macOS/Linux）内容已移除或转为历史参考，不再作为现行要求。

## Context and Problem Statement

仅面向 Windows 平台分发的 Electron 应用需要建立可靠的部署发布与自动更新流程，确保安全性（代码签名）、可靠性（渐进式发布与回滚）、以及良好的使用体验（无缝更新）。

## Decision Drivers

- 满足 Windows 平台分发与签名（Authenticode）要求
- 与 Release Health（ADR-0003）集成，具备健康门禁与回滚能力
- 支持渐进式发布，降低大规模部署风险
- 保持流水线一致性（Windows runner + PowerShell shell）与可维护性

## Considered Options

- electron-updater + Windows 签名 + 渐进式发布（选定）
- Squirrel.Windows + 手动分发
- 仅 GitHub Releases 无自动更新（高运维成本）

## Decision Outcome

选择的方案：electron-updater + Windows 代码签名 + 渐进式发布（Windows-only）

## CI Runner & Shell 策略（Windows-only）

- 默认运行器 `runs-on: windows-latest`
- 统一默认 shell：`defaults.run.shell: pwsh`
- 如需使用第三方工具仅支持 Bash，步骤级显式 `shell: bash` 并标注原因
- 通知/旁路步骤优先使用步骤级 `if:` 与必要 `continue-on-error`

示例（Windows-only 发布 Job 精简示意）：

```yaml
jobs:
  release:
    runs-on: windows-latest
    defaults:
      run:
        shell: pwsh
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - name: Install deps
        run: npm ci
      - name: Import Windows certificate
        run: |
          $Bytes = [Convert]::FromBase64String("${{ secrets.WINDOWS_CERT_P12 }}")
          New-Item -ItemType Directory -Force -Path "build\\certs" | Out-Null
          [IO.File]::WriteAllBytes("build\\certs\\windows-cert.p12", $Bytes)
      - name: Build (Windows)
        run: npm run build:electron
      - name: Sign artifacts
        run: node scripts/release/signing-verify.mjs
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: release-windows
          path: dist\\
```

紧急回滚关键步骤（pwsh 语法示例）：

```yaml
- name: Pre-rollback validation
  run: |
    Write-Host "Validating rollback prerequisites..."
    if (-not (Test-Path -Path "artifacts/manifest.json" -PathType Leaf)) {
      Write-Error "Missing artifacts/manifest.json"
      exit 1
    }
    $version = "${{ env.PREV_GA_VERSION }}"
    $manifest = Get-Content artifacts/manifest.json -Raw | ConvertFrom-Json
    $exists = $manifest.PSObject.Properties.Name -contains $version
    if (-not $exists) {
      Write-Error "Target version $version not found in manifest"
      exit 1
    }

- name: Send emergency notification
  if: ${{ env.WEBHOOK_URL != '' }}
  env:
    WEBHOOK_URL: ${{ secrets.WEBHOOK_URL }}
  run: |
    $payload = @{
      text = "Emergency Rollback"
      attachments = @(@{
        color = "warning"
        fields = @(
          @{ title = "Target Version"; value = "${{ env.PREV_GA_VERSION }}"; short = $true },
          @{ title = "Triggered By";  value = "${{ github.actor }}";         short = $true }
        )
        text = "Rollback initiated on Windows"
      })
    } | ConvertTo-Json -Depth 5
    try {
      Invoke-RestMethod -Uri $env:WEBHOOK_URL -Method Post -Body $payload -ContentType 'application/json'
      Write-Host "Notification sent"
    } catch {
      Write-Warning "Notification failed: $($_.Exception.Message)"
    }
  continue-on-error: true
```

### electron-updater 核心配置

```ts
// electron/main/auto-updater.ts
import { autoUpdater } from 'electron-updater';
import { app, BrowserWindow, dialog } from 'electron';
import log from 'electron-log';

export class AutoUpdaterManager {
  private mainWindow: BrowserWindow | null = null;
  private isUpdateAvailable = false;
  private updateDownloaded = false;

  constructor() {
    this.configureUpdater();
    this.setupEventHandlers();
  }

  private configureUpdater(): void {
    autoUpdater.setFeedURL({
      provider: 'github',
      owner: 'buildgame',
      repo: 'vitegame',
      private: false,
    });
    autoUpdater.logger = log;
    (autoUpdater.logger as any).transports.file.level = 'info';
    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = true;
    autoUpdater.allowPrerelease = process.env.NODE_ENV === 'development';
  }

  private setupEventHandlers(): void {
    autoUpdater.on('checking-for-update', () => this.send('update-checking'));
    autoUpdater.on('update-available', info => {
      this.isUpdateAvailable = true;
      this.send('update-available', { version: info.version });
    });
    autoUpdater.on('update-not-available', () =>
      this.send('update-not-available')
    );
    autoUpdater.on('error', err => this.send('update-error', err.message));
    autoUpdater.on('download-progress', p =>
      this.send('update-download-progress', p)
    );
    autoUpdater.on('update-downloaded', info => {
      this.updateDownloaded = true;
      this.send('update-downloaded', { version: info.version });
      this.promptInstall(info);
    });
  }

  private async promptInstall(info: any): Promise<void> {
    const result = await dialog.showMessageBox(this.mainWindow!, {
      type: 'info',
      title: '更新已下载',
      message: `新版 ${info.version} 已下载，是否安装？`,
      buttons: ['立即安装', '稍后安装'],
      defaultId: 0,
      cancelId: 1,
    });
    if (result.response === 0) autoUpdater.quitAndInstall();
  }

  public setMainWindow(window: BrowserWindow): void {
    this.mainWindow = window;
  }
  public async checkForUpdates(): Promise<void> {
    if (app.isPackaged) await autoUpdater.checkForUpdates();
  }
  public async downloadUpdate(): Promise<void> {
    if (this.isUpdateAvailable) await autoUpdater.downloadUpdate();
  }
  public quitAndInstall(): void {
    if (this.updateDownloaded) autoUpdater.quitAndInstall();
  }
  private send(channel: string, data?: any) {
    this.mainWindow?.webContents.send(channel, data);
  }
}
```

### CI/CD 集成（Windows-only）

```yaml
# .github/workflows/release.yml（节选）
name: Release

env:
  SENTRY_ORG: ${{ secrets.SENTRY_ORG }}
  SENTRY_PROJECT: ${{ secrets.SENTRY_PROJECT }}
  SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}

permissions:
  contents: write
  actions: read
  id-token: write

defaults:
  run:
    shell: pwsh

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - name: Import Windows certificate
        run: |
          $Bytes = [Convert]::FromBase64String("${{ secrets.WINDOWS_CERT_P12 }}")
          New-Item -ItemType Directory -Force -Path "build\\certs" | Out-Null
          [IO.File]::WriteAllBytes("build\\certs\\windows-cert.p12", $Bytes)
      - run: npm run build:release
```

### 渐进式发布策略（概述）

- 采用阶段百分比（如 5%/25%/50%/100%）推进
- 结合 Sentry Release Health 指标作为门禁（Crash-Free Users/Sessions 阈值）
- 不达标自动阻断或触发回滚

### 回滚步骤（概述）

1. 校验回滚清单与目标版本（manifest.json）
2. 更新 feed（latest.yml）指向上一个稳定版本
3. 推送变更并发送通知，监控系统稳定性

## References

- Windows Code Signing Guide
- GitHub Releases API
- electron-builder / electron-updater 文档
