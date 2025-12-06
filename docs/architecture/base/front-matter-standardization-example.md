# Base 文档 Front-Matter 标准化示例

## 问题现状

当前 01章和02章的 front-matter 只包含占位符变量，缺少标准字段：

```yaml
# 当前格式（不完整）
---
APP_NAME: unknown-app
PRODUCT_NAME: Unknown Product
PRODUCT_SLUG: unknown-product
# ... 其他占位符
---
```

## 建议的标准化格式

### 01章标准化后的 front-matter

```yaml
---
title: 01 约束与目标 — Base-Clean (90-95)
status: base-SSoT
adr_refs: [ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005]
placeholders: unknown-app, Unknown Product, unknown-product, gamedev, dev-team, dev-project, dev, 0.0.0, production, 99.5
---
```

### 02章标准化后的 front-matter

```yaml
---
title: 02 安全基线（Electron）— Base-Clean (95)
status: base-SSoT
adr_refs: [ADR-0002, ADR-0005]
placeholders: unknown-app, Unknown Product, unknown-product, gamedev, dev-team, dev-project, dev, 0.0.0, production
---
```

## 标准化后的好处

### 1. 与其他 Base 文档一致

- ✅ 统一的 `title` 字段格式
- ✅ 明确的 `status: base-SSoT` 标识
- ✅ 清晰的 `adr_refs` 追踪关系

### 2. 明确占位符声明

- ✅ `placeholders` 字段明确列出所有占位符
- ✅ 便于自动化工具验证和替换
- ✅ 提供完整的依赖关系映射

### 3. 配置分层实现示例

#### 构建时替换示例（npm run config:substitute）

**替换前（Base 文档）**:

```markdown
# 系统定位

- **产品类型**: 深度生态模拟游戏 - 玩家作为 gamedev 管理员
- **技术栈核心**: Unknown Product 基于 Electron + React 19
- **版本**: 0.0.0
```

**替换后（项目实现）**:

```markdown
# 系统定位

- **产品类型**: 深度生态模拟游戏 - 玩家作为 gamedev 管理员
- **技术栈核心**: ViteGame - 深度生态模拟游戏 基于 Electron + React 19
- **版本**: 0.1.0
```

#### 配置源映射示例

| 占位符            | 配置层     | 实际值                        | 来源                     |
| ----------------- | ---------- | ----------------------------- | ------------------------ |
| `unknown-app`     | Package    | `gamedev-vitegame`            | package.json name        |
| `Unknown Product` | Package    | `ViteGame - 深度生态模拟游戏` | package.json productName |
| `0.0.0`           | Package    | `0.1.0`                       | package.json version     |
| `gamedev`         | Domain     | `gamedev`                     | 硬编码域配置             |
| `dev-team`        | CI Secrets | `my-company`                  | 环境变量/CI密钥          |
| `${NODE_ENV}`     | Runtime    | `production`                  | 运行时环境变量           |

## 实施步骤

### 步骤1: 标准化 Front-Matter

```bash
# 1. 备份当前文档
cp docs/architecture/base/01-introduction-and-goals-v2.md docs/architecture/base/01-introduction-and-goals-v2.md.backup
cp docs/architecture/base/02-security-baseline-electron-v2.md docs/architecture/base/02-security-baseline-electron-v2.md.backup

# 2. 手动更新 front-matter 为标准格式
# （使用上面提供的标准化格式）
```

### 步骤2: 验证标准化结果

```bash
# 验证 Base 文档清洁性
npm run guard:base

# 验证配置完整性
npm run config:layers:validate

# 验证占位符处理
npm run config:substitute:validate
```

### 步骤3: 测试配置替换

```bash
# 开发环境测试（仅验证，不替换）
NODE_ENV=development npm run config:substitute:validate

# 生产环境测试（实际替换）
NODE_ENV=production SENTRY_ORG=test-org npm run config:substitute:docs

# 检查替换结果
grep -n "\${" docs/architecture/base/01-*.md docs/architecture/base/02-*.md
```

## 配置验证清单

### ✅ Front-Matter 必需字段检查

- [x] `title` - 清晰的文档标题
- [x] `status: base-SSoT` - 标识为 Base 文档
- [x] `adr_refs` - 引用相关的 ADR
- [x] `placeholders` - 声明所有使用的占位符

### ✅ 占位符一致性检查

- [x] `placeholders` 字段中声明的占位符与正文中使用的一致
- [x] 所有 `${VAR}` 格式的占位符都有对应的配置源
- [x] 敏感占位符（如 SENTRY\_\*）标识为 CI Secrets

### ✅ 配置分层完整性检查

- [x] Package Layer: `APP_NAME`, `PRODUCT_NAME`, `VERSION`
- [x] CI Secrets Layer: `SENTRY_ORG`, `SENTRY_PROJECT`
- [x] Runtime Layer: `NODE_ENV`, `RELEASE_PREFIX`
- [x] Domain Layer: `DOMAIN_PREFIX`, `CRASH_FREE_SESSIONS`

## 预期效果

### 开发体验改善

- 🚀 **统一的文档结构** - 所有 Base 文档遵循相同标准
- 🔧 **自动化配置管理** - 通过工具链处理占位符替换
- 📊 **完整的追踪矩阵** - ADR 引用和占位符依赖清晰可见

### 部署流程优化

- ⚡ **环境适配自动化** - 不同环境自动使用对应配置
- 🔒 **安全配置分离** - 敏感信息通过 CI 密钥管理
- ✅ **配置验证门禁** - 自动检查配置完整性和合规性

### 维护成本降低

- 📚 **Base 文档保持通用** - 占位符机制确保模板可复用
- 🔄 **项目配置独立管理** - 配置变更不影响 Base 文档结构
- 🛡️ **分层安全策略** - 不同类型配置采用适当的安全级别

这种混合配置管理策略既保持了 Base 文档的可复用性，又实现了项目实施时的配置安全性和灵活性。
