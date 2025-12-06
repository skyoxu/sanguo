# Godot+C# 妯℃澘蹇€熷紑濮嬶紙AI 鍗忎綔瑙嗚锛?
> 鐩爣璇昏€咃細BMAD 娓告垙涓撳浠ｇ悊銆乼ask-master-ai銆丼uperClaude/Claude Code銆丆odex CLI锛屼互鍙婇渶瑕佺悊瑙ｆ湰妯℃澘鈥滄妧鏈墠鎻?+ 鍛戒护鍏ュ彛鈥濈殑浜虹被寮€鍙戣€呫€?
鏈」鐩槸 **Windows-only 鐨?Godot 4.5.1 + C# 娓告垙妯℃澘**锛岀敤浜庢敮鎾?ARC42/C4 + ADR 鐨?AI 椹卞姩寮€鍙戝伐浣滄祦銆傝繖閲屽彧鎻忚堪 Godot 鍙樹綋鐩稿叧鐨勭害鏉熶笌鍏ュ彛锛屼笉鍐嶅睍寮€ Electron/vitegame 缁嗚妭銆?
---

## 1. 鎶€鏈墠鎻?SSoT锛堜緵 BMAD/PRD 浣跨敤锛?
- 骞冲彴涓庤繍琛岀幆澧?  - 浠呮敮鎸?Windows 妗岄潰鐜锛汣I 鐩爣涓?`windows-latest`銆?  - 寮曟搸锛欸odot 4.5.1 .NET锛坢ono锛夋帶鍒跺彴鐗堬紝鐜鍙橀噺/鍙傛暟缁熶竴鍛藉悕涓?`GODOT_BIN`銆?  - .NET锛?.x锛岀敤浜?`Game.Core` 涓?Godot C# 鑴氭湰缂栬瘧涓庡崟鍏冩祴璇曘€?
- 鏋舵瀯鍒嗗眰锛圙odot 鍙樹綋锛?  - `Game.Core`锛氱函 C# 鍩熸ā鍨嬩笌鏈嶅姟锛屼笉寮曠敤 Godot API锛屽彲閫氳繃 xUnit 蹇€熸祴璇曘€?  - `Game.Godot`锛氶€傞厤灞備笌鍦烘櫙鑴氭湰锛屼粎鍦ㄨ繖閲屼娇鐢?Godot API锛圢odes/Signals/Autoload锛夈€?  - `Tests.Godot`锛欸dUnit4 鍦烘櫙闆嗘垚娴嬭瘯椤圭洰锛坔eadless锛岀鐢ㄧ湡瀹?UI 杈撳叆浜嬩欢锛夈€?
- 鎸佷箙鍖栦笌閰嶇疆
  - Settings 鍗曚竴浜嬪疄鏉ユ簮锛圫SoT锛夛細`ConfigFile` 鈫?`user://settings.cfg`锛圓DR-0023锛夈€?  - 棰嗗煙鏁版嵁锛歋QLite锛岄€氳繃 `SqliteDataStore` 閫傞厤鍣ㄨ闂紝浠呭厑璁?`user://` 璺緞锛岀姝?`..` 绌胯秺锛屽け璐ュ啓瀹¤ JSONL锛圓DR-0006锛夈€?
