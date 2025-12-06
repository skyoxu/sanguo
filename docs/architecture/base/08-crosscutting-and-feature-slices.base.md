---
title: 08 crosscutting and feature slices.base
status: base-SSoT
adr_refs: [ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005]
placeholders: unknown-app, Unknown Product, unknown-product, gamedev, production, dev, dev-team, dev-project
derived_from: arc42 §8 (crosscutting concepts), C4 (Context/Container) minimal
last_generated: 2025-08-22
---

> 目的：把“跨切面规则（Crosscutting Concepts）+ 功能纵切（Feature/Vertical Slice）”的**最小可执行 SSoT**固化为模板与门禁，所有具体功能切片落到 overlays/08/ 下，不污染 Base。

## 08.1 范围与原则（SSoT）

- **跨切面规则**：对多个构件生效的原则/约束/模式（命名、风格、安全、可观测、质量门禁等）。
- **功能纵切（Vertical Slice）**：以“单个特性/用例”为单位，贯穿 UI→服务→端口→存储的一条链，按 **${PRD_ID}** 独立交付。
- **Base‑Clean** 要求：
  1. 本章只提供**模板/规则/门禁**；
  2. 具体特性文档与契约进入 `overlays/08/<${PRD_ID}>-<feature>/`；
  3. 每个切片必须提供 **C4 Context + Container** 两张图、事件/端口契约与就地验收。

## 08.2 CloudEvents 1.0跨切面规则（SSoT）

### 事件合约标准（ADR-0004）

所有功能纵切必须遵循CloudEvents 1.0规范：

```typescript
// 统一事件工厂 - src/shared/contracts/cloudevents-core.ts
export interface CloudEvent<T = unknown> extends CeBase {
  // CloudEvents 1.0必需字段
  id: string; // 事件唯一标识符（自动生成UUID）
  source: string; // 事件源URI（如app://vitegame/guild-manager）
  type: string; // 事件类型（reverse DNS格式）
  specversion: '1.0'; // CloudEvents规范版本
  time: string; // 事件时间戳（ISO 8601格式）

  // 可选字段
  data?: T; // 事件负载数据
  datacontenttype?: string; // 数据内容类型
  dataschema?: string; // 数据模式URI
  subject?: string; // 事件主题
}

// 标准工厂函数（强制使用）
export function mkEvent<T = unknown>(
  e: Omit<CeBase, 'id' | 'time' | 'specversion'> & {
    data?: T;
    datacontenttype?: string;
    dataschema?: string;
    subject?: string;
  }
): CloudEvent<T>;
```

### 合规性门禁（强制执行）

```json
{
  "scripts": {
    "cloudevents:check": "node scripts/verify_cloudevents_compliance.mjs"
  }
}
```

**验收标准**：

- ✅ 所有事件使用统一`mkEvent`工厂函数
- ✅ 禁止使用废弃的`createCloudEvent`
- ✅ 事件类型采用reverse DNS格式（如`guild.member.joined`）
- ✅ 运行时验证使用`assertCe`函数
- ✅ `npm run cloudevents:check`全绿通过

## 08.3 目录结构（Base vs Overlays）

```
docs/
  08-feature-slices/
    README.md
    templates/
      feature-slice.template.md
      c4-context.template.mmd
      c4-container.template.mmd
src/
  shared/
    contracts/
      features/
        _template/
          events.ts
          ports.ts
tests/
  unit/features/_template.contract.spec.ts
  e2e/features/_template.e2e.spec.ts
scripts/gates/feature-slice-gate.mjs
overlays/
  08/
    <${PRD_ID}>-<feature>/
      08-<feature>.md
      c4/context.mmd
      c4/container.mmd
      contracts/*.ts
      tests/unit/*.spec.ts
      tests/e2e/*.spec.ts
```

## 08.3 C4 图表模板（Base 要求：模板 + 叠加层必须提供图）

> 注：使用 Mermaid **flowchart** 来表达 C4 的 **Context/Container** 视角（不绑定具体业务）。

### 08.3.1 System Context（模板 · 必填）

