# 内容作者指南（T2 最小闭环）

本指南用于统一内容制作、校验与导入流程，确保新增内容可通过硬门禁并可追溯。

## 你需要知道的四份规范

1. **内容包 Manifest**：`docs/workflows/content-pack-manifest.md`
2. **字段与范围清单**：`docs/workflows/content-schema-fields.md`
3. **ID 与引用一致性**：`docs/workflows/content-id-reference-rules.md`
4. **导入与导出流程**：`docs/workflows/content-import-export-flow.md`

## 最小可用路径（不改代码）

1. 修改内容文件（`Data/*.json` 或 `Data/maps/*`）
2. 同步 bump `version`
3. 补齐 `Data/i18n/zh_cn.json` 与 `Data/i18n/en_us.json`
4. 运行门禁并查看日志

## 必跑门禁命令（Windows）

```
py -3 scripts/python/validate_data_catalog.py --strict
py -3 scripts/python/check_data_versions_bumped.py --base origin/main --head HEAD
```

## 常见失败与定位

- **字段缺失 / 范围越界**：`logs/ci/<date>/data-catalog-validate.log`
- **版本未 bump**：`logs/ci/<date>/data-version-gate.log`

## 命名与 i18n 规则（最短版）

- id：`^[a-z0-9_]{1,32}$`
- nameKey/descriptionKey：必须同时存在于中英文 i18n

## 口径引用

- ADR-0004：事件命名与契约口径。
- ADR-0005：质量门禁与 CI 约束。
- ADR-0019：资源与路径安全基线。
