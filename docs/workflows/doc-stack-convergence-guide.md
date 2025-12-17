# 文档口径全量收敛操作手册（Base + Migration）

## 1. 目的与范围

本手册用于解决仓库文档中残留旧技术栈语境（例如旧桌面壳、旧前端栈、旧测试/构建工具名）导致的人/LLM 误导问题，并给出在本仓库进行“全量收敛”的可执行步骤与验证方式。

适用范围：
- `docs/architecture/base/**`（Base-Clean 口径）
- `docs/architecture/overlays/**/08/**`（功能纵切）
- `docs/migration/**`（迁移历史资料库）
- `docs/adr/**`（ADR 与 Addenda）
- `README.md`、`AGENTS.md`、`CLAUDE.md`（入口与规则文档）

本手册不讨论业务 PRD 具体内容；只讨论文档口径收敛与可执行验证。

## 2. 关键原则（避免误导）

- Base 文档是跨切面与系统骨干的 SSoT，禁止出现任何具体 PRD 标识与具体 08 纵切内容。
- 迁移文档是历史对照资料库，允许保留过程信息，但不得让旧技术栈名词“看起来像当前口径”。如果需要提及旧栈，优先使用“旧桌面壳/旧前端栈/旧项目”等中性描述，避免使用具体产品名。
- 所有扫描与取证输出统一写入 `logs/**`，便于排障与归档；禁止把 `logs/**` 提交到仓库。

## 3. Windows 环境前置（必须）

- Windows 环境下请使用 `py -3` 运行 Python。不要依赖 `python`（可能指向 Microsoft Store alias）。
- 运行 PowerShell 脚本请使用：
  - `powershell -NoProfile -ExecutionPolicy Bypass -File <script.ps1>`
- 文档读写一律使用 UTF-8（脚本已显式使用 `encoding="utf-8"`）。

## 4. 本仓库可执行脚本（SSoT）

### 4.1 Base-Clean 校验（硬门禁）

脚本：`scripts/ci/verify_base_clean.ps1`

校验要点（脚本规则）：
- Base（`docs/architecture/base/**`）不得出现 `PRD-\w+` 命中。
  - 注意：即便是写作示例里的 `PRD-ID` 也会命中（因为它符合 `PRD-\w+`）。
  - Base 中请改用 `PRD_ID`、`${PRD_ID}`、`<PRD_ID>` 等不含连字符的占位符写法。
- Overlay 08（`docs/architecture/overlays/<PRD_ID>/08/*`）每个文件必须至少出现一次 `CH01` 或 `CH03`（或 `Chapter 01/03`）引用。
- Overlay 08 不能出现阈值/门禁关键字的“复制痕迹”（启发式命中）：`p95`、`99.5%`、`coverage >=`、`crash-free` 等。
  - 处理方式：改为引用 ADR/Base 章节，不在 08 章正文复制具体阈值。

