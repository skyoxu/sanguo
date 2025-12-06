---
ADR-ID: ADR-0002
title: Electron安全基线 - 三层拦截与沙箱策略
status: Accepted
decision-time: '2025-08-17'
deciders: [架构团队, 安全团队]
archRefs: [CH01, CH02, CH03, CH04]
verification:
  - path: electron/security/handlers.ts
    assert: nodeIntegration=false, contextIsolation=true, sandbox=true are enforced
  - path: tests/e2e/security.spec.ts
    assert: External windows denied by default and non-whitelisted navigations blocked
  - path: scripts/security/scan-csp.mjs
    assert: Production CSP contains no 'unsafe-inline' and connect-src is whitelisted only
  - path: electron/security/permissions.ts
    assert: PermissionRequest/PermissionCheck handlers default-deny
impact-scope: [electron/, preload/, security/, tests/e2e/security/]
tech-tags: [electron, security, sandbox, CSP, contextIsolation, nodeIntegration]
depends-on: []
depended-by: [ADR-0005, ADR-0008]
test-coverage: tests/e2e/security/electron-security.spec.ts
monitoring-metrics:
  [
    security_config_compliance,
    security_sandbox_enabled,
    security_csp_violations,
  ]
executable-deliverables:
  - electron/security.ts
  - tests/e2e/security/electron-security.spec.ts
  - scripts/scan_electron_safety.mjs
supersedes: []
---

# ADR-0002: Electron安全基线

## Context and Problem Statement

Electron框架默认提供强大的系统能力，但同时带来了较大的安全攻击面。需要建立严格的安全基线，最小化潜在的XSS、RCE和其他安全风险，确保桌面应用的安全性符合企业级要求。

## Decision Drivers

- 减少XSS攻击导致的系统权限提升风险
- 防止恶意脚本通过Node.js API执行任意代码
- 满足企业安全合规要求（SOC2、ISO27001）
- 遵循Electron官方安全最佳实践
- 支持安全审计和渗透测试
- 建立可量化的安全门禁机制

## Considered Options

- **严格沙箱模式**: nodeIntegration=false + contextIsolation=true + sandbox=true
- **部分隔离模式**: 仅启用contextIsolation，保留部分Node集成
- **宽松模式**: 保持Electron默认设置（已拒绝）
- **零信任模式**: 完全禁用所有系统API（开发成本过高）

## Decision Outcome

选择的方案：**严格沙箱模式**

### 核心安全配置

**BrowserWindow安全配置**：

```javascript
new BrowserWindow({
  webPreferences: {
    nodeIntegration: false, // 禁用渲染进程Node.js集成
    contextIsolation: true, // 启用上下文隔离
    sandbox: true, // 启用沙箱模式
    allowRunningInsecureContent: false, // 禁止混合内容
    experimentalFeatures: false, // 禁用实验性功能
    enableRemoteModule: false, // 禁用remote模块
    webSecurity: true, // 启用Web安全
    preload: path.join(__dirname, 'preload.js'),
  },
});
```

**内容安全策略（CSP）**：

```html
<meta
  http-equiv="Content-Security-Policy"
  content="
  default-src 'self';
  script-src 'self' 'nonce-${RUNTIME_NONCE}';
  style-src 'self' 'nonce-${RUNTIME_NONCE}';
  img-src 'self' data: https:;
  font-src 'self' data:;
  connect-src 'self' https://api.${PRODUCT_DOMAIN} wss://api.${PRODUCT_DOMAIN} https://sentry.io;
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
"
/>
```

**Nonce机制实现**：

```javascript
// 主进程中生成运行时nonce
import crypto from 'crypto';

class CSPManager {
  private static generateNonce(): string {
    return crypto.randomBytes(16).toString('base64');
  }

  static createCSPHeader(nonce: string): string {
    return `
      default-src 'self';
      script-src 'self' 'nonce-${nonce}';
      style-src 'self' 'nonce-${nonce}';
      img-src 'self' data: https:;
      font-src 'self' data:;
      connect-src 'self' https://api.${process.env.PRODUCT_DOMAIN} wss://api.${process.env.PRODUCT_DOMAIN} https://sentry.io;
      object-src 'none';
      base-uri 'self';
      form-action 'self';
      frame-ancestors 'none';
    `.replace(/\s+/g, ' ').trim();
  }

  static injectNonceToHTML(html: string, nonce: string): string {
    return html
      .replace(/<script([^>]*)>/g, `<script$1 nonce="${nonce}">`)
      .replace(/<style([^>]*)>/g, `<style$1 nonce="${nonce}">`);
  }
}
```

