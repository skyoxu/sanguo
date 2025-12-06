---
title: 12 glossary v2
status: base-SSoT
adr_refs: [ADR-0001, ADR-0002, ADR-0003, ADR-0004, ADR-0005]
placeholders: unknown-app, Unknown Product, unknown-product, gamedev, dev-team, dev-project, dev, 0.0.0, production, ${I18N_KEY_PREFIX}
derived_from: 12-glossary-v2.md
last_generated: 2025-08-21
c4_context: glossary-system-context
c4_container: glossary-internal-architecture
---

> 在 optimized 基础上，补齐自动化校验/去重/一致性检查，形成工程闭环。

## C4 架构图表

```mermaid
C4Context
  Person(dev, "开发者", "查询术语定义") | System(glossary, "词汇表系统", "SSoT术语管理") | System(i18n, "国际化系统", "多语言支持") | System(validation, "验证系统", "一致性检查")
  Rel(dev, glossary, "查询术语") | Rel(glossary, i18n, "提供翻译映射") | Rel(glossary, validation, "术语一致性检查")
```

```mermaid
C4Container
  Container(api, "术语API", "TypeScript", "查询接口") | Container(store, "存储层", "JSON+Schema", "术语数据") | Container(validator, "验证器", "TypeScript", "去重+i18n校验") | Container(i18nAdapter, "i18n适配器", "TypeScript", "翻译同步")
  Rel(api, store, "读取术语") | Rel(validator, store, "验证完整性") | Rel(i18nAdapter, store, "同步翻译")
```

## 结构化 SSOT + 高级TypeScript

```ts
type TermType = 'domain' | 'tech' | 'abbr';
type I18nKey<T extends string> = `${T}.${string}`;
type ValidatedTerm<T> = T extends GlossaryTerm ? T : never;

interface GlossaryTerm {
  term: string;
  definition: string;
  type: TermType;
  zhCN: string;
  enUS: string;
  source: string;
  owner: string;
  aliases?: string[];
  i18nKey: I18nKey<'glossary'>;
}

export const GlossaryTerms: Record<string, GlossaryTerm> = {
  contentSecurityPolicy: {
    term: 'CSP',
    definition: 'Content Security Policy',
    type: 'abbr',
    zhCN: '内容安全策略',
    enUS: 'Content Security Policy',
    source: 'ADR-0002',
    owner: 'Security',
    aliases: ['content-security-policy', 'csp'],
    i18nKey: 'glossary.security.csp',
  },
  crashFreeSessions: {
    term: 'Crash‑Free Sessions',
    definition: 'Sentry release health metric',
    type: 'domain',
    zhCN: '无崩溃会话率',
    enUS: 'Crash‑Free Sessions',
    source: 'ADR-0003',
    owner: 'QA',
    aliases: ['crash-free', 'healthy-sessions'],
    i18nKey: 'glossary.metrics.crash_free',
  },
};

function detectDuplicates<T extends GlossaryTerm>(
  terms: T[]
): { duplicates: string[]; aliases: string[] } {
  const termSet = new Set();
  const aliasSet = new Set();
  return terms.reduce(
    (acc, term) => {
      if (termSet.has(term.term)) acc.duplicates.push(term.term);
      term.aliases?.forEach(alias =>
        aliasSet.has(alias) ? acc.aliases.push(alias) : aliasSet.add(alias)
      );
      termSet.add(term.term);
      return acc;
    },
    { duplicates: [], aliases: [] }
  );
}

function validateI18nConsistency<T extends Record<string, GlossaryTerm>>(
  glossary: T,
  i18nKeys: string[]
): { missing: string[]; invalid: string[] } {
  const keys = Object.values(glossary).map(term => term.i18nKey);
  return {
    missing: keys.filter(key => !i18nKeys.includes(key)),
    invalid: keys.filter(key => !key.startsWith('glossary.')),
  };
}
```

## 工程化校验脚本

```js
// scripts/validate-glossary.mjs
import {
  GlossaryTerms,
  detectDuplicates,
  validateI18nConsistency,
} from '../src/shared/contracts/glossary.js';
import { readFileSync } from 'fs';

const i18nKeys = JSON.parse(readFileSync('src/i18n/keys.json', 'utf8'));
const terms = Object.values(GlossaryTerms);
const duplicates = detectDuplicates(terms);
const i18nIssues = validateI18nConsistency(GlossaryTerms, i18nKeys);

if (duplicates.duplicates.length || duplicates.aliases.length) {
  console.error('❌ 发现重复术语:', duplicates);
  process.exit(1);
}
if (i18nIssues.missing.length || i18nIssues.invalid.length) {
  console.error('❌ i18n不一致:', i18nIssues);
  process.exit(1);
}
console.log(`✅ 词汇表校验通过 (${terms.length}个术语)`);
```
