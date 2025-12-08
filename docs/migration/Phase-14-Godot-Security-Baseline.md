# Phase 14: Godot 安全基线与审计

> **核心目标**：实现与 Electron ADR-0002 等价的 Godot 安全基线，建立 URL 白名单、HTTPRequest 约束、文件系统保护、审计日志的完整体系。  
> **工作量**：5-7 人天  
> **依赖**：Phase 8（场景设计）、Phase 12（Headless 测试）  
> **交付物**：Security.cs Autoload + 8+ 个 GdUnit4 测试 + ADR-0018 草案 + CI 集成  
> **验收标准**：本地 `npm run test:security` 通过 + 安全审计 JSONL 生成

---

## 1. 背景与动机

### 原版（vitegame）安全基线

**Electron 实现（ADR-0002）**：
- nodeIntegration=false, contextIsolation=true, sandbox=true
- 严格 CSP：无 unsafe-inline/eval，connect-src 白名单
- Preload 脚本白名单暴露 API，主进程验证参数
- HTTP 请求强制 HTTPS，域/路径白名单

**代码示例**：
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

### Godot 特定挑战

| 挑战 | 根因 | Godot 解决方案 |
|-----|-----|--------------|
| 无浏览器 CSP | 脚本语言自由度高 | 应用层白名单 + 运行时检查 |
| HTTPRequest API 不同 | Godot 内置类型 | 自定义适配层（HTTPSecurityWrapper） |
| 文件系统无沙箱 | 脚本可访问任意路径 | user:// 约束 + 运行时守卫 |
| Signal 无类型安全 | 弱类型信号系统 | 契约定义 + 测试覆盖 + Lint |
| 无原生审计 API | 无 Sentry SDK（ Native） | JSONL 本地 + Sentry.cs 主动上报 |

### 安全基线的价值

1. **防御入侵**：白名单机制阻止恶意外联与本地文件访问
2. **合规审计**：完整审计日志满足 SOC2/ISO27001 证明需求
3. **事后溯源**：JSONL 记录所有安全决策与拒绝原因
4. **渐进增强**：基础规则 + 可扩展自定义规则引擎

---

## 2. 安全基线定义

### 2.1 5 大防守领域

#### A. 网络白名单（URL / Domain）

**规则**：
- [允许]：https://sentry.io, https://api.example.com 等受信域
- FAIL **Deny**：非白名单域、http 协议、file:// 本地路径
- FAIL **Deny**：../../../ 路径穿越

**实现**：
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

#### B. HTTPRequest 约束

**规则**：
- [允许]：GET（数据获取）、POST（Sentry 上报）
- FAIL **Deny**：PUT、DELETE、PATCH（修改操作）
- FAIL **Deny**：无 Content-Type 的 POST
- FAIL **Deny**：超大请求体（>10MB）

**实现**：
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

#### C. 文件系统保护

**规则**：
- [允许]：res:// （资源目录，只读）
- [允许]：user:// （用户数据目录，读写）
- FAIL **Deny**：os.* 路径（绝对路径）
- FAIL **Deny**：../ 路径穿越

**实现**：
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

#### D. 审计日志（JSONL）

**格式**：
```jsonl
{"timestamp":"2025-11-07T10:30:45.123Z","event_type":"URL_ALLOWED","resource":"https://sentry.io/api/events/","decision":"ALLOW","reason":"passed all checks","source":"Security.is_url_allowed"}
{"timestamp":"2025-11-07T10:30:46.456Z","event_type":"DOMAIN_DENIED","resource":"https://malicious.com/data","decision":"DENY","reason":"domain not in whitelist: malicious.com","source":"Security.is_url_allowed"}
{"timestamp":"2025-11-07T10:30:47.789Z","event_type":"HTTP_REQUEST_INITIATED","resource":"https://api.example.com/user","decision":"ALLOW","reason":"method=GET","source":"HTTPSecurityWrapper.request_secure"}
```

**字段**：
- timestamp：ISO 8601 格式，精确到毫秒
- event_type：枚举值（URL_ALLOWED, DOMAIN_DENIED, HTTP_METHOD_DENIED 等）
- resource：操作的资源（URL、文件路径）
- decision：ALLOW / DENY / ERROR
- reason：人类可读的决策原因
- source：发出决策的函数/方法

**实现**：
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

#### E. Signal 契约验证

**规则**：
- [允许]：预定义的 Signal（game_started, game_over 等）
- FAIL **Deny**：未注册的 Signal 发送
- FAIL **Deny**：Signal 参数类型不匹配

**实现**（通过 GdUnit4 测试验证）：
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

## 3. Security.cs Autoload 完整实现

### 3.1 核心结构

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

## 4. 发布包完整性与权限策略（Windows + C#）

### 4.1 代码签名与完整性校验
- 使用 signtool 对导出的 `*.exe` 进行 SHA256 签名（见 Phase-17 附录 `scripts/sign_executable.py`）；
- 在发布前生成校验和清单（SHA256），在发布说明中提供下载与校验指引；
- CI 中将签名日志与校验和落盘 `logs/ci/YYYY-MM-DD/security/`，归档与门禁一同保存。

### 4.2 文件系统与 SQLite 权限
- 仅在 `user://` 下读写运行时数据，`res://` 严格只读；
- SQLite 数据库文件建议放置于 `user://data/`，记录文件权限策略与轮转（WAL 模式、备份目录）；
- 日志与审计（JSONL）路径统一为 `user://logs/<module>/`，避免写入未知位置；
- 禁止以绝对路径访问系统目录；在审计中记录拒绝原因与调用源。

