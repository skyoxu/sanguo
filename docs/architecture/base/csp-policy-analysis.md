# Content Security Policy (CSP) 策略分析

## 当前 CSP 配置

```html
<meta
  http-equiv="Content-Security-Policy"
  content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' ws: wss: https://api.${DOMAIN_OBSERVABILITY} https://${DOMAIN_OBSERVABILITY};"
/>
```

## 策略选择：default-src 'self' vs 'none'

### default-src 'self' (当前选择)

- **适用场景**: 需要加载本地资源的应用
- **优势**:
  - 允许加载同源资源，适合 Electron 应用的本地文件结构
  - 为其他指令提供合理的默认值
  - 在保证安全的前提下提供更好的开发体验
- **安全性**: 高（仍然阻止外部恶意资源）

### default-src 'none' (严格策略)

- **适用场景**: 高安全要求或纯静态内容
- **优势**:
  - 最严格的默认策略
  - 需要明确声明每个资源类型
- **劣势**: 需要为每个资源类型单独配置

## 当前配置安全分析

| 指令          | 配置                                                                                  | 安全级别 | 说明                             |
| ------------- | ------------------------------------------------------------------------------------- | -------- | -------------------------------- |
| `default-src` | `'self'`                                                                              | 高       | 只允许同源资源，阻止外部注入     |
| `script-src`  | `'self'`                                                                              | 高       | 只允许本地脚本，完全阻止外部脚本 |
| `style-src`   | `'self' 'unsafe-inline'`                                                              | 中高     | 允许内联样式，但限制外部样式表   |
| `img-src`     | `'self' data:`                                                                        | 高       | 允许本地图片和 data URI          |
| `font-src`    | `'self'`                                                                              | 高       | 只允许本地字体文件               |
| `connect-src` | `'self' ws: wss: https://api.${DOMAIN_OBSERVABILITY} https://${DOMAIN_OBSERVABILITY}` | 高       | 明确允许必要的网络连接           |

## Electron 安全最佳实践符合性

### ✅ 符合要求

1. **阻止外部脚本执行**: `script-src 'self'` 完全阻止外部脚本
2. **限制网络请求**: `connect-src` 明确白名单化必要连接
3. **防止代码注入**: 无 `'unsafe-eval'` 配置
4. **资源控制**: 所有资源类型都有明确限制

### ⚠️ 需要注意

1. **内联样式**: `'unsafe-inline'` 在 style-src 中存在一定风险
   - **原因**: Tailwind CSS 和某些 UI 框架需要内联样式
   - **缓解**: 样式内容来源可控，不接受用户输入

### 🔐 安全强化建议

1. **考虑使用 nonce**: 为内联样式添加 nonce 以替代 `'unsafe-inline'`
2. **监控 CSP 违规**: 添加 `report-uri` 或 `report-to` 指令
3. **定期审查白名单**: 确保 connect-src 中的域名仍然必要

## 与 Electron 安全模型的集成

```typescript
// electron/main.ts
new BrowserWindow({
  webPreferences: {
    nodeIntegration: false, // ✅ 配合 CSP 阻止 Node.js 访问
    contextIsolation: true, // ✅ 隔离上下文，CSP 作为额外防护层
    sandbox: true, // ✅ 沙箱模式 + CSP 双重防护
    preload: path.join(__dirname, 'preload.js'),
  },
});
```

## 测试验证

E2E 测试确保 CSP 配置正确应用：

```typescript
// tests/e2e/smoke.electron.spec.ts
test('CSP configuration is properly applied', async () => {
  const cspMetaTag = await page.locator(
    'meta[http-equiv="Content-Security-Policy"]'
  );
  const cspContent = await cspMetaTag.getAttribute('content');
  expect(cspContent).toContain("default-src 'self'");
  expect(cspContent).toContain("script-src 'self'");
});
```

## 结论

当前的 `default-src 'self'` 配置在 Electron 应用场景下是**安全且实用**的选择：

1. **安全性**: 有效防止外部资源注入和XSS攻击
2. **实用性**: 支持本地资源加载，适合 Electron 架构
3. **合规性**: 符合 Electron 安全最佳实践要求
4. **可维护性**: 配置清晰，易于理解和维护

这种配置在提供足够安全保护的同时，保持了良好的开发和用户体验。
