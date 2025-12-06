# Phase 14 Backlog 鈥?Godot 瀹夊叏鍩虹嚎澧炲己

> 鐘舵€侊細Backlog锛堥潪褰撳墠妯℃澘 DoD锛屾寜闇€娓愯繘鍚敤锛?> 鐩殑锛氭壙鎺?Phase-14-Godot-Security-Baseline.md 涓皻鏈湪褰撳墠 Godot+C# 妯℃澘瀹屽叏钀藉湴鐨勫畨鍏ㄨ鍒欙紝閬垮厤鈥滆摑鍥捐姹傗€濅笌鈥滃疄闄呭疄鐜扳€濊劚鑺傦紝鍚屾椂涓哄悗缁」鐩彁渚涘彲閫夊畨鍏ㄥ寮烘竻鍗曘€?> 鐩稿叧 ADR锛欰DR-0002锛圗lectron 瀹夊叏鍩虹嚎锛夈€丄DR-0003锛堝璁′笌鍙戝竷鍋ュ悍锛夈€丄DR-0006锛堟暟鎹瓨鍌級銆丄DR-0005锛堣川閲忛棬绂侊級

---

## B1锛氱綉缁滅櫧鍚嶅崟閰嶇疆鍖栦笌缁熶竴灏佽

- 鐜扮姸锛?  - `SecurityHttpClient` 褰撳墠閫氳繃 [Export] 鏆撮湶 `AllowedDomains`銆乣AllowedMethods`銆乣EnforceHttps` 绛夊瓧娈碉紝榛樿鍊煎唴鑱斿湪 C# 涓紱
  - Phase鈥?4 鏂囨。涓殑 `OpenUrlSafe` 钃濆浘绀轰緥灏氭湭浣滀负缁熶竴鍏ュ彛瀵规帴 `OS.ShellOpen` 鎴?HTTPRequest 閫傞厤灞傘€?- 鐩爣锛?  - 灏嗏€滃厑璁稿煙鍚?鍗忚/鏂规硶鈥濅粠纭紪鐮佽縼绉诲埌闆嗕腑閰嶇疆锛堜緥濡傞」鐩缃€丆onfigFile 鎴栫幆澧冨彉閲忥級锛屽苟鍦ㄦ枃妗ｄ腑缁欏嚭 SSoT銆?  - 鎻愪緵涓€涓粺涓€鐨?URL 鎵撳紑鍏ュ彛锛堜緥濡?`SecurityUrlAdapter` 鎴栨墿灞?`SecurityHttpClient`锛夛紝灏佽 `OS.ShellOpen()` 璋冪敤锛屽己鍒舵墽琛?HTTPS + 鍩熺櫧鍚嶅崟銆?- 寤鸿瀹炵幇鏂瑰紡锛?  - 寮曞叆 `ALLOWED_EXTERNAL_HOSTS` 鐜鍙橀噺鎴?Config 鑺傜偣锛岃В鏋愪负瀹夊叏鐧藉悕鍗曪紱
  - 鍦?UI/Glue 灞傜姝㈢洿鎺ヨ皟鐢?`OS.ShellOpen`锛屾敼涓鸿皟鐢ㄧ粺涓€鐨勫畨鍏ㄩ€傞厤鍣紱
  - 淇濇寔鐜版湁 `SecurityHttpClient.Validate` 浣滀负 HTTP 閫氳矾鐨勪腑蹇冮獙璇佺偣銆?- 浼樺厛绾э細P1鈥揚2锛堥€傚悎鍦ㄧ湡瀹為」鐩渶瑕佸閾?澶栫綉璁块棶鏃惰惤瀹烇紝妯℃澘闃舵淇濈暀涓?Backlog锛夈€?
---

## B2锛氭枃浠剁郴缁熶繚鎶ょ粺涓€灏佽

