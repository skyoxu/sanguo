# Phase 14: Godot 瀹夊叏鍩虹嚎涓庡璁?

> **鏍稿績鐩爣**锛氬疄鐜颁笌 Electron ADR-0002 绛変环鐨?Godot 瀹夊叏鍩虹嚎锛屽缓绔?URL 鐧藉悕鍗曘€丠TTPRequest 绾︽潫銆佹枃浠剁郴缁熶繚鎶ゃ€佸璁℃棩蹇楃殑瀹屾暣浣撶郴銆? 
> **宸ヤ綔閲?*锛?-7 浜哄ぉ  
> **渚濊禆**锛歅hase 8锛堝満鏅璁★級銆丳hase 12锛圚eadless 娴嬭瘯锛? 
> **浜や粯鐗?*锛歋ecurity.cs Autoload + 8+ 涓?GdUnit4 娴嬭瘯 + ADR-0018 鑽夋 + CI 闆嗘垚  
> **楠屾敹鏍囧噯**锛氭湰鍦?`npm run test:security` 閫氳繃 + 瀹夊叏瀹¤ JSONL 鐢熸垚

---

## 1. 鑳屾櫙涓庡姩鏈?

### 鍘熺増锛坴itegame锛夊畨鍏ㄥ熀绾?

**Electron 瀹炵幇锛圓DR-0002锛?*锛?
- nodeIntegration=false, contextIsolation=true, sandbox=true
- 涓ユ牸 CSP锛氭棤 unsafe-inline/eval锛宑onnect-src 鐧藉悕鍗?
- Preload 鑴氭湰鐧藉悕鍗曟毚闇?API锛屼富杩涚▼楠岃瘉鍙傛暟
- HTTP 璇锋眰寮哄埗 HTTPS锛屽煙/璺緞鐧藉悕鍗?

**浠ｇ爜绀轰緥**锛?
```javascript
// electron/main.ts
const window = new BrowserWindow({
  nodeIntegration: false,
  contextIsolation: true,
  webPreferences: { preload: path.join(__dirname, 'preload.ts') }
});

window.webContents.session.webRequest.onBeforeSendHeaders(
  (details, callback) => {
    const url = new URL(details.url);
    const allowed = WHITELIST.some(d => url.hostname.endsWith(d));
    callback({ cancel: !allowed });
  }
);
```

### Godot 鐗瑰畾鎸戞垬

| 鎸戞垬 | 鏍瑰洜 | Godot 瑙ｅ喅鏂规 |
|-----|-----|--------------|
| 鏃犳祻瑙堝櫒 CSP | 鑴氭湰璇█鑷敱搴﹂珮 | 搴旂敤灞傜櫧鍚嶅崟 + 杩愯鏃舵鏌?|
| HTTPRequest API 涓嶅悓 | Godot 鍐呯疆绫诲瀷 | 鑷畾涔夐€傞厤灞傦紙HTTPSecurityWrapper锛?|
| 鏂囦欢绯荤粺鏃犳矙绠?| 鑴氭湰鍙闂换鎰忚矾寰?| user:// 绾︽潫 + 杩愯鏃跺畧鍗?|
| Signal 鏃犵被鍨嬪畨鍏?| 寮辩被鍨嬩俊鍙风郴缁?| 濂戠害瀹氫箟 + 娴嬭瘯瑕嗙洊 + Lint |
| 鏃犲師鐢熷璁?API | 鏃?Sentry SDK锛?Native锛?| JSONL 鏈湴 + Sentry.cs 涓诲姩涓婃姤 |

### 瀹夊叏鍩虹嚎鐨勪环鍊?

1. **闃插尽鍏ヤ镜**锛氱櫧鍚嶅崟鏈哄埗闃绘鎭舵剰澶栬仈涓庢湰鍦版枃浠惰闂?
2. **鍚堣瀹¤**锛氬畬鏁村璁℃棩蹇楁弧瓒?SOC2/ISO27001 璇佹槑闇€姹?
3. **浜嬪悗婧簮**锛欽SONL 璁板綍鎵€鏈夊畨鍏ㄥ喅绛栦笌鎷掔粷鍘熷洜
4. **娓愯繘澧炲己**锛氬熀纭€瑙勫垯 + 鍙墿灞曡嚜瀹氫箟瑙勫垯寮曟搸

