# 数据导出与导入流程（T2 最小路径）

本流程用于在不改代码的情况下新增或调整内容，并保证能通过硬门禁校验。
适用范围：Data/** 的最小可玩闭环内容。

## 目标

- 内容新增不依赖目录扫描，完全显式文件列表。
- 变更可追溯，版本门禁与 i18n 覆盖门禁必过。
- 导入失败可定位到具体文件与字段。

## 目录与职责

- Data/*.json：内容单表与索引。
- Data/maps/_index.json：地图入口索引。
- Data/i18n/zh_cn.json 与 Data/i18n/en_us.json：双语字典。
- logs/ci/<YYYY-MM-DD>/：门禁证据与失败定位。

## 最小导出与导入流程（不改代码）

### 1) 选择内容类型并准备条目

支持类型：地图、角色、事件、卡牌、建筑、宝物、州郡、设施。

### 2) 更新内容文件

- 仅编辑 Data/*.json 或 Data/maps/*。
- 每次改动必须递增文件的 ersion。
- 新增条目必须具备 
ameKey/descriptionKey。

### 3) 补齐 i18n

- 在 Data/i18n/zh_cn.json 与 Data/i18n/en_us.json 同时新增键。
- 若只补中文或英文，将触发硬门禁失败。

### 4) 地图相关更新

- 修改 Data/maps/map*.json 后，必须同步 bump：
  - Data/maps/map*.json 的 ersion
  - Data/maps/_index.json 的 ersion 与对应 contentVersion

### 5) 门禁校验（本地）

- py -3 scripts/python/validate_data_catalog.py --strict
- py -3 scripts/python/check_data_versions_bumped.py --base origin/main --head HEAD

### 6) 失败定位

- logs/ci/<date>/data-catalog-validate.log
- logs/ci/<date>/data-version-gate.log

## 导入约束（硬门禁）

- 不允许目录扫描，必须通过 _index.json 或显式路径。
- 路径仅允许 
es://Data/ 与 
es://Assets/。
- ID 与引用一致性需通过门禁（见 docs/workflows/content-id-reference-rules.md）。
- 字段与范围约束需通过门禁（见 docs/workflows/content-schema-fields.md）。

## 最小模板示例

### 新增卡牌（action_cards.json）

- 新增条目到 Data/action_cards.json
- 同步 bump ersion
- 增加 card.<id>.name 与 card.<id>.desc 的中英文 key

### 新增事件（random_events.json）

- 新增 event 与 pool 引用
- 同步 bump ersion
- 增加 event.<id>.name 与 event.<id>.desc 的中英文 key

## 禁止事项

- 禁止在 Data/** 使用 meta 字段。
- 禁止在本地绕过门禁后再提交。
- 禁止只改内容不改 ersion。

## 口径引用

- ADR-0004：事件命名与契约口径。
- ADR-0005：质量门禁与 CI 约束。
- ADR-0019：资源与路径安全基线。
