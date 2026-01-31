# 内容数据盘点（覆盖与缺口）

## 盘点范围
- Data/** 旧路径内容（兼容）
- Data/packs/** 内容包路径（推荐）

## 目录现状
- Data/*.json（角色、事件、卡牌、建筑、宝物、州郡等）
- Data/maps/_index.json + Data/maps/*.json
- Data/i18n/zh_cn.json + Data/i18n/en_us.json
- Data/packs/_index.json
- Data/packs/<packId>/pack.json
- Data/packs/<packId>/characters.json
- Data/packs/<packId>/random_events.json
- Data/packs/<packId>/action_cards.json
- Data/packs/<packId>/buildings.json
- Data/packs/<packId>/relics.json
- Data/packs/<packId>/regions.json
- Data/packs/<packId>/facilities.json
- Data/packs/<packId>/maps/_index.json + Data/packs/<packId>/maps/<mapId>.json
- Data/packs/<packId>/i18n/zh_cn.json + Data/packs/<packId>/i18n/en_us.json

## 规则与脚本覆盖
- scripts/python/check_data_versions_bumped.py：Data/** 版本 bump 硬门禁
- scripts/python/validate_data_catalog.py：Data/** 字段/类型/i18n/effectKind 校验
- scripts/python/validate_content_packs.py --strict：pack 索引、pack.json、路径存在、i18n、字段级门禁
- scripts/python/data_catalog_rules*.py：字段规则、ID/引用一致性、数值范围与权重校验

## CI 接入与证据
- scripts/python/ci_pipeline.py：包含 content pack 硬门禁
- scripts/python/quality_gates.py：调用 ci_pipeline，作为硬门禁入口
- 证据路径：logs/ci/<date>/content-pack-validate.log 与 content-pack-validate.json
- 相关日志：logs/ci/<date>/data-catalog-validate.log、data-version-gate.log

## 缺口与注意事项
- 旧路径与 pack 路径并存，新增内容优先走 pack，避免双源漂移
- 修改 pack 目录结构时必须同步 pack.json 与 i18n
- 新增字段或枚举值时先更新 data_catalog_rules*，再补内容