---

## 2. 瀹夊叏鍩虹嚎瀹氫箟

### 2.0 Godot+C# 鍙樹綋锛堝綋鍓嶆ā鏉垮疄鐜帮級

> 鏈妭鎻忚堪鐨勬槸 **godotgame 妯℃澘宸茬粡钀藉湴鐨勫畨鍏ㄥ熀绾垮疄鐜?*锛岀敤浜庡榻?ADR鈥?002/0006 涓庤繍琛屾椂浠ｇ爜銆備笅鏂囩粰鍑虹殑澶у彿 `Security : Node` 绀轰緥浠嶇劧鏄摑鍥剧骇鍙傝€冿紝涓嶄唬琛ㄥ綋鍓嶄粨搴撶殑鍞竴瀹炵幇褰㈠紡銆?
- 鑷涓庡璁★紙鍚姩鍩虹嚎锛夛細
  - Autoload锛歚SecurityAudit="res://Game.Godot/Scripts/Security/SecurityAudit.cs"` 宸插湪 `project.godot` 涓厤缃紱
  - 鍚姩鏃跺啓鍏?`user://logs/security/security-audit.jsonl`锛岃褰曪細
    - `ts`锛歎TC 鏃堕棿鎴筹紙ISO8601锛夛紱
    - `event_type="SECURITY_BASELINE"`锛?    - `app`锛氬簲鐢ㄥ悕绉帮紙浠?`application/config/name` 鑾峰彇锛屽け璐ユ椂閫€鍖栦负 `GodotGame`锛夛紱
    - `godot`锛欸odot 鐗堟湰瀛楃涓诧紱
    - `db_backend`锛歚GODOT_DB_BACKEND` 鐜鍙橀噺鎴?`default`锛?    - `demo`锛歚TEMPLATE_DEMO` 鐜鍙橀噺鏄惁涓?`1`锛?    - `plugin_sqlite`锛氭槸鍚︽帰娴嬪埌 SQLite 鎻掍欢绫诲瓨鍦ㄣ€?
- DB 瀹夊叏涓庡璁★紙鏁版嵁瀛樺偍鍙樹綋锛屽綊鍙?ADR鈥?006锛夛細
  - 缁勪欢锛歚Game.Godot/Adapters/SqliteDataStore.cs` 瀹炵幇 `ISqlDatabase`锛屽苟鍦?`Open(string dbPath)` 涓己鍒讹細
    - 浠呭厑璁?`user://` 鍓嶇紑璺緞锛?    - 绂佹鍖呭惈 `..` 鐨勮矾寰勭┛瓒婏紱
    - 浣跨敤 `GlobalizePath` 鍚庝繚璇佺洰褰曞瓨鍦ㄣ€?  - 瀹¤锛?    - 鍦?`TryOpen/Execute/Query` 绛夊け璐ヨ矾寰勮皟鐢ㄥ唴閮?`Audit(action, reason, target)`锛?    - 鍐欏叆 `logs/ci/<YYYY-MM-DD>/security-audit.jsonl`锛?    - 瀛楁鏍煎紡锛歚{ ts, action, reason, target, caller }`锛屼笌 ADR鈥?006 / AGENTS.md 涓 DB 瀹¤鏃ュ織鐨勫彛寰勪竴鑷淬€?
- HTTP 瀹夊叏涓庡璁★紙缃戠粶鐧藉悕鍗曞彉浣擄級锛?  - 缁勪欢锛歚Game.Godot/Scripts/Security/SecurityHttpClient.cs`锛屼綔涓?`Node` 绾?http 楠岃瘉鍣細
    - `AllowedDomains` / `AllowedMethods` / `EnforceHttps` / `MaxBodyBytes` 閫氳繃 [Export] 鎻愪緵閰嶇疆锛?    - `Validate(method, url, contentType, bodyBytes)`锛?      - 鎷掔粷绌?URL銆乣file://`銆侀潪 https锛堝湪 `EnforceHttps==true` 鏃讹級锛?      - 鎷掔粷涓嶅湪 `AllowedDomains` 鍐呯殑鍩熷悕锛?      - 鎷掔粷缂哄皯 `Content-Type` 鐨?POST锛?      - 鎷掔粷瓒呰繃 `MaxBodyBytes` 鐨勮姹備綋锛?      - 鍏佽璇锋眰鏃惰 `HTTP_ALLOWED` 瀹¤浜嬩欢銆?  - 瀹¤杈撳嚭锛?    - 闃绘柇鏃讹細閫氳繃 `RequestBlocked(reason, url)` Signal 鏆撮湶缁?GDScript锛?    - 鎵€鏈夊厑璁?鎷掔粷璺緞璋冪敤 `Audit(eventType, url, reason)`锛屽啓鍏?`user://logs/security/audit-http.jsonl`锛?    - 瀛楁鏍煎紡锛歚{ ts, event_type, url, reason, source }`銆?