运行命令：
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\ci\\verify_base_clean.ps1`

产出位置：
- `logs/ci/<YYYYMMDD-HHMMSS>/base-clean/summary.json`

### 4.2 UTF-8 与疑似乱码扫描（取证 + 门禁前置）

脚本：`scripts/python/check_encoding.py`

作用：
- 严格 UTF-8 解码检查（`errors="strict"`）。
- 额外做“疑似语义乱码”（mojibake）启发式检测。

运行命令：
- `py -3 scripts/python/check_encoding.py --root docs`

产出位置：
- `logs/ci/<YYYY-MM-DD>/encoding/**`

### 4.3 旧技术栈术语扫描（取证）

脚本：`scripts/python/scan_doc_stack_terms.py`

默认扫描关键词（可按需扩展脚本）：
- 旧项目名、旧桌面壳、旧前端框架、旧构建/测试/E2E 工具等（大小写不敏感）

运行命令：
- `py -3 scripts/python/scan_doc_stack_terms.py --root docs`
- 严格模式（用于 CI 或本地门禁）：`py -3 scripts/python/scan_doc_stack_terms.py --root docs --fail-on-hits`

产出位置：
- `logs/ci/<YYYY-MM-DD>/doc-stack-scan/summary.json`
- `logs/ci/<YYYY-MM-DD>/doc-stack-scan/scan.json`

### 4.4 旧术语中性化替换（全量收敛工具）

脚本：`scripts/python/sanitize_legacy_stack_terms.py`

作用：
- 对 `docs/**` 中的旧栈名词进行中性化替换，避免旧技术栈词汇作为“当前口径”出现在文档里。
- 只处理文本类文件（`.md/.txt/.yml/.yaml/.json/...`），使用 UTF-8 严格读写。

运行命令（写回）：
- `py -3 scripts/python/sanitize_legacy_stack_terms.py --root docs --write`

产出位置：
- `logs/ci/<YYYY-MM-DD>/legacy-term-sanitize/summary.json`
- `logs/ci/<YYYY-MM-DD>/legacy-term-sanitize/changes.json`

### 4.5 文档去 Emoji/符号清理（可选但推荐）

脚本：`scripts/python/sanitize_docs_no_emoji.py`

作用：
- 按映射替换/删除文档中的 emoji/dingbat 符号，满足仓库“禁止 emoji”规则。

运行命令（写回）：
- `py -3 scripts/python/sanitize_docs_no_emoji.py --root docs --extra README.md AGENTS.md CLAUDE.md --write`

产出位置：
- `logs/ci/<YYYY-MM-DD>/emoji-sanitize.json`

## 5. 全量收敛推荐步骤（按顺序）

### Step 0：在新分支上执行

- `git switch -c docs/converge-doc-stack`

### Step 1：先做编码与语义乱码扫描（取证）

- `py -3 scripts/python/check_encoding.py --root docs`

若 `bad>0`：
- 优先用编辑器按 UTF-8 重新保存（不要用控制台 copy/paste 修复）。
- 再复跑脚本确认 `bad=0`。

### Step 2：扫描旧栈术语（取证）

- `py -3 scripts/python/scan_doc_stack_terms.py --root docs`

查看 `logs/ci/<YYYY-MM-DD>/doc-stack-scan/summary.json` 里的 Top files，优先处理入口文档与 Base。

### Step 3：批量中性化替换（全量收敛）

- `py -3 scripts/python/sanitize_legacy_stack_terms.py --root docs --write`

替换后必须做两类复核：
- 语义复核：确认“旧栈”段落仍然表达“历史对照”，且不会被理解为当前运行时依赖。
- 路径复核：如果文档里包含旧文件名/路径提示，需要同步更新为真实存在的文件路径。

### Step 4：修复 Base-Clean 违规（硬规则）

运行并查看报表：
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\ci\\verify_base_clean.ps1`

常见违规与修复方式：
- Base 命中 `PRD-\w+`
  - 把 Base 文档中的 `PRD-ID`、`PRD-xxx` 等写法替换为 `PRD_ID`、`${PRD_ID}` 等不含 `PRD-` 前缀的占位符。
- Overlay 08 缺少 `CH01/CH03`
  - 推荐在 YAML Front-Matter 加 `Arch-Refs: [CH01, CH03]`，并在正文中增加“见 CH01/CH03”引用句。
- Overlay 08 复制阈值/门禁关键字
  - 移除 `p95/coverage>=/crash-free/99.5%` 等词汇与数字阈值；改为“引用 ADR-0003/ADR-0005/ADR-0015（或对应 Base 章节）”的表述。

### Step 5：可选的去 Emoji 清理

如果仓库规则要求“完全无 emoji”：
- `py -3 scripts/python/sanitize_docs_no_emoji.py --root docs --extra README.md AGENTS.md CLAUDE.md --write`

### Step 6：复跑扫描，形成最终取证

- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\ci\\verify_base_clean.ps1`
- `py -3 scripts/python/check_encoding.py --root docs`
- `py -3 scripts/python/scan_doc_stack_terms.py --root docs`

通过标准：
- Base-Clean `passed=true`
- Encoding `bad=0`
- Doc stack scan `hits=0`

### Step 7：提交（不要提交 logs）

- `git status -sb` 确认只有规则文档/脚本/文档变更
- `git add docs AGENTS.md CLAUDE.md scripts`
- `git commit -m "docs: converge documentation to Godot stack"`
- `git push -u origin <your-branch>`

## 6. 验证方式（最小清单）

本仓库建议把以下三条作为文档收敛的最小验证集（本地与 CI 均可运行）：
- `scripts/ci/verify_base_clean.ps1`（硬规则）
- `scripts/python/check_encoding.py --root docs`（编码与语义乱码取证）
- `scripts/python/scan_doc_stack_terms.py --root docs --fail-on-hits`（旧栈词汇回流防线，可先软门禁再硬门禁）

## 7. 常见坑与排查

- Base 里写了 `PRD-ID` 仍会触发 `PRD-\w+`：这不是脚本误报，是规则本身的副作用。Base 请用 `PRD_ID` 这类占位符。
- 终端显示“乱码”时不要用复制粘贴修复文档：优先打开文件本身或查看脚本落盘的 JSON 报告（`logs/ci/**`）。
- Overlay 08 出现 `p95` 等指标名也会触发重复阈值启发式：指标命名建议避开这些关键词，或改为更中性的 `latency`/`frame_time` 等，并把阈值放回 ADR/Base。

## 8. 可选增强（防止回流）

建议把 `scan_doc_stack_terms.py` 以“软门禁”先接入 CI（只写 Step Summary，不阻断），稳定后再切换为硬门禁（`--fail-on-hits`），从流程上避免旧语境回流导致的长期误导。