```mermaid
%% C4: System Context — Feature Slice (template)
flowchart LR
  actor([User/Actor])
  app[[unknown-app]]
  slice[[{feature} Slice]]
  telemetry[(Release Health/Telemetry)]
  external[(External Service · optional)]
  actor -->|interacts with| app
  app -->|invokes| slice
  slice -->|observability| telemetry
  slice --> external
```

### 08.3.2 Container（模板 · 必填）

```mermaid
%% C4: Container — Feature Slice (template)
flowchart TB
  subgraph App[unknown-app]
    renderer[Renderer (React 18)]
    preload[Preload Bridge (controlled IPC)]
    main[Main Process]
    service[Feature Service]
    port[(Storage/External Port)]
  end
  renderer --> preload
  preload --> main
  renderer --> service
  service --> port
```

## 08.4 事件与端口命名（模板）

- 事件命名：`gamedev.${entity}.${action}`（小写蛇形），示例：`gameplay.system.error_occurred`。
- 端口命名：`<Entity>Repository` / `<Domain>Service`。

```ts
// src/shared/contracts/features/_template/events.ts
export type EventName = `${string}.${string}.${string}`;
export interface CE<T> {
  // CloudEvents 1.0 外层（可选但推荐）
  specversion: '1.0';
  id: string;
  source: string;
  type: string;
  time: string;
  datacontenttype?: string;
  data: T;
}
export type FeatureCreated = CE<{ id: string; by: string }>;
export const isEventName = (s: string) => /^[a-z_]+\.[a-z_]+\.[a-z_]+$/.test(s);
```

```ts
// src/shared/contracts/features/_template/ports.ts
export interface EntityRepository<T> {
  getById(id: string): Promise<T | null>;
  upsert(entity: T): Promise<void>;
}
export interface DomainService<I, O> {
  execute(request: I): Promise<O>;
}
```

## 08.5 质量门禁（最小实现 · CI 可阻断）

> 目标：每个 overlays/08/<${PRD_ID}>-<feature> 必须具备：front‑matter/adr_refs、C4 两图、契约与测试占位。

```js
// scripts/gates/feature-slice-gate.mjs
import fs from 'node:fs';
import path from 'node:path';
const dir = process.argv[2]; // overlays/08/<${PRD_ID}>-<feature>
function fail(msg) {
  console.error('❌ feature-slice gate:', msg);
  process.exit(1);
}
const must = ['08-<feature>.md', 'c4/context.mmd', 'c4/container.mmd'];
for (const f of must) {
  if (!fs.existsSync(path.join(dir, f))) fail(`missing ${f}`);
}
const md = fs.readFileSync(path.join(dir, '08-<feature>.md'), 'utf8');
if (!/^adr_refs:\s*\[.*\]/m.test(md)) fail('missing front-matter adr_refs');
if (!/\$\{DOMAIN_PREFIX\}/.test(md)) fail('missing placeholders');
console.log('✅ feature-slice gate passed');
```

## 08.6 验收清单（Base）

- [ ] 叠加层每个切片均包含 **Context + Container** 两图；
- [ ] 事件与端口命名符合模板；
- [ ] `feature-slice-gate.mjs` 可在 CI 中执行并阻断；
- [ ] 关键事件以 **CloudEvents 1.0 外层**包装或可映射；
- [ ] 单元/契约/E2E 测试至少有占位用例。

## 08.7 就地测试（占位）

```ts
// tests/unit/features/_template.contract.spec.ts
import { describe, it, expect } from 'vitest';
import { isEventName } from '../../../src/shared/contracts/features/_template/events';
describe('feature slice contracts', () => {
  it('event naming rule', () => {
    expect(isEventName('demo.entity.action')).toBe(true);
    expect(isEventName('bad.format')).toBe(false);
  });
});
```

## 08.8 写作与评审指引

- Base 只保留模板/门禁/规则；具体内容进 overlays/08/，**一切业务术语不得进入 Base**。
- PR 审查至少检查：占位符、ADR 链接、C4 两图、契约/测试/门禁是否齐备。