- 宸叉湁瀹夊叏娴嬭瘯锛圙dUnit4锛夛細
  - HTTP 鎷︽埅涓庡璁★細
    - `Tests.Godot/tests/Integration/Security/test_security_http_client.gd`锛氶獙璇?http 鍗忚銆佹湭鐭ュ煙鍚嶃€丳OST 鏃?Content-Type/瓒呭ぇ body 琚嫆缁濓紱
    - `Tests.Godot/tests/Integration/Security/test_security_http_audit.gd`锛氶獙璇佹嫆缁濊矾寰勪細鍐欏叆 `audit-http.jsonl`锛屼笖 `event_type` 鍖呭惈 `protocol_denied`锛?    - `Tests.Godot/tests/Integration/Security/test_security_http_allowed_audit.gd`锛氶獙璇佸厑璁歌矾寰勫啓鍏?`HTTP_ALLOWED` 浜嬩欢銆?  - DB 瀹¤涓庡け璐ヨ矾寰勶細
    - `Tests.Godot/tests/Security/Backlog/test_db_audit_exec_query_fail.gd`锛氶獙璇?DB 鎵ц澶辫触鏃朵細鍦?`logs/ci/<date>/security-audit.jsonl` 涓拷鍔犲璁¤銆?
> 鍚庣画濡傞渶鎵╁睍 URL/file/signal 绛夐澶栧畨鍏ㄨ鍒欙紝搴斾紭鍏堝湪涓婅堪缁勪欢鍩虹涓婂閲忓疄鐜帮紝骞跺湪 Phase-14 Backlog 涓櫥璁版墿灞曢」銆?
### 2.1 5 澶ч槻瀹堥鍩?
#### A. 缃戠粶鐧藉悕鍗曪紙URL / Domain锛?

**瑙勫垯**锛?
- [鍏佽]锛歨ttps://sentry.io, https://api.example.com 绛夊彈淇″煙
- FAIL **Deny**锛氶潪鐧藉悕鍗曞煙銆乭ttp 鍗忚銆乫ile:// 鏈湴璺緞
- FAIL **Deny**锛?./../../ 璺緞绌胯秺

**瀹炵幇**锛?
```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
```

#### B. HTTPRequest 绾︽潫

**瑙勫垯**锛?
- [鍏佽]锛欸ET锛堟暟鎹幏鍙栵級銆丳OST锛圫entry 涓婃姤锛?
- FAIL **Deny**锛歅UT銆丏ELETE銆丳ATCH锛堜慨鏀规搷浣滐級
- FAIL **Deny**锛氭棤 Content-Type 鐨?POST
- FAIL **Deny**锛氳秴澶ц姹備綋锛?10MB锛?

**瀹炵幇**锛?
```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
```

#### C. 鏂囦欢绯荤粺淇濇姢

**瑙勫垯**锛?
- [鍏佽]锛歳es:// 锛堣祫婧愮洰褰曪紝鍙锛?
- [鍏佽]锛歶ser:// 锛堢敤鎴锋暟鎹洰褰曪紝璇诲啓锛?
- FAIL **Deny**锛歰s.* 璺緞锛堢粷瀵硅矾寰勶級
- FAIL **Deny**锛?./ 璺緞绌胯秺

**瀹炵幇**锛?
```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
```

#### D. 瀹¤鏃ュ織锛圝SONL锛?

