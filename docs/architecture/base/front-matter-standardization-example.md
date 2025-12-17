# Base 文档 Front-Matter 标准化示例（Godot 模板）

本页给出 Base 文档建议使用的 front-matter 字段形态，用于提升可追溯性与自动化校验能力。

## 最小字段建议

- `title`：简短标题（可用英文）
- `status`：Base 文档固定为 `base-SSoT`
- `adr_refs`：与该章节强相关的 ADR 列表
- `placeholders`：正文中使用到的占位符列表（Base 禁止出现真实 PRD_ID）

## 示例：01 章

```yaml
---
title: 01 introduction and goals v2
status: base-SSoT
adr_refs: [ADR-0018, ADR-0019, ADR-0003, ADR-0004, ADR-0020, ADR-0015, ADR-0011, ADR-0025]
placeholders: unknown-app, Unknown Product, unknown-product, ${DOMAIN_PREFIX}, ${PRD_ID}, dev-team, dev-project, dev, production
---
```

## 示例：02 章（文件名保留历史后缀）

```yaml
---
title: 02 security baseline v2 (godot)
status: base-SSoT
adr_refs: [ADR-0019, ADR-0011, ADR-0003, ADR-0020]
placeholders: unknown-app, Unknown Product, ${DOMAIN_PREFIX}, dev-team, production
---
```

## 自动化校验（Windows）

- Base 清洁度：`pwsh -File scripts/ci/verify_base_clean.ps1`
- 编码/疑似乱码：`py -3 scripts/python/check_encoding.py --root docs/architecture/base`