- 鐜扮姸锛?  - SqliteDataStore 宸插 DB 璺緞瀹炴柦 `user://` 鍓嶇紑涓?`..` 鎷掔粷锛?  - 鍏跺畠鏂囦欢璁块棶锛堜緥濡?ConfigFile銆佸鍑恒€佷复鏃舵枃浠讹級鐩墠澶氬鐩存帴璋冪敤 Godot `FileAccess`/`DirAccess`锛岀己灏戠粺涓€瀹堝崼锛?  - Phase鈥?4 钃濆浘涓殑 `OpenFileSecure` 绀轰緥灏氭湭浠ヨ繍琛屾椂浠ｇ爜褰㈠紡钀藉湴銆?- 鐩爣锛?  - 鎻愪緵缁熶竴鐨勬枃浠惰闂€傞厤灞傦紙濡?`SecurityFileAdapter` 鎴栨墿灞曠幇鏈夌粍浠讹級锛屽皝瑁?`FileAccess` 涓?`DirAccess` 璋冪敤锛?    - 浠呭厑璁?`res://`锛堝彧璇伙級涓?`user://`锛堣鍐欙級锛?    - 鎷掔粷缁濆璺緞涓?`../` 璺緞绌胯秺锛?    - 澶辫触璺緞鍐欏叆瀹¤鏃ュ織銆?- 寤鸿瀹炵幇鏂瑰紡锛?  - 鍦?Phase鈥?4 钃濆浘鐨?`OpenFileSecure` 鍩虹涓婏紝鎻愮偧涓哄疄闄呴€傞厤绫伙紝骞堕€愭鏇挎崲妯℃澘涓殑鐩磋繛 FileAccess 璋冪敤锛?  - 涓?SqliteDataStore 鐨勮矾寰勮鍒欎繚鎸佷竴鑷达紝閬垮厤鍑虹幇澶氬鏍囧噯銆?- 浼樺厛绾э細P2锛堝瀹夊叏鍩虹嚎鏈変环鍊硷紝浣嗛渶瑕佺粨鍚堝疄闄呬笟鍔?I/O 瑙勫垝鑺傚锛夈€?
---

## B3锛歄S.execute / 澶栭儴杩涚▼璋冪敤瀹堝崼

- 鐜扮姸锛?  - 褰撳墠妯℃澘涓熀鏈湭浣跨敤 `OS.execute`锛孭hase鈥?/AGENTS 涓粎浠庢枃妗ｅ眰瑙勫畾鈥滈粯璁ょ鐢紝鎴栦粎寮€鍙戞€佸紑鍚苟涓ュ璁♀€濓紱
  - 娌℃湁缁熶竴鐨勮繍琛屾椂瀹堝崼鎴栧璁″疄鐜般€?- 鐩爣锛?  - 涓哄悗缁彲鑳藉紩鍏ョ殑澶栭儴杩涚▼璋冪敤鎻愪緵缁熶竴瀹夊叏閫傞厤灞傦細
    - 榛樿鎷掔粷鎵ц澶栭儴鍛戒护锛?    - 鑻ュ繀椤绘墽琛岋紝闇€鏄惧紡澹版槑鐧藉悕鍗曞懡浠?鍙傛暟骞跺啓鍏ュ畨鍏ㄥ璁?JSONL銆?- 寤鸿瀹炵幇鏂瑰紡锛?  - 寮曞叆 `SecurityProcessAdapter`锛屽 `OS.execute` 鍋氱粺涓€灏佽锛屽苟鍦ㄦā鏉夸唬鐮佷腑绂佹鐩存帴璋冪敤 `OS.execute`锛?  - 鍦?Phase鈥?4 鏂囨。涓?ADR鈥?002 鐨?Godot 鍙樹綋涓褰曡閫傞厤鍣ㄧ殑绾︽潫涓庡璁″彛寰勩€?- 浼樺厛绾э細P3锛堜粎鍦ㄧ‘鏈夐渶姹傛椂鍚敤锛屾ā鏉块樁娈靛彲涓嶅疄鐜帮級銆?
---