**鏍煎紡**锛?
```jsonl
{"timestamp":"2025-11-07T10:30:45.123Z","event_type":"URL_ALLOWED","resource":"https://sentry.io/api/events/","decision":"ALLOW","reason":"passed all checks","source":"Security.is_url_allowed"}
{"timestamp":"2025-11-07T10:30:46.456Z","event_type":"DOMAIN_DENIED","resource":"https://malicious.com/data","decision":"DENY","reason":"domain not in whitelist: malicious.com","source":"Security.is_url_allowed"}
{"timestamp":"2025-11-07T10:30:47.789Z","event_type":"HTTP_REQUEST_INITIATED","resource":"https://api.example.com/user","decision":"ALLOW","reason":"method=GET","source":"HTTPSecurityWrapper.request_secure"}
```

**瀛楁**锛?
- timestamp锛欼SO 8601 鏍煎紡锛岀簿纭埌姣
- event_type锛氭灇涓惧€硷紙URL_ALLOWED, DOMAIN_DENIED, HTTP_METHOD_DENIED 绛夛級
- resource锛氭搷浣滅殑璧勬簮锛圲RL銆佹枃浠惰矾寰勶級
- decision锛欰LLOW / DENY / ERROR
- reason锛氫汉绫诲彲璇荤殑鍐崇瓥鍘熷洜
- source锛氬彂鍑哄喅绛栫殑鍑芥暟/鏂规硶

**瀹炵幇**锛?
```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
```

#### E. Signal 濂戠害楠岃瘉

**瑙勫垯**锛?
- [鍏佽]锛氶瀹氫箟鐨?Signal锛坓ame_started, game_over 绛夛級
- FAIL **Deny**锛氭湭娉ㄥ唽鐨?Signal 鍙戦€?
- FAIL **Deny**锛歋ignal 鍙傛暟绫诲瀷涓嶅尮閰?

**瀹炵幇**锛堥€氳繃 GdUnit4 娴嬭瘯楠岃瘉锛夛細
```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
```

---

## 3. Security.cs Autoload 瀹屾暣瀹炵幇

### 3.1 鏍稿績缁撴瀯

 ```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
 ```

---

## 4. 鍙戝竷鍖呭畬鏁存€т笌鏉冮檺绛栫暐锛圵indows + C#锛?

### 4.1 浠ｇ爜绛惧悕涓庡畬鏁存€ф牎楠?
- 浣跨敤 signtool 瀵瑰鍑虹殑 `*.exe` 杩涜 SHA256 绛惧悕锛堣 Phase-17 闄勫綍 `scripts/sign_executable.py`锛夛紱
- 鍦ㄥ彂甯冨墠鐢熸垚鏍￠獙鍜屾竻鍗曪紙SHA256锛夛紝鍦ㄥ彂甯冭鏄庝腑鎻愪緵涓嬭浇涓庢牎楠屾寚寮曪紱
- CI 涓皢绛惧悕鏃ュ織涓庢牎楠屽拰钀界洏 `logs/ci/YYYY-MM-DD/security/`锛屽綊妗ｄ笌闂ㄧ涓€鍚屼繚瀛樸€?

### 4.2 鏂囦欢绯荤粺涓?SQLite 鏉冮檺
- 浠呭湪 `user://` 涓嬭鍐欒繍琛屾椂鏁版嵁锛宍res://` 涓ユ牸鍙锛?
- SQLite 鏁版嵁搴撴枃浠跺缓璁斁缃簬 `user://data/`锛岃褰曟枃浠舵潈闄愮瓥鐣ヤ笌杞浆锛圵AL 妯″紡銆佸浠界洰褰曪級锛?
- 鏃ュ織涓庡璁★紙JSONL锛夎矾寰勭粺涓€涓?`user://logs/<module>/`锛岄伩鍏嶅啓鍏ユ湭鐭ヤ綅缃紱
- 绂佹浠ョ粷瀵硅矾寰勮闂郴缁熺洰褰曪紱鍦ㄥ璁′腑璁板綍鎷掔粷鍘熷洜涓庤皟鐢ㄦ簮銆?