- 浜嬩欢绯荤粺
  - Core 浜嬩欢锛歚DomainEvent` + `EventBus` + `EventBusAdapter`锛圕#锛夛紝鍦?Godot 涓互 `DomainEventEmitted` Signal 鏆撮湶銆?  - 鍛藉悕瑙勮寖锛?    - UI 鑿滃崟锛歚ui.menu.<action>`锛堝 `ui.menu.start`, `ui.menu.settings`, `ui.menu.quit`锛夈€?    - Screen 鐢熷懡鍛ㄦ湡锛歚screen.<name>.<action>`锛堝 `screen.start.loaded`, `screen.settings.saved`锛夈€?    - 棰嗗煙浜嬩欢锛堟帹鑽愶級锛歚core.<entity>.<action>`锛堝 `core.score.updated`, `core.health.updated`, `core.game.started`锛夈€?    - Demo 绀轰緥锛歚demo.*` 浠呯敤浜庢ā鏉挎紨绀猴紝涓嶅缓璁嚭鐜板湪鐪熷疄涓氬姟浜嬩欢涓€?  - 鍘嗗彶浜嬩欢鍚嶏細`game.started` / `score.changed` / `player.health.changed` 浠呬繚鐣欏湪閮ㄥ垎娴嬭瘯涓庡吋瀹硅矾寰勪腑锛屾柊 Story/浠诲姟蹇呴』浣跨敤 `core.*.*` / `ui.menu.*` / `screen.*.*`銆?
> 瀵?BMAD锛氱敓鎴?PRD 鏃讹紝鍑℃秹鍙婁簨浠?鎸佷箙鍖?瀹夊叏/娴嬭瘯鐨勬潯鐩紝搴斾紭鍏堥伒寰笂杩扮害鏉燂紝骞跺湪 CH05/CH06/CH07/Phase-9 鏂囨。涓煡鎵?Godot 鍙樹綋璇存槑锛屼笉瑕侀粯璁?Web/Electron 妯″紡銆?
---

## 2. 浠?PRD 鍒?tasks.json 鐨勭害鏉燂紙渚?task-master-ai 浣跨敤锛?
褰?task-master-ai 灏?PRD 杞崲涓?`tasks.json` 鏃讹紝寤鸿閬靛畧浠ヤ笅缁撴瀯涓庡洖閾捐鍒欙細

- 浠诲姟鍏冩暟鎹粨鏋勶紙寤鸿妯℃澘锛?
```jsonc
{
  "id": "PH8-SCORE-001",
  "title": "Add core score service and events",
  "layer": "core", // core | adapter | scene | test | doc
  "adr_refs": ["ADR-0004", "ADR-0006"],
  "chapter_refs": ["CH05", "CH06", "Phase-8-Scene-Design"],
  "overlay_refs": ["PRD-<PRODUCT>/08/..."],
  "depends_on": ["PH4-DOMAIN-BASE"],
  "description": "Implement score domain model and publish core.score.updated events."
}
```

- layer 寤鸿
  - `core`锛氬彧鏀?`Game.Core/**` 涓?`Game.Core.Tests/**`銆?  - `adapter`锛氬彧鏀?`Game.Godot/Adapters/**`锛堝惈 Db/Config/Security/EventBus 绛夛級銆?  - `scene`锛氭敼 `Game.Godot/Scenes/**` 涓?`Game.Godot/Scripts/**` 涓殑 UI/Glue/Navigation銆?  - `test`锛氭敼 `Game.Core.Tests/**` 鎴?`Tests.Godot/tests/**`銆?  - `doc`锛氭敼 `docs/adr/**`, `docs/architecture/base/**`, `docs/migration/**` 绛夈€?
- 鍥為摼瑕佹眰
  - 姣忎釜浠诲姟蹇呴』鑷冲皯寮曠敤 1 鏉?**宸叉帴鍙楃殑 ADR**锛堝 ADR-0004/0005/0006/0023锛夛紝纭繚鎶€鏈喅绛栨潵婧愬敮涓€銆?  - 鑻ヤ换鍔′慨鏀瑰畨鍏?瑙傚療鎬?璐ㄩ噺闂ㄧ鍙ｅ緞锛屽簲鍦ㄤ换鍔℃弿杩颁腑鎸囨槑闇€鏂板鎴?Supersede 鐨?ADR锛堝苟鐢变汉绫?AI 鍙﹁捣 ADR 鑽夋锛夈€?  - 鑻ヤ换鍔¤惤鍦?Phase-8 涔嬪悗锛圫cene/Glue/E2E 绛夛級锛屽簲寮曠敤鐩稿簲 Phase 鏂囨。涓?overlays 涓殑 08 绔犺妭銆?
> 瀵?task-master-ai锛氱敓鎴?`tasks.json` 鏃讹紝璇峰皢 Godot 鐗规湁浠诲姟绫诲瀷锛坰cene glue銆丟dUnit tests銆丆onfigFile/SQLite 閫傞厤锛夋樉寮忔爣璁颁负瀵瑰簲 layer锛屽苟淇濇寔 ADR/Phase 鍥為摼锛屼笉瑕佸垱閫犫€滄棤鏉ユ簮鐨勬妧鏈喅绛栤€濄€?
---

## 3. 甯哥敤鍛戒护鍏ュ彛锛堜緵 AI 宸ュ叿涓庝汉绫诲叡鐢級

鏈ā鏉夸紭鍏堥€氳繃 Python 鑴氭湰缁熶竴椹卞姩 CI/娴嬭瘯/Smoke銆傛帹鑽愪紭鍏堜娇鐢?`scripts/python/dev_cli.py` 鏆撮湶鐨勫瓙鍛戒护锛岃€屼笉鏄湪涓婂眰宸ュ叿閲嶅鎷兼帴闀垮懡浠よ銆?
### 3.1 dev_cli 瀛愬懡浠わ紙鎺ㄨ崘璋冪敤鏂瑰紡锛?
```bash
py -3 scripts/python/dev_cli.py run-ci-basic \
  --godot-bin "C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe"

py -3 scripts/python/dev_cli.py run-quality-gates \
  --godot-bin "C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe" \
  --gdunit-hard --smoke

py -3 scripts/python/dev_cli.py run-gdunit-hard \
  --godot-bin "C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe"

py -3 scripts/python/dev_cli.py run-gdunit-full \
  --godot-bin "C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe"

py -3 scripts/python/dev_cli.py run-smoke-strict \
  --godot-bin "C:\Godot\Godot_v4.5.1-stable_mono_win64_console.exe" \
  --timeout-sec 5
```

- `run-ci-basic`
  - 璋冪敤 `ci_pipeline.py all`锛屾墽琛岋細dotnet 娴嬭瘯 + 鑷锛圕ompositionRoot锛? 缂栫爜鎵弿銆?  - 鐢ㄤ簬鍩虹鍋ュ悍妫€鏌ワ紝涓嶅寘鍚?GdUnit 涓?Smoke銆?
- `run-quality-gates`
  - 璋冪敤 `quality_gates.py all`锛屽彲閫?`--gdunit-hard` 涓?`--smoke`锛?    - `--gdunit-hard`锛氳繍琛?Adapters/Config + Security GdUnit 灏忛泦锛堢‖闂ㄧ锛夈€?    - `--smoke`锛氳繍琛屼弗鏍?headless Smoke锛堥渶瑕佹娴嬪埌 `[TEMPLATE_SMOKE_READY]` 鎴?`[DB] opened`锛夈€?
- `run-gdunit-hard`
  - 鐩存帴璋冪敤 `run_gdunit.py`锛屽彧璺?`tests/Adapters/Config` 涓?`tests/Security` 闆嗗悎锛屾姤鍛婅緭鍑哄埌 `logs/e2e/dev-cli/gdunit-hard`銆?
- `run-gdunit-full`
  - 鐩存帴璋冪敤 `run_gdunit.py`锛岃窇 Adapters + Security + Integration + UI 闆嗗悎锛屾姤鍛婅緭鍑哄埌 `logs/e2e/dev-cli/gdunit-full`銆?
- `run-smoke-strict`
  - 璋冪敤 `smoke_headless.py`锛屼互涓ユ牸妯″紡璺?Main 鍦烘櫙 Smoke锛屼綔涓哄揩閫熷彲鐜╂€у啋鐑熷叆鍙ｃ€?
> 瀵?SuperClaude/Claude Code/Codex CLI锛氫笂灞?MCP 宸ュ叿鍙粺涓€涓帴 dev_cli 鐨勫瓙鍛戒护锛屼笉闇€瑕侀噸澶嶇淮鎶よ剼鏈弬鏁扮粏鑺傘€?
---

## 4. 鏈€灏忊€淎I 椹卞姩宸ヤ綔娴佲€濈ず渚?
### 4.1 BMAD 鈫?PRD锛堥珮灞傦級

1. BMAD 娓告垙涓撳浠ｇ悊璇诲彇锛?   - `CLAUDE.md`, `AGENTS.md`锛堝崗浣滆鍒欙級锛?   - `docs/architecture/base/**`锛圕H01鈥揅H07锛夛紱
   - `docs/adr/**`锛堢壒鍒槸 ADR鈥?004/0005/0006/0023锛夛紱
   - 鏈枃浠讹紙Godot 鎶€鏈墠鎻愶級銆?2. 鐢熸垚 PRD 鏃讹細
   - 灏嗚緭鍏?鐘舵€佹洿鏂?瀛樺偍/SLO 璁捐鎴愰€傞厤 Godot+C#锛歋cene+Signal+ConfigFile+SQLite锛岃€岄潪娴忚鍣?UI/HTTP API 涓轰腑蹇冦€?
### 4.2 task-master-ai 鈫?tasks.json

1. 璇诲彇 PRD + ADR/Phase 鏂囨。锛屾寜鏈枃浠剁 2 鑺傜殑缁撴瀯鐢熸垚 `tasks.json`锛?   - 姣忎釜浠诲姟鎸囧畾 `layer`銆乣adr_refs`銆乣chapter_refs`銆乣overlay_refs`锛?   - 鏄庣‘鍝簺浠诲姟鏄?Core銆佸摢浜涙槸 Adapter/Scene銆佸摢浜涙槸 Tests/Docs銆?2. 灏?`tasks.json` 鏀惧叆鏈粨搴擄紙渚嬪 `docs/tasks/tasks.json`锛夛紝渚?SuperClaude/Claude Code 娑堣垂銆?
### 4.3 SuperClaude/Claude Code + Codex CLI 鎵ц浠诲姟

- SuperClaude/Claude Code锛?  - 閫愭潯璇诲彇 `tasks.json`锛屾牴鎹?layer/refs 鍐冲畾淇敼 `Game.Core`銆乣Game.Godot`銆乣Tests.Godot` 鎴栨枃妗ｏ紱
  - 浣跨敤鏈ā鏉垮凡鏈夌殑鑴氭湰鍜屽伐浣滄祦锛堥€氳繃 dev_cli锛夎繘琛屽崟鍏冩祴璇曞拰 GdUnit 鍦烘櫙娴嬭瘯锛?  - 鏈€缁堥€氳繃瀹樻柟 subagents/skills 宸ュ叿杩涜 code review 涓庢祴璇曠粨鏋滄眹鎬汇€?
- Codex CLI锛堝綋鍓嶅姪鎵嬶級锛?  - 浣滀负杈呭姪浠ｇ悊锛屼紭鍏堥伒寰?`AGENTS.md` 涓庢湰鏂囦欢绾︽潫锛?  - 鍦ㄩ渶瑕侀獙璇佷唬鐮?娴嬭瘯/CI 鏃朵紭鍏堣皟鐢細
    - `py -3 scripts/python/dev_cli.py run-ci-basic ...`
    - `py -3 scripts/python/dev_cli.py run-quality-gates ...`銆?
---

## 5. 鍚庣画鎵╁睍寤鸿锛堜粎妯℃澘瑙嗚锛?
- 褰撴煇涓」鐩噯澶囦笂绾挎椂锛?  - 浼樺厛浠?Phase鈥?6/ADR鈥?003 Backlog 涓€夋嫨 Sentry Release Health 鎺ュ叆鏂规锛?  - 缁撳悎 Phase鈥?5/Phase鈥?1 Backlog锛屾敹绱?Perf P95 闂ㄧ锛堟寜鍦烘櫙/鐢ㄤ緥缁村害缁嗗寲锛夈€?
- 瀵规ā鏉挎湰韬紝涓嶅缓璁户缁湪 Phase 鏂囨。缁嗚妭涓婃棤闄愭墿灞曪紝鑰屾槸浼樺厛锛?  - 淇濇寔鏈枃浠朵笌 `PROJECT_CAPABILITIES_STATUS.md` 涓€鑷达紱
  - 淇濊瘉 dev_cli 涓庣幇鏈夎剼鏈殑琛屼负绋冲畾锛屼负澶氫唬鐞嗗崗浣滄彁渚涙竻鏅扮殑鈥滃懡浠?SSoT鈥濄€?