## B4锛氬璁?JSONL 鏍￠獙鑴氭湰涓庨棬绂?
- 鐜扮姸锛?  - SqliteDataStore 涓?SecurityAudit/SecurityHttpClient 宸插垎鍒啓鍏ワ細
    - `logs/ci/<date>/security-audit.jsonl`锛圖B 灞傦級锛?    - `user://logs/security/security-audit.jsonl`锛堝惎鍔ㄥ熀绾匡級锛?    - `user://logs/security/audit-http.jsonl`锛圚TTP 瀹夊叏锛夛紱
  - Phase鈥?3 Backlog 涓彁鍑轰簡鈥滃璁?JSONL 鏍￠獙鈥濈殑璐ㄩ噺闂ㄧ锛屼絾灏氭湭瀹炵幇鍏蜂綋鑴氭湰銆?- 鐩爣锛?  - 鎻愪緵涓€涓?Python 鑴氭湰锛堜緥濡?`scripts/python/validate_audit_logs.py`锛夛紝瀵瑰叧閿璁℃枃浠惰繘琛岀粨鏋勬牎楠岋細
    - 姣忚蹇呴』鏄悎娉?JSON锛?    - 鍖呭惈鏈€灏忓瓧娈甸泦鍚堬紙渚嬪 {ts, action, reason, target, caller} 鎴栫浉搴斿彉浣擄級锛?    - 鍙€夛細鏍￠獙 event_type/decision 绛夊瓧娈靛€兼槸鍚﹀湪鍏佽鏋氫妇鍐呫€?- 寤鸿瀹炵幇鏂瑰紡锛?  - 灏嗚鑴氭湰浣滀负 Phase鈥?3 `quality_gates.py` 鐨勫彲閫夎蒋闂ㄧ鎺ュ叆锛?  - 鍦?Phase鈥?4 鏂囨。涓?ADR鈥?006/0003 涓紩鐢ㄨ鏍￠獙鑴氭湰浣滀负鈥滃璁″彲楠岃瘉鈥濈殑涓€閮ㄥ垎銆?- 浼樺厛绾э細P2锛堝瀹夊叏涓庡彲瑙傛祴鎬ф湁瀹為檯浠峰€硷紝浣嗕笉寮哄埗妯℃澘闃舵瀹屾垚锛夈€?
---

## B5锛歋ignal 濂戠害楠岃瘉涓庢祴璇曢棬绂?
- 鐜扮姸锛?  - Phase鈥?4 钃濆浘涓彁鍑轰簡鈥淪ignal 濂戠害楠岃瘉鈥濓紙鍙厑璁搁瀹氫箟浜嬩欢銆佸弬鏁扮被鍨嬪尮閰嶏級锛屼絾褰撳墠瀹炵幇涓昏闆嗕腑鍦?Phase鈥? 鐨?EventBusAdapter + 娴嬭瘯灞傦紝灏氭湭褰㈡垚鐙珛鐨勫畨鍏ㄩ棬绂侊紱
  - 娌℃湁涓撻棬鐨?CI 姝ラ妫€鏌モ€滃畨鍏ㄧ浉鍏?Signal 鏄惁鍏峰 XML 娉ㄩ噴銆佸懡鍚嶆槸鍚︾鍚堢害瀹氣€濈瓑銆?- 鐩爣锛?  - 灏嗕笌瀹夊叏鐩稿叧鐨?Signal锛堜緥濡?SecurityHttpClient.RequestBlocked锛夌撼鍏ヤ竴濂楃粺涓€鐨勫绾︿笌闂ㄧ浣撶郴锛?    - 鍛藉悕/鍙傛暟閫氳繃 xUnit/GdUnit4 娴嬭瘯鎴栭潤鎬佹鏌ヨ剼鏈獙璇侊紱
    - 鍏抽敭 Signal 琛ラ綈 XML 鏂囨。娉ㄩ噴锛堣 Phase鈥? Backlog B2锛夈€?- 寤鸿瀹炵幇鏂瑰紡锛?  - 鍦?Phase鈥? Backlog 鐨勫熀纭€涓婏紝涓?Security 鐩稿叧 Signal 澧炲姞娴嬭瘯鐢ㄤ緥鎴栭潤鎬佸垎鏋愯剼鏈紱
  - 灏嗙粨鏋滅撼鍏?Phase鈥?3 鐨勪俊鍙峰悎瑙?Backlog锛坰ignal compliance锛変腑缁熶竴绠＄悊銆?- 浼樺厛绾э細P3锛堟洿鍋忓悜浠ｇ爜鏁存磥涓庡绾︽槑纭紝瀹夊叏鏀剁泭闂存帴锛屽彲鍦ㄥ悗缁凯浠ｄ腑澶勭悊锛夈€?