### 4.3 鍙嶅皠/鍔ㄦ€佸姞杞介檺鍒?
- 绂佹浠庝笉鍙椾俊浠讳綅缃姩鎬佸姞杞?DLL/鑴氭湰锛圙DNative/Reflection 鍙楅檺锛夛紱
- 鍦ㄤ唬鐮佸璁¤剼鏈腑鎵弿楂樺嵄 API锛堝弽灏勮皟鐢?DllImport/Process.Start 绛夛級锛?
- 灏嗏€滃畨鍏ㄥ璁¤剼鏈€濊緭鍑鸿惤鐩樹负 `logs/ci/YYYY-MM-DD/security/security-audit.json`锛屼綔涓?Phase-13 鍙€夐棬绂佹潵婧愶紙閿欒鏁?0锛夈€?

### 4.4 闅愮涓庤劚鏁?
- 瀵规棩蹇椾腑鍙兘鍖呭惈鐨勮矾寰?鐢ㄦ埛淇℃伅杩涜鑴辨晱锛?
- Sentry 涓紑鍚?PII 绛栫暐涓庨噰鏍风巼锛屽噺灏戞晱鎰熶俊鎭毚闇诧紱
- 灏嗚劚鏁忚鍒欎笌閲囨牱鐜囦綔涓烘瀯寤哄厓鏁版嵁鐨勪竴閮ㄥ垎锛堝弬鑰?Phase-16 涓?Phase-17锛夈€?

### 3.2 HTTPSecurityWrapper 瀹炵幇

```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
```

---

## 4. GdUnit4 娴嬭瘯濂椾欢锛?+ 涓祴璇曪級

### 4.1 URL 鐧藉悕鍗曟祴璇?

```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
```

### 4.2 HTTPRequest 瀹夊叏娴嬭瘯

```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
```

### 4.3 鏂囦欢绯荤粺淇濇姢娴嬭瘯

```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
```

### 4.4 瀹¤鏃ュ織娴嬭瘯

```csharp
using Godot;
using System;
using System.Text.Json;
using System.IO;

public partial class Security : Node
{
    private static readonly string[] AllowedDomains = new []{"https://example.com","https://sentry.io"};

    public bool OpenUrlSafe(string url)
    {
        if (!url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
        {
            Audit("PROTOCOL_DENIED", url, "not https");
            return false;
        }
        var allowed = false;
        foreach (var d in AllowedDomains)
        {
            if (url.StartsWith(d, StringComparison.OrdinalIgnoreCase)) { allowed = true; break; }
        }
        if (!allowed)
        {
            Audit("DOMAIN_DENIED", url, "not in whitelist");
            return false;
        }
        OS.ShellOpen(url);
        Audit("URL_ALLOWED", url, "ok");
        return true;
    }

    public FileAccess? OpenFileSecure(string path, FileAccess.ModeFlags mode)
    {
        if (!(path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) || path.StartsWith("user://", StringComparison.OrdinalIgnoreCase)))
        {
            Audit("FILE_PATH_DENIED", path, "not res:// or user://");
            return null;
        }
        if (path.Contains("../"))
        {
            Audit("FILE_TRAVERSAL_BLOCKED", path, "contains ../");
            return null;
        }
        if (path.StartsWith("res://", StringComparison.OrdinalIgnoreCase) && mode != FileAccess.ModeFlags.Read)
        {
            Audit("RES_WRITE_BLOCKED", path, "res:// read-only");
            return null;
        }
        Audit("FILE_OPEN_ALLOWED", path, $"mode={mode}");
        return FileAccess.Open(path, mode);
    }

    private void Audit(string eventType, string resource, string reason)
    {
        var entry = new { timestamp = DateTime.UtcNow.ToString("O"), event_type = eventType, resource, decision = eventType.EndsWith("ALLOWED")?"ALLOW":"DENY", reason, source = nameof(Security)};
        var line = JsonSerializer.Serialize(entry) + "
";
        var dir = ProjectSettings.GlobalizePath("user://logs/security");
        Directory.CreateDirectory(dir);
        File.AppendAllText(Path.Combine(dir, "audit.jsonl"), line);
    }
}
```

---

## 5. ADR-0018 鑽夋

### ADR-0018: Godot 瀹夊叏鍩虹嚎涓庤繍琛屾椂闃叉姢