**Preload脚本API白名单**：

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // 文件操作白名单
  readFile: path => ipcRenderer.invoke('file:read', path),
  writeFile: (path, data) => ipcRenderer.invoke('file:write', path, data),

  // 系统信息白名单
  getSystemInfo: () => ipcRenderer.invoke('system:info'),

  // 应用控制白名单
  minimize: () => ipcRenderer.send('window:minimize'),
  close: () => ipcRenderer.send('window:close'),
});
```

### Positive Consequences

- 显著降低XSS导致的RCE风险（风险降低90%+）
- 提供最强的安全隔离和权限最小化
- 符合SOC2/ISO27001安全合规要求
- 支持自动化安全工具扫描和审计
- 遵循OWASP和业界安全最佳实践
- 建立可量化的安全指标体系

### Negative Consequences

- 调试复杂度增加，需要额外的开发工具配置
- 需要通过IPC进行主渲染进程通信，增加开发成本
- 某些第三方库可能需要适配或替换
- 初期开发时需要额外的安全配置工作
- 性能轻微下降（<5%）

## Verification

### 5大验证类别体系

#### 1. 配置安全验证

- **测试验证**: tests/e2e/security/electron-config.spec.ts
- **门禁脚本**: scripts/scan_electron_safety.mjs
- **监控指标**: security.config_compliance, security.sandbox_enabled
- **验证频率**: 每次构建 + 每日定时扫描

**验证清单**：

- [ ] `nodeIntegration: false` - 渲染进程禁用Node集成
- [ ] `contextIsolation: true` - 上下文完全隔离
- [ ] `sandbox: true` - 沙箱模式启用
- [ ] `allowRunningInsecureContent: false` - 禁止混合内容
- [ ] `experimentalFeatures: false` - 禁用实验功能
- [ ] `enableRemoteModule: false` - 禁用remote模块

#### 2. CSP策略验证

- **测试验证**: tests/e2e/security/csp-policy.spec.ts
- **门禁脚本**: scripts/verify_csp_policy.mjs
- **监控指标**: security.csp_violations, security.inline_script_blocks
- **验证频率**: 每次部署 + 运行时监控

**验证清单**：

- [x] `script-src 'self' 'nonce-${RUNTIME_NONCE}'` - 仅允许同源脚本和nonce授权脚本
- [x] `style-src 'self' 'nonce-${RUNTIME_NONCE}'` - 仅允许同源样式和nonce授权内联样式
- [x] `object-src 'none'` - 禁止对象嵌入
- [x] `base-uri 'self'` - 限制base标签URI
- [x] 无`unsafe-inline`和`unsafe-eval` - 通过nonce机制安全支持必要的内联代码
- [x] `connect-src` 保持Sentry集成 - 支持监控和错误追踪
- [ ] CSP报告机制启用 - 违规行为监控
- [ ] Nonce生成机制安全 - 每次页面加载生成新的随机nonce

#### 3. Preload脚本安全验证

- **测试验证**: tests/unit/security/preload-whitelist.spec.ts
- **门禁脚本**: scripts/audit_preload_apis.mjs
- **监控指标**: security.api_exposure_count, security.dangerous_apis
- **验证频率**: 每次代码提交 + 安全审计

**验证清单**：

- [ ] 仅暴露必要的API白名单 - 最小权限原则
- [ ] 所有暴露的API进行输入验证 - 防注入攻击
- [ ] 使用`contextBridge.exposeInMainWorld` - 标准桥接方式
- [ ] 禁止暴露完整的`require`或fs API - 防止权限绕过
- [ ] API参数类型严格验证 - TypeScript强类型

#### 4. 权限和导航控制验证

- **测试验证**: tests/e2e/security/navigation-control.spec.ts
- **门禁脚本**: scripts/check_navigation_guards.mjs
- **监控指标**: security.navigation_blocks, security.permission_denials
- **验证频率**: 每次发布 + 渗透测试

**验证清单**：

- [ ] `setPermissionRequestHandler` - 权限请求拦截
- [ ] `will-navigate`事件拦截 - 导航行为控制
- [ ] `setWindowOpenHandler` - 新窗口控制
- [ ] 外部URL访问白名单 - 限制网络请求范围
- [ ] 文件协议访问限制 - 防止本地文件泄露

#### 5. 运行时安全监控

- **测试验证**: tests/integration/security/runtime-monitoring.spec.ts
- **门禁脚本**: scripts/security_runtime_check.mjs
- **监控指标**: security.runtime_violations, security.exploit_attempts
- **验证频率**: 实时监控 + 每小时汇总

**验证清单**：

- [ ] CSP违规实时报告 - 异常行为检测
- [ ] 异常IPC调用监控 - 恶意脚本识别
- [ ] 内存异常访问检测 - 缓冲区溢出防护
- [ ] 网络请求异常监控 - 数据泄露防护
- [ ] 文件系统访问审计 - 敏感文件保护

## Operational Playbook

### 升级步骤

1. **配置更新**: 更新BrowserWindow配置启用所有安全选项
2. **预加载脚本**: 实施Preload脚本API白名单机制
3. **CSP部署**: 配置严格CSP策略到所有HTML页面
4. **Nonce机制**: 实现运行时nonce生成和注入系统
   - 在主进程中实现CSPManager类
   - 为每个页面加载生成唯一nonce
   - 自动注入nonce到script和style标签
5. **事件处理**: 添加权限和导航事件处理器
6. **监控启用**: 部署运行时安全监控和告警系统
7. **验证测试**: 运行完整的5大类安全验证套件

### 回滚步骤

1. **紧急回滚**: 如遇严重兼容性问题，可临时关闭sandbox模式
2. **CSP降级**: 逐步调整CSP策略至最低可接受安全级别
3. **API恢复**: 临时开放必要的API访问权限
4. **问题记录**: 详细记录安全问题并制定修复计划
5. **不可回滚**: nodeIntegration和contextIsolation设置不可回滚

### 迁移指南

- **代码重构**: 现有代码需要通过IPC与主进程通信
- **依赖清理**: 移除渲染进程中的直接Node.js API调用
- **库兼容性**: 第三方库需验证沙箱模式兼容性
- **调试配置**: 开发时使用devtools的security面板检查配置
- **团队培训**: 安全开发最佳实践和工具使用培训

### 安全事件响应流程

1. **告警触发**: 自动监控系统检测到安全异常
2. **风险评估**: 安全团队评估事件级别和影响范围
3. **应急处置**: 根据级别执行相应的应急处置措施
4. **根因分析**: 深入分析安全事件的根本原因
5. **改进措施**: 更新安全策略和防护机制

## Phase 9: 依赖安全审计自动化

### 概述

Phase 9 通过自动化工具实现本ADR的依赖安全合规要求，集成npm audit和许可证合规检查到CI/CD流程。

### 自动化工具

#### 1. npm audit集成 (scripts/ci/parse-npm-audit.mjs)

**功能**：

- 解析npm audit v7+ JSON格式
- 提取CVE ID和漏洞详情
- 生成可执行的修复建议
- 构建依赖链路径

**阻塞规则**：

- Critical漏洞 → 阻止合并
- High漏洞 → 阻止合并
- Moderate漏洞 → 仅警告
- Low/Info漏洞 → 记录但不阻止

#### 2. 许可证合规检查 (scripts/ci/validate-licenses.mjs)

**功能**：

- 检测禁止的Copyleft许可证
- 标记未知/缺失的许可证
- 验证许可证白名单合规性

**禁止的许可证（Copyleft）**：

```javascript
const PROHIBITED_LICENSES = [
  'GPL-3.0',
  'GPL-3.0-only',
  'GPL-3.0-or-later',
  'AGPL-3.0',
  'AGPL-3.0-only',
  'AGPL-3.0-or-later',
  'GPL-2.0',
  'GPL-2.0-only',
  'GPL-2.0-or-later', // 为一致性也禁止 GPL-2.0
  'LGPL-3.0',
  'LGPL-3.0-only',
  'LGPL-3.0-or-later', // Lesser GPL 对 Electron 同样有问题
];
```

**理由**：

- **GPL/AGPL**: 强 Copyleft 许可证，要求整个项目开源，与商业闭源 Electron 应用不兼容
- **LGPL**: 虽然比 GPL 宽松，但在 Electron 动态链接场景下仍存在合规风险，禁止使用以避免法律纠纷

**允许的许可证（Permissive）**：

```javascript
const ALLOWED_LICENSES = [
  'MIT',
  'Apache-2.0',
  'BSD-3-Clause',
  'BSD-2-Clause',
  'ISC',
  'CC0-1.0',
  '0BSD',
  'Unlicense',
  'Python-2.0', // Python Software Foundation License
  'Zlib', // zlib License
  'CC-BY-3.0', // Creative Commons Attribution 3.0
  'CC-BY-4.0', // Creative Commons Attribution 4.0
  'BlueOak-1.0.0', // Blue Oak Model License
  'WTFPL', // Do What The F*ck You Want To Public License
];
```

**阻塞规则**：

- GPL/AGPL/LGPL 许可证 → 阻止合并 (Critical 级别违规)
- 未知/缺失许可证 → 仅警告 (需人工审核)
- 允许的许可证 → 通过

#### 3. 统一安全报告 (scripts/ci/generate-security-report.mjs)

**功能**：

- 合并npm audit + 许可证验证结果
- 计算综合阻塞状态
- 生成Markdown摘要 (security-summary.md)
- 生成JSON报告 (security-audit.json)

**综合阻塞逻辑**：

```javascript
const blocksMerge =
  vulnCritical > 0 || // Critical漏洞阻止
  vulnHigh > 0 || // High漏洞阻止
  licenseViolations > 0; // GPL/AGPL违规阻止