---

## 浣跨敤璇存槑

- 瀵逛簬鍩轰簬鏈ā鏉垮垱寤虹殑鏂伴」鐩細
  - 鍦ㄩ渶瑕佽闂閮ㄧ綉缁?鏂囦欢/杩涚▼鏃讹紝浼樺厛璇勪及骞跺疄鐜?B1/B2锛屽鐓?Phase鈥?4 鏂囨。涓殑钃濆浘绀轰緥涓庣幇鏈?Security 缁勪欢锛?  - 褰撳璁′笌鍚堣闇€姹傛彁楂樻椂锛屽啀閫愭鍚敤 B4锛堝璁?JSONL 鏍￠獙锛夊拰 B5锛圫ignal 濂戠害闂ㄧ锛夈€?
- 瀵逛簬妯℃澘鏈韩锛?  - 褰撳墠 Phase 14 浠呰姹?`SecurityAudit` + `SqliteDataStore` + `SecurityHttpClient` 鎻愪緵鏈€灏忓畨鍏ㄥ熀绾垮拰瀹¤杈撳嚭锛?  - 鏈?Backlog 鏂囦欢鐢ㄤ簬璁板綍钃濆浘涓皻鏈惤鍦扮殑瀹夊叏澧炲己锛岄伩鍏嶅湪 Phase 14 鍐呴儴缁х画鏃犻檺鎵╁紶鑼冨洿銆?
---

## 褰撳墠妯℃澘瀹炵幇灏忕粨锛?025-11锛岀姸鎬佸揩鐓э級

涓轰究浜庡悗缁淮鎶わ紝杩欓噷琛ュ厖涓€娈碘€滃綋鍓?Godot 妯℃澘宸茬粡钀藉疄鐨勫畨鍏ㄦ祴璇曚笌鎶€鍊虹姸鎬佲€濊鏄庯細

- DB 璺緞瀹夊叏鐢ㄤ緥锛堝凡瀹炵幇锛?  - 鏂囦欢锛歚Tests.Godot/tests/Security/Hard/test_db_path_rejection.gd`
  - 琛屼负锛氶€氳繃 `SqliteDataStore.TryOpen` 楠岃瘉 `user://` 姝ｅ父锛岀粷瀵硅矾寰勪笌 `user://../` 璺緞绌胯秺杩斿洖 `false`銆?  - 浣滅敤锛氬皢 Phase鈥?4 鏂囨。涓€滀粎鍏佽 res:///user://銆佺姝㈢┛瓒娾€濈殑 DB 鍙ｅ緞钀藉疄涓哄彲鎵ц娴嬭瘯銆?