**Status**: Proposed  
**Context**: 灏?Electron CSP + preload 瀹夊叏妯″瀷杩佺Щ鍒?Godot 鐜  
**Decision**:
1. 寤虹珛 Security.cs Autoload 浣滀负鍏ㄥ眬瀹夊叏瀹堝崼
2. URL 鐧藉悕鍗曟満鍒讹紙纭紪鐮?+ 鍔ㄦ€佸姞杞斤級
3. HTTPRequest 寮哄埗鍗忚/鏂规硶/澶у皬绾︽潫
4. 鏂囦欢绯荤粺 user:// 绾︽潫 + 璺緞绌胯秺妫€鏌?
5. JSONL 瀹¤鏃ュ織 + Sentry 涓婃姤闆嗘垚

**Consequences**:
- 鎵€鏈夌綉缁?鏂囦欢鎿嶄綔鍧囬€氳繃 Security.cs锛堟€ц兘 <1ms锛?
- JSONL 鏃ュ織渚夸簬浜嬪悗婧簮涓庡悎瑙勫璁?
- 鍙墿灞曡鍒欏紩鎿庢敮鎸佽嚜瀹氫箟瀹夊叏绛栫暐
- 闇€瀹氭湡缁存姢鐧藉悕鍗曪紙鏂板煙鍚嶉渶鏇存柊锛?

**References**:
- ADR-0002: Electron 瀹夊叏鍩虹嚎锛堝師鐗堝鏍囷級
- OWASP Top 10: A01/A02/A04锛堟敞鍏ャ€佽璇併€佷笉瀹夊叏璁捐锛?
- Godot 鏂囨。锛欶ile System Access锛坲ser:// 鏈哄埗锛?
- Sentry Godot SDK锛欵rror Tracking

---

## 6. CI 闆嗘垚

### 6.1 security-gate.ps1

```powershell
# scripts/ci/run_security_tests.ps1

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$LogDir
)

$ErrorActionPreference = "Stop"

$gutSecurityReport = "$LogDir/security-tests.json"

Write-Host "Running security tests with GdUnit4..." -ForegroundColor Cyan

# 杩愯 Security 鐩稿叧 GdUnit4 娴嬭瘯
$gutCommand = @(
    "godot", "--headless", "--no-window",
    "--scene", "res://tests/SmokeTestRunner.tscn",
    "--", "output=$gutSecurityReport", "filter=Security"
)

Write-Host "Running: $($gutCommand -join ' ')" -ForegroundColor Cyan
& $gutCommand[0] $gutCommand[1..($gutCommand.Length-1)]

# 楠岃瘉瀹¤鏃ュ織瀛樺湪涓旀牸寮忔纭?
$auditLog = "user://logs/security-audit.jsonl"

if (Test-Path $auditLog) {
    Write-Host "Audit log generated: $auditLog" -ForegroundColor Green
    
    # 楠岃瘉 JSONL 鏍煎紡
    $validLines = 0
    Get-Content $auditLog | ForEach-Object {
        if ($_ -match '^\{.*\}$') {
            $validLines++
        }
    }
    
    Write-Host "Valid JSONL lines: $validLines" -ForegroundColor Green
} else {
    Write-Host "FAIL Audit log not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Security tests completed" -ForegroundColor Green
exit 0
```

### 6.2 Phase 13 璐ㄩ噺闂ㄧ鎵╁睍

鍦?`quality_gates.py` 涓坊鍔?GATE-10 瀹¤鏃ュ織楠岃瘉锛堝凡鍦?Phase 13 涓畾涔夛級銆?

---

## 7. 瀹屾垚娓呭崟涓庨獙鏀舵爣鍑?

### 7.1 瀹炵幇妫€鏌ユ竻鍗?

- [ ] 瀹炵幇 Security.cs Autoload锛堟牳蹇冨姛鑳斤級
  - [ ] URL 鐧藉悕鍗曠鐞?
  - [ ] HTTPRequest 鍖呰涓庣害鏉?
  - [ ] 鏂囦欢绯荤粺淇濇姢
  - [ ] JSONL 瀹¤鏃ュ織
- [ ] 缂栧啓 鈮? 涓?GdUnit4 瀹夊叏娴嬭瘯
  - [ ] URL 鐧藉悕鍗曪紙6 涓級
  - [ ] HTTPRequest锛? 涓級
  - [ ] 鏂囦欢绯荤粺锛? 涓級
  - [ ] 瀹¤鏃ュ織锛? 涓級
  - [ ] 鎬昏锛氣墺20 涓祴璇曠敤渚?