```

**状态定义**：

- `BLOCKED`: 存在Critical/High漏洞或许可证违规
- `WARNING`: 存在Moderate漏洞或未知许可证
- `PASSED`: 所有检查通过

#### 4. GitHub Actions工作流 (.github/workflows/pr-security-audit.yml)

**触发条件**：

- package.json变更
- package-lock.json变更
- PR opened/synchronize/reopened事件

**执行步骤**：

1. 运行npm audit (moderate+严重级别)
2. 解析npm audit结果 (parse-npm-audit.mjs)
3. 生成许可证清单 (license-checker)
4. 验证许可证合规性 (validate-licenses.mjs)
5. 生成统一安全报告 (generate-security-report.mjs)
6. 上传安全审计报告为artifacts
7. 检查阻塞状态并相应失败/通过

**输出文件**：

- `audit-result.json`: npm audit原始输出
- `audit-parsed.json`: 解析后的漏洞数据
- `licenses.json`: 完整许可证清单
- `licenses-validation.json`: 许可证合规验证结果
- `security-audit.json`: 统一安全报告
- `security-summary.md`: Markdown摘要

#### 5. PR评论集成 (scripts/pr-integration.mjs)

**功能**：

- 自动读取security-audit.json
- 在PR评论中显示安全审计结果
- 包含漏洞详情和许可证违规
- 明确标记阻塞原因

**评论内容**：

- 整体安全状态 (PASSED/WARNING/BLOCKED)
- npm audit漏洞按严重级别分类
- Critical/High漏洞详细信息 (CVE, 建议修复)
- 许可证违规详情
- 未知许可证清单
- 阻塞原因说明

### 验收标准

- [ ] package.json变更时自动触发安全审计工作流
- [ ] Critical/High漏洞正确阻止PR合并
- [ ] GPL/AGPL许可证正确识别并阻止合并
- [ ] 安全报告在30秒内生成
- [ ] PR评论显示完整安全审计结果
- [ ] artifacts包含所有中间和最终报告
- [ ] 阻塞状态正确反映在CI状态检查中

### 监控指标

- `security.audit_runtime`: 安全审计执行时间
- `security.vulnerabilities_blocked`: 因漏洞阻止的PR数量
- `security.license_violations_blocked`: 因许可证违规阻止的PR数量
- `security.false_positives`: 误报计数
- `security.audit_failures`: 审计工具失败次数

### 相关文件

- 实现计划: `docs/implementation-plans/Phase-9-Dependency-Security-Implementation-Plan.md`
- GitHub工作流: `.github/workflows/pr-security-audit.yml`
- 解析脚本: `scripts/ci/parse-npm-audit.mjs`
- 验证脚本: `scripts/ci/validate-licenses.mjs`
- 报告生成: `scripts/ci/generate-security-report.mjs`
- PR集成: `scripts/pr-integration.mjs`

## References

- **CH章节关联**: CH01, CH02
- **相关ADR**: ADR-0004-event-bus-and-contracts, ADR-0005-quality-gates
- **外部文档**:
  - [Electron Security Guide](https://www.electronjs.org/docs/tutorial/security)
  - [Electronegativity Scanner](https://github.com/doyensec/electronegativity)
  - [OWASP Electron Security](https://owasp.org/www-project-electron-security/)
  - [CSP Level 3 Specification](https://www.w3.org/TR/CSP3/)
- **安全工具**: Electronegativity, ESLint security rules, Snyk vulnerability scanner, npm audit, license-checker
- **合规框架**: SOC2 CC6.1, ISO27001 A.12.6.1
- **Phase 9实现**: `docs/implementation-plans/Phase-9-Dependency-Security-Implementation-Plan.md`
- **Godot+C# 变体**:
  - 安全基线在 Godot 模板中通过 `SecurityAudit`（Autoload 启动审计）、`SqliteDataStore`（DB 路径守卫 + CI 审计）与 `SecurityHttpClient`（HTTP 验证与审计）落地，详细规则见 `docs/migration/Phase-14-Godot-Security-Baseline.md` 与 ADR-0006。