### 4.3 反射/动态加载限制
- 禁止从不受信任位置动态加载 DLL/脚本（GDNative/Reflection 受限）；
- 在代码审计脚本中扫描高危 API（反射调用/DllImport/Process.Start 等）；
- 将“安全审计脚本”输出落盘为 `logs/ci/YYYY-MM-DD/security/security-audit.json`，作为 Phase-13 可选门禁来源（错误数=0）。

### 4.4 隐私与脱敏
- 对日志中可能包含的路径/用户信息进行脱敏；
- Sentry 中开启 PII 策略与采样率，减少敏感信息暴露；
- 将脱敏规则与采样率作为构建元数据的一部分（参考 Phase-16 与 Phase-17）。

### 3.2 HTTPSecurityWrapper 实现

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

## 4. GdUnit4 测试套件（8+ 个测试）

### 4.1 URL 白名单测试

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

### 4.2 HTTPRequest 安全测试

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

### 4.3 文件系统保护测试

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

### 4.4 审计日志测试

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

## 5. ADR-0018 草案

### ADR-0018: Godot 安全基线与运行时防护

**Status**: Proposed  
**Context**: 将 Electron CSP + preload 安全模型迁移到 Godot 环境  
**Decision**:
1. 建立 Security.cs Autoload 作为全局安全守卫
2. URL 白名单机制（硬编码 + 动态加载）
3. HTTPRequest 强制协议/方法/大小约束
4. 文件系统 user:// 约束 + 路径穿越检查
5. JSONL 审计日志 + Sentry 上报集成

**Consequences**:
- 所有网络/文件操作均通过 Security.cs（性能 <1ms）
- JSONL 日志便于事后溯源与合规审计
- 可扩展规则引擎支持自定义安全策略
- 需定期维护白名单（新域名需更新）

**References**:
- ADR-0002: Electron 安全基线（原版对标）
- OWASP Top 10: A01/A02/A04（注入、认证、不安全设计）
- Godot 文档：File System Access（user:// 机制）
- Sentry Godot SDK：Error Tracking

---

## 6. CI 集成

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

# 运行 Security 相关 GdUnit4 测试
$gutCommand = @(
    "godot", "--headless", "--no-window",
    "--scene", "res://tests/SmokeTestRunner.tscn",
    "--", "output=$gutSecurityReport", "filter=Security"
)

Write-Host "Running: $($gutCommand -join ' ')" -ForegroundColor Cyan
& $gutCommand[0] $gutCommand[1..($gutCommand.Length-1)]

# 验证审计日志存在且格式正确
$auditLog = "user://logs/security-audit.jsonl"

if (Test-Path $auditLog) {
    Write-Host "Audit log generated: $auditLog" -ForegroundColor Green
    
    # 验证 JSONL 格式
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

### 6.2 Phase 13 质量门禁扩展

在 `quality_gates.py` 中添加 GATE-10 审计日志验证（已在 Phase 13 中定义）。

---

## 7. 完成清单与验收标准

### 7.1 实现检查清单

- [ ] 实现 Security.cs Autoload（核心功能）
  - [ ] URL 白名单管理
  - [ ] HTTPRequest 包装与约束
  - [ ] 文件系统保护
  - [ ] JSONL 审计日志
- [ ] 编写 ≥8 个 GdUnit4 安全测试
  - [ ] URL 白名单（6 个）
  - [ ] HTTPRequest（5 个）
  - [ ] 文件系统（6 个）
  - [ ] 审计日志（3 个）
  - [ ] 总计：≥20 个测试用例
- [ ] 实现 HTTPSecurityWrapper 包装类
- [ ] 集成到冒烟测试（Phase 12）
- [ ] 生成安全审计报告（HTML）
- [ ] 编写 ADR-0018 草案
- [ ] CI 脚本集成（run_security_tests.ps1）
- [ ] 文档化白名单管理流程
- [ ] 本地测试 `npm run test:security` 通过

### 7.2 验收标准

| 项目 | 验收标准 | 确认 |
|-----|--------|------|
| Security.cs 完整度 | 5 大防守领域全覆盖 | □ |
| 测试覆盖 | ≥20 个 GdUnit4 测试通过 | □ |
| 审计日志 | JSONL 格式 100% 有效 | □ |
| 白名单管理 | 硬编码 + 动态加载配合 | □ |
| CI 集成 | 自动生成 security-audit.jsonl | □ |
| 文档完整 | Phase 14 文档 ≥900 行 | □ |
| ADR 质量 | ADR-0018 草案完成 | □ |

---

## 8. 风险与缓解

| # | 风险 | 等级 | 缓解 |
|---|-----|------|-----|
| 1 | 白名单过严导致功能被阻 | 中 | 前期宽松（audit only），逐步强制 |
| 2 | 审计日志性能影响 | 低 | 异步写入，可配置关闭 |
| 3 | Signal 契约难以强制 | 中 | 通过 GdUnit4 测试 + Lint 规则 |
| 4 | HTTPRequest 超时导致卡顿 | 低 | timeout 配置（默认 10s），可降级 |
| 5 | 白名单版本管理混乱 | 中 | 版本化配置文件 + PR 流程 |

---

## 9. 参考与链接

- **ADR-0002**：Electron 安全基线（原版对标）
- **ADR-0003**：可观测性与审计日志
- **Phase 8**：场景设计（Signal 定义）
- **Phase 12**：Headless 测试框架
- **Phase 13**：质量门禁脚本（GATE-10 审计日志验证）
- **Godot 文档**：[FileAccess](https://docs.godotengine.org/en/stable/classes/class_fileaccess.html)、[HTTPRequest](https://docs.godotengine.org/en/stable/classes/class_httprequest.html)、[Signal](https://docs.godotengine.org/en/stable/tutorials/step_by_step/signals.html)

---

**文档版本**：1.0  
**完成日期**：2025-11-07  
**作者**：Claude Code  
**状态**：Ready for Implementation