- [ ] 瀹炵幇 HTTPSecurityWrapper 鍖呰绫?
- [ ] 闆嗘垚鍒板啋鐑熸祴璇曪紙Phase 12锛?
- [ ] 鐢熸垚瀹夊叏瀹¤鎶ュ憡锛圚TML锛?
- [ ] 缂栧啓 ADR-0018 鑽夋
- [ ] CI 鑴氭湰闆嗘垚锛坮un_security_tests.ps1锛?
- [ ] 鏂囨。鍖栫櫧鍚嶅崟绠＄悊娴佺▼
- [ ] 鏈湴娴嬭瘯 `npm run test:security` 閫氳繃

### 7.2 楠屾敹鏍囧噯

| 椤圭洰 | 楠屾敹鏍囧噯 | 纭 |
|-----|--------|------|
| Security.cs 瀹屾暣搴?| 5 澶ч槻瀹堥鍩熷叏瑕嗙洊 | 鈻?|
| 娴嬭瘯瑕嗙洊 | 鈮?0 涓?GdUnit4 娴嬭瘯閫氳繃 | 鈻?|
| 瀹¤鏃ュ織 | JSONL 鏍煎紡 100% 鏈夋晥 | 鈻?|
| 鐧藉悕鍗曠鐞?| 纭紪鐮?+ 鍔ㄦ€佸姞杞介厤鍚?| 鈻?|
| CI 闆嗘垚 | 鑷姩鐢熸垚 security-audit.jsonl | 鈻?|
| 鏂囨。瀹屾暣 | Phase 14 鏂囨。 鈮?00 琛?| 鈻?|
| ADR 璐ㄩ噺 | ADR-0018 鑽夋瀹屾垚 | 鈻?|

---

## 8. 椋庨櫓涓庣紦瑙?

| # | 椋庨櫓 | 绛夌骇 | 缂撹В |
|---|-----|------|-----|
| 1 | 鐧藉悕鍗曡繃涓ュ鑷村姛鑳借闃?| 涓?| 鍓嶆湡瀹芥澗锛坅udit only锛夛紝閫愭寮哄埗 |
| 2 | 瀹¤鏃ュ織鎬ц兘褰卞搷 | 浣?| 寮傛鍐欏叆锛屽彲閰嶇疆鍏抽棴 |
| 3 | Signal 濂戠害闅句互寮哄埗 | 涓?| 閫氳繃 GdUnit4 娴嬭瘯 + Lint 瑙勫垯 |
| 4 | HTTPRequest 瓒呮椂瀵艰嚧鍗￠】 | 浣?| timeout 閰嶇疆锛堥粯璁?10s锛夛紝鍙檷绾?|
| 5 | 鐧藉悕鍗曠増鏈鐞嗘贩涔?| 涓?| 鐗堟湰鍖栭厤缃枃浠?+ PR 娴佺▼ |

---

## 9. 鍙傝€冧笌閾炬帴

- **ADR-0002**锛欵lectron 瀹夊叏鍩虹嚎锛堝師鐗堝鏍囷級
- **ADR-0003**锛氬彲瑙傛祴鎬т笌瀹¤鏃ュ織
- **Phase 8**锛氬満鏅璁★紙Signal 瀹氫箟锛?
- **Phase 12**锛欻eadless 娴嬭瘯妗嗘灦
- **Phase 13**锛氳川閲忛棬绂佽剼鏈紙GATE-10 瀹¤鏃ュ織楠岃瘉锛?
- **Godot 鏂囨。**锛歔FileAccess](https://docs.godotengine.org/en/stable/classes/class_fileaccess.html)銆乕HTTPRequest](https://docs.godotengine.org/en/stable/classes/class_httprequest.html)銆乕Signal](https://docs.godotengine.org/en/stable/tutorials/step_by_step/signals.html)

---

**鏂囨。鐗堟湰**锛?.0  
**瀹屾垚鏃ユ湡**锛?025-11-07  
**浣滆€?*锛欳laude Code  
**鐘舵€?*锛歊eady for Implementation