- DB open 澶辫触瀹¤鐢ㄤ緥锛堝凡瀹炵幇锛?  - 鏂囦欢锛歚Tests.Godot/tests/Security/Hard/test_db_open_denied_writes_audit_log.gd`
  - 琛屼负锛氬缁濆璺緞璋冪敤 `TryOpen` 澶辫触鍚庯紝璇诲彇 `logs/ci/<date>/security-audit.jsonl` 鏈€鍚庝竴鏉¤褰曪紝骞舵柇瑷€ `action == "db.open.fail"`銆?  - 浣滅敤锛氶獙璇?`SqliteDataStore.TryOpen` 鐨勫璁￠€昏緫鐪熷疄钀界洏锛岃€屼笉浠呬粎鍋滅暀鍦ㄦ枃妗ｆ弿杩般€?
- HTTP 闃绘柇 Signal 鐢ㄤ緥锛堝凡瀹炵幇锛?  - 鏂囦欢锛歚Tests.Godot/tests/Integration/Security/test_security_http_block_signal.gd`
  - 琛屼负锛氬垱寤?`SecurityHttpClient` 鑺傜偣锛屾嫆缁濅竴涓?`http://` URL锛屽苟鏂█鍙戝嚭浜?`RequestBlocked(reason, url)` Signal 涓?URL 浠?`http://` 寮€澶淬€?  - 浣滅敤锛氫负 Phase鈥?4 Backlog 涓彁鍒扮殑鈥滃畨鍏ㄧ浉鍏?Signal 濂戠害楠岃瘉鈥濇彁渚涗簡涓€鏉″熀纭€绀轰緥锛岀敤浜庡悗缁墿灞曘€?
- `test_db_audit_exec_query_fail.gd` 鐘舵€侊紙淇濈暀涓?SKIP 鎶€鏈€哄崰浣嶏級
  - 鏂囦欢锛歚Tests.Godot/tests/Security/Backlog/test_db_audit_exec_query_fail.gd`
  - 鐜扮姸锛?    - `_new_db` 浣跨敤鏄惧紡绫诲瀷 `var db: Node = null`锛岄伩鍏?GDScript 4.5 瀵?`null` 鎺ㄦ柇澶辫触鐨?Parser Error锛?    - 娴嬭瘯涓讳綋浠呭彂鍑?`push_warning("SKIP: exec/query audit covered by open-fail test; no try/catch in GDScript")` 骞?`assert_bool(true)`锛屼笉鍐嶅皾璇曡Е鍙?C# Execute/Query 寮傚父锛?    - 缂╄繘宸茬粺涓€鏁寸悊锛屼絾 GdUnit4 瀵光€滃巻鍙?Tab/绌烘牸娣风敤鈥濈殑瑙ｆ瀽浠嶅彲鑳界粰鍑虹缉杩涜鍛婏紝寤鸿鍦?Godot 缂栬緫鍣ㄥ唴鐢ㄢ€滅缉杩涜浆鎹⑩€濆姛鑳藉啀娆′繚瀛樹互褰诲簳娓呴櫎銆?  - 浣滅敤锛?    - 鏄庣‘鍛婄煡鍚庣画缁存姢鑰咃細exec/query 绾у埆鐨勫璁￠€昏緫鐩墠鐢扁€渙pen-fail 娴嬭瘯 + C# 绔?Audit 璋冪敤鈥濋棿鎺ヨ鐩栵紱
    - 閬垮厤鍥?GDScript 鏃?try/catch 鍦?headless CI 涓紩鍙?Debugger Break锛屽悓鏃朵繚鐣欐湭鏉ヨ嫢寮曞叆 try/catch 鎴栨ˉ鎺ョ被鏃舵墿灞曟鐢ㄤ緥鐨勭┖闂淬€?
> 缁撹锛?> - Phase 14 鍦ㄥ綋鍓嶆ā鏉夸腑锛孌B/HTTP/Config 鐨勨€滆矾寰勪笌瀹¤鍩虹嚎鈥濆凡缁忛€氳繃澶氭潯 GdUnit 鐢ㄤ緥钀藉湴锛?> - `test_db_audit_exec_query_fail.gd` 琚埢鎰忛檷绾т负 SKIP 鍗犱綅锛屾彁绀哄悗缁嫢瑕佹祴璇?Execute/Query 绾у埆瀹¤锛屽簲浼樺厛寮曞叆鏇村畨鍏ㄧ殑妗ユ帴鏂瑰紡锛堜緥濡?DbTestHelper/C# 渚у寘瑁癸級鑰屼笉鏄湪 GDScript 涓洿鎺ヨЕ鍙戝紓甯搞€?

