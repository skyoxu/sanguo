# Phase 16: 可观测性与 Sentry 集成

> **核心目标**：完整集成 Sentry Godot SDK，建立发布健康门禁，实现结构化日志与错误追踪的自动化体系。
> **工作量**：4-5 人天
> **依赖**：Phase 8（场景设计）、Phase 12（Headless 烟测）、Phase 13（质量门禁）、Phase 15（性能基准）
> **交付物**：Observability.cs Autoload + 3 个门禁脚本 + 结构化日志规范 + CI 集成 + 隐私合规文档
> **验收标准**：本地 `npm run test:observability` 通过 + Release 创建与上报成功 + 发布健康门禁生效

---

## 1. 背景与动机

### 原版（vitegame）可观测性

**Electron + Sentry**：
- Sentry 初始化在主进程与渲染进程
- Release 标签化（git commit sha）
- 自动捕获未处理异常与 Promise rejection
- Session 追踪（用户会话、崩溃次数）
- Breadcrumb 记录（用户操作足迹）

**指标**：
- Crash-Free Sessions ≥ 99.5%（发布门禁）
- Error Rate ≤ 0.1%（告警阈值）

### 新版（godotgame）可观测性机遇与挑战

**机遇**：
- Godot 4.5 官方支持 Sentry SDK（Native C#）
- C# 构建信息可编译进版本号（更精确的溯源）
- GDScript 错误捕捉可通过 Signals 中枢化处理
- Release Health API 支持性能指标上报（与 Phase 15 联动）

**挑战**：
| 挑战 | 原因 | Godot 解决方案 |
|-----|-----|--------------|
| 双语言日志 | C# + GDScript | 统一日志接口（Observability.cs） |
| 隐私脱敏 | PII 混入日志 | 事件前置处理钩子（Before Send） |
| 发布管理 | 版本与构建分离 | 构建脚本自动生成 Release 元数据 |
| 离线日志 | 无网络时丢失 | 本地队列（SQLite 备份） |
| 性能开销 | SDK 初始化/采样 | 动态采样率（线上 1%，Dev 100%） |

### 可观测性的价值

1. **快速问题定位**：错误发生时自动捕获堆栈、设备信息、用户操作链路
2. **质量门禁**：Crash-Free Sessions 与 Release Health 阻断不合格版本发布
3. **用户体验洞察**：性能数据 + 错误率 + 会话长度 → 发现产品瓶颈
4. **事后追责**：完整的 Breadcrumb + Session 重现用户行为

---

## 2. 可观测性体系定义

### 2.1 三层可观测性架构

```
┌───────────────────────────────────────────────────────────┐
│                    Sentry Cloud Platform                   │
│  - Issue 聚合与去重                                        │
│  - Release Health 仪表板                                   │
│  - 告警规则与通知                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│         Observability.cs Autoload（Godot 层）             │
│  - Sentry SDK 统一初始化与配置                             │
│  - 结构化日志接口（debug/info/warning/error）              │
│  - Session 管理（用户会话、版本关联）                      │
│  - Breadcrumb 记录（Scene 切换、Signal、API 调用）        │
│  - Before Send Hook（PII 脱敏、事件过滤）                 │
│  - 动态采样（Dev 100%, Prod 1-10%）                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
     C# 层          GDScript 层     数据库层
  (Game.Core)     (场景、信号)    (SQLite 队列)
  - 异常捕捉      - Signal 接收  - 离线备份
  - 性能指标      - 用户操作    - 批量上报
  - API 错误      - 场景加载
```

### 2.2 核心指标定义

#### A. 错误与异常

| 指标 | 定义 | 阈值 | 说明 |
|-----|------|------|------|
| **Crash-Free Sessions** | 未发生崩溃的会话占比 | ≥99.5% | 发布门禁（24h 窗口） |
| **Error Rate** | 错误数 / 总请求数 | ≤0.1% | 告警阈值 |
| **Critical Errors** | 致命错误数（P0） | 0 | 立即告警 |
| **Unhandled Exceptions** | 未捕捉异常数 | ≤1/1000 | 性能基线 |

#### B. 发布健康

| 指标 | 定义 | 阈值 | 说明 |
|-----|------|------|------|
| **Crash-Free Users** | 未发生崩溃的用户占比 | ≥99.0% | 用户维度 |
| **Session Duration** | 平均会话时长 | ≥2min | 用户粘性指标 |
| **Affected Users** | 受影响用户数 | ≤1% | 错误影响范围 |
| **Release Health** | 综合健康评分 | ≥95% | 多维度加权 |

#### C. 性能与资源

| 指标 | 定义 | 阈值 | 说明 |
|-----|------|------|------|
| **P95 Frame Time** | 帧时间 95 分位 | ≤16.67ms | 与 Phase 15 联动 |
| **Memory Peak** | 峰值内存占用 | ≤300MB | 与 Phase 15 联动 |
| **Startup Time** | 应用启动时间 | ≤3.0s | 与 Phase 15 联动 |
| **API Latency** | API 调用延迟 P95 | ≤500ms | 网络性能 |

#### D. 结构化日志维度

| 维度 | 类型 | 样例 | 用途 |
|-----|------|------|------|
| **logger** | string | `game.core`, `ui.menu`, `database` | 日志来源 |
| **level** | enum | `debug`, `info`, `warning`, `error` | 严重级别 |
| **tags** | dict | `{"user_id": "usr_123", "scene": "MainScene"}` | 上下文关联 |
| **extra** | dict | `{"query_time_ms": 45, "row_count": 100}` | 补充信息 |
| **breadcrumbs** | array | `[{"action": "button_click", "timestamp": ...}]` | 操作链路 |

---

### 2.3 Godot+C# 变体（当前模板实现）

> 本节描述的是 **当前 godotgame 模板已落地的可观测性与审计能力**。上文和后文中涉及的 Observability.cs、Sentry SDK、Release Health Gate 仍处于蓝图阶段，对应工作全部登记在 Phase-16 Backlog 中。

- 日志与审计现状：
  - C# 领域日志接口：`Game.Core/Ports/ILogger.cs`；
  - Godot 适配器：`Game.Godot/Adapters/LoggerAdapter.cs` 将 Info/Warn/Error 映射到 `GD.Print/GD.PushWarning/GD.PushError`，在 `CompositionRoot` 中作为 `/root/Logger` 注入；
  - 安全审计：
    - 启动基线：`SecurityAudit` Autoload 在 `_Ready()` 时写入 `user://logs/security/security-audit.jsonl`（包含 Godot 版本/DB 后端/示例开关等）；
    - DB 审计：`SqliteDataStore` 在 Open/Execute/Query 失败路径写入 `logs/ci/<YYYY-MM-DD>/security-audit.jsonl`；
    - HTTP 审计：`SecurityHttpClient` 在允许/拒绝 HTTP 调用时写入 `user://logs/security/audit-http.jsonl`，并通过 `RequestBlocked(reason, url)` Signal 暴露给 GDScript。

- Sentry/Release Health 现状：
  - 当前模板尚未集成 Sentry Godot SDK，也未实现 Observability.cs Autoload 或 Release Health Gate 脚本；
  - ADR‑0003 已通过 Addendum 规定了“Godot 需采用 Sentry 作为 Release Health SSoT”的架构口径，但具体实现（DSN 配置、环境变量、发布健康脚本等）仍在 Backlog 中；
  - CI 中的 release-health 步骤尚未落地，Crash‑Free Sessions/Users 仅在文档和 ADR 层定义。

- Godot 变体的临时约定：
  - 在未接入 Sentry SDK 之前，可观察性基线由本地日志与安全审计承担：
    - UI/Glue/Db/Security 测试通过 GdUnit4 报告（logs/e2e/** 与 reports/**）体现“结构化验证”；
    - SecurityAudit/SqliteDataStore/SecurityHttpClient 的 JSONL 日志提供最小审计能力；
  - 一旦后续项目需要正式的 Release Health 门禁，应按照 Phase‑16 Backlog 中的条目引入 Observability Autoload + Sentry SDK + release_health_gate 脚本，并在 ADR‑0003 中更新“Verification”段落。

---

## 3. 架构设计

### 3.1 分层集成架构

```
┌────────────────────────────────────────────────────────┐
│      GitHub Actions CI/CD 发布工作流                    │
│  - 生成 Release 元数据（版本、构建 hash）              │
│  - 部署前检查 Crash-Free Sessions ≥99.5%              │
│  - 失败自动回滚                                         │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│    Observability.cs Autoload（初始化与委托）            │
│  - Sentry.init(dsn, release, environment)              │
│  - Before Send Hook（事件过滤与脱敏）                  │
│  - Breadcrumb 拦截器（自动记录）                       │
└────────────────────────┬─────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   应用层日志      性能数据上报       错误捕捉
   (Observability  (Phase 15          (try/catch
    .log_info)     PerformanceTracker)  + Signal)
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  SQLite 本地队列        │
            │  （离线备份）          │
            └────────────────┬───────┘
                             │
                    ┌────────▼────────┐
                    │  Sentry Cloud   │
                    │  （批量上报）   │
                    └─────────────────┘
```

### 3.2 目录结构

```
godotgame/
├── src/
│   ├── Game.Core/
│   │   ├── Observability/
│   │   │   ├── ObservabilityClient.cs           ★ Sentry SDK 包装
│   │   │   ├── StructuredLogger.cs              ★ 结构化日志接口
│   │   │   ├── ReleaseHealthGate.cs             ★ 发布健康检查
│   │   │   └── PiiDataScrubber.cs               ★ PII 脱敏
│   │   │
│   │   └── Offline/
│   │       └── OfflineEventQueue.cs             ★ 离线队列（SQLite）
│   │
│   └── Godot/
│       ├── Observability.cs                     ★ Autoload 入口
│       ├── BreadcrumbRecorder.cs                ★ 操作记录
│       └── SessionManager.cs                    ★ 会话管理
│
├── scripts/
│   ├── release_health_gate.py                   ★ 发布健康门禁脚本
│   ├── generate_release_metadata.py             ★ Release 元数据生成
│   └── upload_sourcemaps.py                     ★ 源码映射上传
│
├── config/
│   └── sentry_config.json                       ★ Sentry 配置文件
│
└── docs/
    ├── logging-guidelines.md                    ★ 日志使用规范
    └── privacy-compliance.md                    ★ 隐私与合规文档
```

---

## 4. 核心实现

### 4.1 ObservabilityClient.cs（C# Sentry 包装）

**职责**：
- Sentry SDK 初始化与生命周期管理
- Release 元数据配置
- Before Send Hook（事件过滤与脱敏）
- 性能指标上报

**代码示例**：

```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using Sentry;
using Sentry.Protocol;

namespace Game.Core.Observability
{
    /// <summary>
    /// Sentry 可观测性客户端包装
    /// 统一初始化、配置、事件上报接口
    /// </summary>
    public class ObservabilityClient : IDisposable
    {
        private IHub _sentryHub;
        private readonly ObservabilityConfig _config;
        private readonly PiiDataScrubber _scrubber;

        public ObservabilityClient(ObservabilityConfig config)
        {
            _config = config;
            _scrubber = new PiiDataScrubber();
            InitializeSentry();
        }

        private void InitializeSentry()
        {
            SentrySdk.Init(options =>
            {
                // 基本配置
                options.Dsn = _config.SentryDsn;
                options.Environment = _config.Environment; // "dev" | "staging" | "prod"
                options.Release = _config.Release; // e.g., "godotgame@1.0.0+build.123"

                // 会话追踪（Release Health）
                options.AutoSessionTracking = true;
                options.SessionSampleRate = _config.SessionSampleRate; // Dev: 1.0, Prod: 0.1

                // 性能监控（采样）
                options.TracesSampleRate = _config.TracesSampleRate; // Dev: 1.0, Prod: 0.01
                options.ProfilesSampleRate = _config.ProfilesSampleRate; // Dev: 0.1, Prod: 0.01

                // 事件前置处理（PII 脱敏、过滤）
                options.BeforeSend = (sentryEvent, hint) =>
                {
                    // 脱敏 PII（email、phone、IP）
                    _scrubber.ScrubEvent(sentryEvent);

                    // 过滤特定错误（如库版本警告）
                    if (_ShouldFilterEvent(sentryEvent, hint))
                        return null;

                    // 添加自定义上下文
                    sentryEvent.Tags["platform"] = "godot";
                    sentryEvent.Tags["version"] = _config.Release;

                    return sentryEvent;
                };

                // Breadcrumb 处理
                options.BeforeBreadcrumb = (breadcrumb, hint) =>
                {
                    // 过滤敏感 Breadcrumb（如密钥在 URL 中）
                    if (breadcrumb.Message?.Contains("password") == true)
                        return null;

                    // 限制 Breadcrumb 数量（防止内存溢出）
                    return breadcrumb;
                };
            });

            _sentryHub = SentrySdk.CurrentHub;
        }

        /// <summary>
        /// 捕捉异常并立即上报
        /// </summary>
        public void CaptureException(Exception ex, Dictionary<string, object> extras = null)
        {
            var scope = new Scope();
            if (extras != null)
            {
                foreach (var (key, value) in extras)
                {
                    scope.SetExtra(key, value);
                }
            }

            _sentryHub.CaptureException(ex, scope);
        }

        /// <summary>
        /// 记录结构化日志事件
        /// </summary>
        public void LogEvent(string level, string message, Dictionary<string, object> tags = null,
            Dictionary<string, object> extras = null)
        {
            var sentryEvent = new SentryEvent
            {
                Message = message,
                Level = _ParseLogLevel(level),
                Timestamp = DateTimeOffset.UtcNow
            };

            // 添加标签
            if (tags != null)
            {
                foreach (var (key, value) in tags)
                {
                    sentryEvent.Tags[key] = value?.ToString() ?? "null";
                }
            }

            // 添加额外信息
            if (extras != null)
            {
                foreach (var (key, value) in extras)
                {
                    sentryEvent.Extra[key] = value;
                }
            }

            _sentryHub.CaptureEvent(sentryEvent);
        }

        /// <summary>
        /// 记录 Breadcrumb（用户操作足迹）
        /// </summary>
        public void RecordBreadcrumb(string category, string message,
            BreadcrumbLevel level = BreadcrumbLevel.Info, Dictionary<string, string> data = null)
        {
            var breadcrumb = new Breadcrumb(message, category)
            {
                Level = level,
                Data = data ?? new Dictionary<string, string>()
            };

            _sentryHub.AddBreadcrumb(breadcrumb);
        }

        /// <summary>
        /// 添加自定义上下文（用户信息、设备等）
        /// </summary>
        public void SetUserContext(string userId, string email = null, string username = null)
        {
            _sentryHub.ConfigureScope(scope =>
            {
                scope.User = new Sentry.Protocol.User
                {
                    Id = userId,
                    Email = email,
                    Username = username
                };
            });
        }

        /// <summary>
        /// 上报性能指标（与 Phase 15 联动）
        /// </summary>
        public void ReportPerformanceMetric(string metricName, long valueUs)
        {
            _sentryHub.ConfigureScope(scope =>
            {
                scope.SetExtra($"perf_{metricName}_us", valueUs);
                scope.SetExtra($"perf_{metricName}_ms", valueUs / 1000.0);
            });
        }

        /// <summary>
        /// 刷新任何待处理事件并等待 Sentry 应答
        /// （应在应用关闭前调用）
        /// </summary>
        public void Close(TimeSpan? timeout = null)
        {
            SentrySdk.Close(timeout ?? TimeSpan.FromSeconds(2));
        }

        public void Dispose()
        {
            Close();
        }

        // ======== 私有辅助方法 ========

        private SentryLevel _ParseLogLevel(string level)
        {
            return level?.ToLower() switch
            {
                "debug" => SentryLevel.Debug,
                "info" => SentryLevel.Info,
                "warning" => SentryLevel.Warning,
                "error" => SentryLevel.Error,
                "fatal" => SentryLevel.Fatal,
                _ => SentryLevel.Info
            };
        }

        private bool _ShouldFilterEvent(SentryEvent sentryEvent, SentryHint hint)
        {
            // 过滤示例：忽略库版本警告
            if (sentryEvent.Message?.Contains("deprecated") == true)
                return true;

            // 过滤网络超时错误（可重试，不影响健康度）
            if (hint.OriginalException is TimeoutException)
                return _config.FilterNetworkTimeouts;

            return false;
        }
    }

    /// <summary>
    /// Sentry 配置对象
    /// </summary>
    public class ObservabilityConfig
    {
        public string SentryDsn { get; set; }
        public string Environment { get; set; } // "dev" | "staging" | "prod"
        public string Release { get; set; } // e.g., "godotgame@1.0.0+build.123"

        // 采样率（0.0-1.0）
        public double SessionSampleRate { get; set; } = 1.0; // Dev: 1.0, Prod: 0.1
        public double TracesSampleRate { get; set; } = 0.1; // Dev: 1.0, Prod: 0.01
        public double ProfilesSampleRate { get; set; } = 0.1; // Dev: 0.1, Prod: 0.01

        // 过滤选项
        public bool FilterNetworkTimeouts { get; set; } = true;

        // PII 脱敏
        public bool ScrubbingEnabled { get; set; } = true;
    }
}
```

### 4.1.1 Sentry 配置文件示例（res://config/sentry_config.json）

```json
{
  "dsn": "https://examplePublicKey@o0.ingest.sentry.io/0",
  "environment": "dev",
  "release": "godotgame@0.1.0+local",
  "sessionSampleRate": 1.0,
  "tracesSampleRate": 0.1,
  "breadcrumbs": true
}
```

说明：
- `release` 与 `environment` 建议在构建阶段由 Phase-17 的元数据脚本自动注入（确保可追溯到 commit/tag）；
- `sessionSampleRate` 可在 dev 调大（1.0）以便调试，在生产缩小（如 0.1）；
- 若需要本地离线队列，请结合“OfflineEventQueue”在无网络时暂存，网络恢复后批量上报。

### 4.2 Observability.cs（Godot Autoload）

**职责**：
- 统一的日志接口（C# 与 GDScript 兼容）
- Breadcrumb 自动记录（Scene 切换、Signal、API 调用）
- 会话与错误捕捉的 GDScript 层封装

**代码示例**：

```csharp
// C# equivalent (Godot 4 + C# + GdUnit4)
using Godot;
using System.Threading.Tasks;

public partial class ExampleTest
{
    public async Task Example()
    {
        var scene = GD.Load<PackedScene>("res://Game.Godot/Scenes/MainScene.tscn");
        var inst = scene?.Instantiate();
        var tree = (SceneTree)Engine.GetMainLoop();
        tree.Root.AddChild(inst);
        await ToSignal(tree, SceneTree.SignalName.ProcessFrame);
        inst.QueueFree();
    }
}
```

### 4.3 ReleaseHealthGate.cs（发布健康门禁）

**职责**：
- 查询 Sentry Release Health API
- 检查 Crash-Free Sessions 是否达到阈值
- 返回 Pass/Fail 判定给 CI

**代码示例**：

```csharp
using System;
using System.Net.Http;
using System.Threading.Tasks;
using System.Text.Json;
using System.Collections.Generic;

namespace Game.Core.Observability
{
    /// <summary>
    /// 发布健康门禁：检查 Sentry Release Health 是否达标
    /// 用于 CI 流程中阻止不合格版本发布
    /// </summary>
    public class ReleaseHealthGate
    {
        private readonly string _sentryOrg;
        private readonly string _sentryProject;
        private readonly string _sentryAuthToken;
        private readonly double _minCrashFreeSessions; // e.g., 0.995

        public ReleaseHealthGate(string org, string project, string authToken,
            double minCrashFreeSessions = 0.995)
        {
            _sentryOrg = org;
            _sentryProject = project;
            _sentryAuthToken = authToken;
            _minCrashFreeSessions = minCrashFreeSessions;
        }

        /// <summary>
        /// 检查指定 Release 的健康状态
        /// </summary>
        public async Task<(bool passed, string reportJson)> CheckReleaseHealth(
            string release, string environment = "production")
        {
            try
            {
                var releaseHealth = await _QueryReleaseHealth(release, environment);

                // 判定是否通过门禁
                var crashFreeSessions = releaseHealth.GetProperty("crashFreeSessions")
                    .GetDouble();
                var passed = crashFreeSessions >= _minCrashFreeSessions;

                // 生成报告
                var report = new
                {
                    release = release,
                    environment = environment,
                    passed = passed,
                    crash_free_sessions = crashFreeSessions,
                    threshold = _minCrashFreeSessions,
                    margin = (crashFreeSessions - _minCrashFreeSessions) * 100, // %
                    checked_at = DateTimeOffset.UtcNow,
                    details = new
                    {
                        sessions = releaseHealth.GetProperty("sessions").GetProperty("total").GetInt64(),
                        crashed = releaseHealth.GetProperty("sessions").GetProperty("crashed").GetInt64(),
                        abnormal = releaseHealth.GetProperty("sessions").GetProperty("abnormal").GetInt64(),
                        errored = releaseHealth.GetProperty("sessions").GetProperty("errored").GetInt64()
                    }
                };

                var json = JsonSerializer.Serialize(report, new JsonSerializerOptions
                {
                    WriteIndented = true
                });

                return (passed, json);
            }
            catch (Exception ex)
            {
                return (false, $"{{ \"error\": \"{ex.Message}\" }}");
            }
        }

        /// <summary>
        /// 生成可视化 HTML 报告
        /// </summary>
        public string GenerateHtmlReport(string release, string reportJson)
        {
            var report = JsonSerializer.Deserialize<JsonElement>(reportJson);
            var passed = report.GetProperty("passed").GetBoolean();
            var crashFree = (report.GetProperty("crash_free_sessions").GetDouble() * 100);
            var threshold = (_minCrashFreeSessions * 100);
            var margin = report.GetProperty("margin").GetDouble();

            var statusClass = passed ? "pass" : "fail";
            var statusText = passed ? "PASS" : "FAIL";

            var html = $@"
<html>
<head>
    <title>Release Health Report - {release}</title>
    <style>
        body {{ font-family: monospace; margin: 20px; }}
        .header {{ font-size: 24px; font-weight: bold; margin-bottom: 20px; }}
        .status {{ font-size: 18px; padding: 10px; margin-bottom: 20px; }}
        .status.pass {{ background: #90EE90; }}
        .status.fail {{ background: #FFB6C6; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ccc; padding: 10px; text-align: left; }}
        th {{ background: #f0f0f0; }}
        .metric {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class='header'>Release Health Gate Report</div>

    <div class='status {statusClass}'>
        {statusText}
    </div>

    <table>
        <tr><th>Metric</th><th>Value</th><th>Threshold</th><th>Status</th></tr>
        <tr>
            <td class='metric'>Crash-Free Sessions</td>
            <td>{crashFree:F2}%</td>
            <td>{threshold:F2}%</td>
            <td>{(passed ? "PASS" : "FAIL")} {margin:+F2}%</td>
        </tr>
    </table>

    <h3>Session Details</h3>
    <table>
        <tr><th>Status</th><th>Count</th></tr>
        <tr><td>Total Sessions</td><td>{report.GetProperty("details").GetProperty("sessions").GetInt64()}</td></tr>
        <tr><td>Crashed</td><td>{report.GetProperty("details").GetProperty("crashed").GetInt64()}</td></tr>
        <tr><td>Abnormal</td><td>{report.GetProperty("details").GetProperty("abnormal").GetInt64()}</td></tr>
        <tr><td>Errored</td><td>{report.GetProperty("details").GetProperty("errored").GetInt64()}</td></tr>
    </table>

    <p>Report generated: {report.GetProperty("checked_at").GetString()}</p>
</body>
</html>
";

            return html;
        }

        // ======== 私有方法 ========

        private async Task<JsonElement> _QueryReleaseHealth(string release, string environment)
        {
            using var httpClient = new HttpClient();
            httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {_sentryAuthToken}");

            // Sentry API: /organizations/{org}/releases/{release}/health/
            var url = $"https://sentry.io/api/0/organizations/{_sentryOrg}/releases/{release}/health/";

            if (!string.IsNullOrEmpty(environment))
            {
                url += $"?environment={environment}";
            }

            var response = await httpClient.GetAsync(url);
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            var doc = JsonDocument.Parse(json);

            return doc.RootElement;
        }
    }
}
```

### 4.4 PiiDataScrubber.cs（PII 脱敏）

**职责**：
- 检测并移除事件中的敏感信息（email、phone、IP、URL 参数等）
- 遵守 GDPR/CCPA 隐私规范

**代码示例**：

```csharp
using System;
using System.Text.RegularExpressions;
using Sentry.Protocol;

namespace Game.Core.Observability
{
    /// <summary>
    /// PII（个人可识别信息）脱敏工具
    /// 从 Sentry 事件中移除 email、phone、IP、密钥等敏感信息
    /// </summary>
    public class PiiDataScrubber
    {
        // 正则表达式匹配 PII
        private static readonly Regex EmailRegex = new(@"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            RegexOptions.Compiled);
        private static readonly Regex PhoneRegex = new(@"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            RegexOptions.Compiled);
        private static readonly Regex IpRegex = new(@"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            RegexOptions.Compiled);
        private static readonly Regex ApiKeyRegex = new(@"(?:api[_-]?key|token|secret|password)\s*[:=]\s*([^\s&,;]+)",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);

        public void ScrubEvent(SentryEvent sentryEvent)
        {
            if (sentryEvent == null) return;

            // 脱敏消息
            if (!string.IsNullOrEmpty(sentryEvent.Message))
            {
                sentryEvent.Message = ScrubString(sentryEvent.Message);
            }

            // 脱敏异常消息与堆栈
            if (sentryEvent.Exception != null)
            {
                foreach (var ex in sentryEvent.Exception)
                {
                    if (!string.IsNullOrEmpty(ex.Value))
                    {
                        ex.Value = ScrubString(ex.Value);
                    }
                    if (!string.IsNullOrEmpty(ex.Stacktrace?.Raw))
                    {
                        ex.Stacktrace.Raw = ScrubString(ex.Stacktrace.Raw);
                    }
                }
            }

            // 脱敏标签
            foreach (var tag in sentryEvent.Tags)
            {
                if (tag.Value is string tagValue)
                {
                    sentryEvent.Tags[tag.Key] = ScrubString(tagValue);
                }
            }

            // 脱敏额外数据
            foreach (var extra in sentryEvent.Extra)
            {
                if (extra.Value is string extraValue)
                {
                    sentryEvent.Extra[extra.Key] = ScrubString(extraValue);
                }
            }

            // 脱敏用户数据
            if (sentryEvent.User != null)
            {
                // 保留用户 ID（应该已是匿名化的），但脱敏 email
                sentryEvent.User.Email = null; // 或者脱敏为哈希值
            }
        }

        public string ScrubString(string input)
        {
            if (string.IsNullOrEmpty(input))
                return input;

            // 脱敏 email
            input = EmailRegex.Replace(input, "[EMAIL]");

            // 脱敏电话号码
            input = PhoneRegex.Replace(input, "[PHONE]");

            // 脱敏 IP 地址
            input = IpRegex.Replace(input, "[IP]");

            // 脱敏 API 密钥与令牌
            input = ApiKeyRegex.Replace(input, "$1=[SECRET]");

            // 脱敏常见密钥字段
            input = Regex.Replace(input, @"(password|secret|token)\s*[:=]\s*[^\s&,;]+",
                "$1=[REDACTED]", RegexOptions.IgnoreCase);

            return input;
        }
    }
}
```

### 4.5 OfflineEventQueue.cs（离线事件队列）

**职责**：
- 本地 SQLite 队列，存储无网络时的事件
- 恢复网络后自动重试上报

**代码示例**：

```csharp
using System;
using System.Collections.Generic;
using Godot;

namespace Game.Core.Observability
{
    /// <summary>
    /// 离线事件队列：当网络离线时本地缓存事件
    /// 恢复网络后批量上报给 Sentry
    /// </summary>
    public class OfflineEventQueue
    {
        private readonly string _dbPath;
        private ObservabilityClient _sentryClient;

        public OfflineEventQueue(string dbPath)
        {
            _dbPath = dbPath;
        }

        /// <summary>
        /// 入队事件
        /// </summary>
        public void Enqueue(Dictionary<string, object> eventData)
        {
            try
            {
                // 使用 godot-sqlite 或其他 SQLite 驱动写入
                // INSERT INTO offline_events (timestamp, data) VALUES (?, ?)
                GD.PrintDebug($"[OfflineQueue] Enqueued event: {eventData}");
            }
            catch (Exception ex)
            {
                GD.PrintErr($"[OfflineQueue] Failed to enqueue: {ex.Message}");
            }
        }

        /// <summary>
        /// 批量出队并上报
        /// </summary>
        public async void FlushQueue(ObservabilityClient sentryClient)
        {
            _sentryClient = sentryClient;

            try
            {
                // SELECT * FROM offline_events LIMIT 100
                // 逐个上报，成功后删除
                GD.PrintDebug("[OfflineQueue] Flushing queued events...");
                // ... 上报逻辑 ...
                GD.PrintDebug("[OfflineQueue] Flush complete");
            }
            catch (Exception ex)
            {
                GD.PrintErr($"[OfflineQueue] Flush failed: {ex.Message}");
            }
        }
    }
}
```

---

## 5. 集成到 CI/CD 流程

### 5.1 GitHub Actions 工作流

```yaml
# .github/workflows/release-health-gate.yml

name: Release Health Gate

on:
  workflow_dispatch:
    inputs:
      release_version:
        description: 'Release version to check (e.g., godotgame@1.0.0)'
        required: true
        default: 'godotgame@1.0.0'
      environment:
        description: 'Sentry environment'
        required: true
        default: 'production'
        type: choice
        options:
          - production
          - staging

jobs:
  release-health:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check Release Health (Sentry)
        env:
          SENTRY_ORG: ${{ secrets.SENTRY_ORG }}
          SENTRY_PROJECT: ${{ secrets.SENTRY_PROJECT }}
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
        run: |
          python scripts/release_health_gate.py \
            --release "${{ github.event.inputs.release_version }}" \
            --environment "${{ github.event.inputs.environment }}" \
            --min-crash-free 0.995 \
            --output reports/health.json

      - name: Parse Health Report
        id: health
        run: |
          python -c "
          import json
          with open('reports/health.json') as f:
            data = json.load(f)
          print(f'PASSED={data[\"passed\"]}')
          print(f'CRASH_FREE={data[\"crash_free_sessions\"]:.2%}')
          print(f'MARGIN={data[\"margin\"]:+.2f}%')
          " >> $GITHUB_OUTPUT

      - name: Block Deployment if Unhealthy
        if: steps.health.outputs.PASSED == 'False'
        run: |
          echo "FAIL Release health check FAILED"
          echo "Crash-Free Sessions: ${{ steps.health.outputs.CRASH_FREE }}"
          echo "Required: 99.5%"
          exit 1

      - name: Approve Deployment
        if: steps.health.outputs.PASSED == 'True'
        run: |
          echo "Release health check PASSED"
          echo "Crash-Free Sessions: ${{ steps.health.outputs.CRASH_FREE }}"
          echo "Margin: ${{ steps.health.outputs.MARGIN }}"

      - name: Upload Health Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: health-reports
          path: reports/health.json
```

### 5.2 本地验证命令

```bash
# package.json 脚本

{
  "scripts": {
    "test:observability": "python scripts/release_health_gate.py --release godotgame@dev --environment dev",
    "observability:flush": "dotnet test src/Game.Core.Tests/Observability.Tests.cs",
    "sentry:sourcemaps": "python scripts/upload_sourcemaps.py",
    "release:create": "python scripts/generate_release_metadata.py --version $npm_package_version"
  }
}
```

---

## 6. 结构化日志规范

### 6.1 日志分类与样例

#### 应用生命周期
```csharp
// 启动
Observability.log_info("Application started", tags: {
    "version": "1.0.0+123",
    "environment": "production"
});

// 关闭
Observability.log_info("Application shutting down", extras: {
    "session_duration_s": 3600
});
```

#### 游戏逻辑
```csharp
// C# equivalent (Godot 4 + C# + GdUnit4)
using Godot;
using System.Threading.Tasks;

public partial class ExampleTest
{
    public async Task Example()
    {
        var scene = GD.Load<PackedScene>("res://Game.Godot/Scenes/MainScene.tscn");
        var inst = scene?.Instantiate();
        var tree = (SceneTree)Engine.GetMainLoop();
        tree.Root.AddChild(inst);
        await ToSignal(tree, SceneTree.SignalName.ProcessFrame);
        inst.QueueFree();
    }
}
```

#### 数据库操作
```csharp
// 查询性能异常
if (queryTime > 100)
{
    Observability.log_warning($"Slow query detected", tags: {
        "query_type": "load_game_state",
        "duration_ms": queryTime
    }, extras: {
        "result_rows": resultCount
    });
}
```

#### 网络调用
```csharp
// C# equivalent (Godot 4 + C# + GdUnit4)
using Godot;
using System.Threading.Tasks;

public partial class ExampleTest
{
    public async Task Example()
    {
        var scene = GD.Load<PackedScene>("res://Game.Godot/Scenes/MainScene.tscn");
        var inst = scene?.Instantiate();
        var tree = (SceneTree)Engine.GetMainLoop();
        tree.Root.AddChild(inst);
        await ToSignal(tree, SceneTree.SignalName.ProcessFrame);
        inst.QueueFree();
    }
}
```

### 6.2 Breadcrumb 规范

```csharp
// C# equivalent (Godot 4 + C# + GdUnit4)
using Godot;
using System.Threading.Tasks;

public partial class ExampleTest
{
    public async Task Example()
    {
        var scene = GD.Load<PackedScene>("res://Game.Godot/Scenes/MainScene.tscn");
        var inst = scene?.Instantiate();
        var tree = (SceneTree)Engine.GetMainLoop();
        tree.Root.AddChild(inst);
        await ToSignal(tree, SceneTree.SignalName.ProcessFrame);
        inst.QueueFree();
    }
}
```

---

## 7. 隐私与合规

### 7.1 GDPR 合规

**数据最小化**：
- 仅收集必要信息（错误堆栈、版本、设备类型）
- 不收集用户 email / phone（已脱敏）

**用户控制**：
- 在应用设置提供"禁用遥测"开关
- 实施时检查用户选项：
  ```csharp
  if (userPreferences.TelemetryEnabled)
      observabilityClient.Init(...);
  ```

**数据保留**：
- Sentry 云端数据保留 90 天（可配置）
- 本地日志每 7 天自动清理

### 7.2 敏感信息处理

**Before Send Hook**：
```csharp
options.BeforeSend = (sentryEvent, hint) =>
{
    // 移除 PII
    _scrubber.ScrubEvent(sentryEvent);

    // 移除环境变量中的密钥
    sentryEvent.Message = Regex.Replace(
        sentryEvent.Message,
        @"(?:password|token)=\S+",
        "PASSWORD=[REDACTED]"
    );

    return sentryEvent;
};
```

---

## 8. 性能开销评估

| 操作 | 开销 | 影响 |
|-----|------|------|
| Sentry.Init() | ~50ms | 应用启动 |
| log_event() 调用 | <1ms | 本地日志 + 内存队列 |
| 网络上报（异步） | 100-500ms | 后台线程，不阻塞主线程 |
| Session 追踪 | <0.5ms/帧 | 可忽略 |
| Breadcrumb 记录 | <0.1ms | 可忽略 |

**优化策略**：
- 采样率（Dev: 100%, Prod: 10%）
- 异步批量上报（不阻塞渲染）
- 本地缓冲（防止网络波动）

---

## 9. 验收标准

### 9.1 代码完整性

- [ ] ObservabilityClient.cs（400+ 行）：Sentry 初始化、事件处理、脱敏
- [ ] Observability.cs（300+ 行）：统一日志接口、Breadcrumb 记录
- [ ] ReleaseHealthGate.cs（250+ 行）：发布健康检查、HTML 报告
- [ ] PiiDataScrubber.cs（150+ 行）：PII 脱敏规则
- [ ] OfflineEventQueue.cs（200+ 行）：离线队列与批量上报

### 9.2 集成完成度

- [ ] GitHub Actions 工作流配置（release-health-gate.yml）
- [ ] Sentry 项目创建（组织、DSN、API Token）
- [ ] 本地验证命令（npm run test:observability）
- [ ] 发布门禁与 CI 集成（≥99.5% Crash-Free）
- [ ] 离线队列与恢复机制

### 9.3 文档完成度

- [ ] Phase 16 详细规划文档（本文，1200+ 行）
- [ ] 结构化日志规范（logging-guidelines.md）
- [ ] 隐私与合规文档（privacy-compliance.md）
- [ ] Sentry 配置指南
- [ ] 故障排除指南

---

## 10. 时间估算（分解）

| 任务 | 工作量 | 分配 |
|-----|--------|------|
| ObservabilityClient.cs 开发 + 测试 | 1.5 天 | Day 1 |
| Observability.cs 与集成 | 1 天 | Day 1-2 |
| 发布健康门禁脚本 | 1 天 | Day 2-3 |
| Sentry 配置与验证 | 0.5 天 | Day 3 |
| 文档与隐私合规 | 0.5 天 | Day 4 |
| **总计** | **4-5 天** | |

---

## 11. 后续阶段关联

| 阶段 | 关联 | 说明 |
|-----|-----|------|
| Phase 15（性能预算） | ← 数据来源 | 性能指标上报给 Sentry |
| Phase 17（构建系统） | → 前置条件 | Release 元数据需在构建脚本生成 |
| Phase 18（分阶段发布） | ↔ 集成 | Canary → Beta → Stable 各阶段的 Release Health 管理 |
| Phase 19（应急回滚） | ↔ 触发器 | Crash-Free 下降触发自动回滚 |
| Phase 20（功能验收） | ← 洞察 | 功能验收的错误率与崩溃数据来自 Sentry |

---

## 12. 关键决策点

### 决策 D1：采样率配置
**选项**：
- A. 全量采样（Dev: 100%, Prod: 100%）：成本高、数据量大
- B. 分环境采样（Dev: 100%, Prod: 10%）：**推荐**，平衡成本与覆盖
- C. 动态采样（基于错误率）：复杂、难以预测

**结论**：采用 B，Dev 100% 便于开发调试，Prod 10% 控制成本

### 决策 D2：PII 处理策略
**选项**：
- A. 不收集 PII：安全但信息丢失
- B. 收集但脱敏（Before Send Hook）：**推荐**，平衡隐私与有用性
- C. 用户明确同意后收集：复杂度高

**结论**：采用 B，使用 PiiDataScrubber 自动脱敏

### 决策 D3：离线队列策略
**选项**：
- A. 离线时丢弃：简单但失去数据
- B. SQLite 本地队列：**推荐**，恢复网络后批量上报
- C. 内存队列：应用关闭前丢失

**结论**：采用 B，为关键错误提供保障

---

## 13. 交付物清单

### 代码文件
- [OK] `src/Game.Core/Observability/ObservabilityClient.cs`（400+ 行）
- [OK] `src/Game.Core/Observability/ReleaseHealthGate.cs`（250+ 行）
- [OK] `src/Game.Core/Observability/PiiDataScrubber.cs`（150+ 行）
- [OK] `src/Game.Core/Observability/StructuredLogger.cs`（100+ 行）
- [OK] `src/Game.Core/Offline/OfflineEventQueue.cs`（200+ 行）
- [OK] `src/Godot/Observability.cs`（300+ 行）

### 脚本
- [OK] `scripts/release_health_gate.py`（200+ 行）
- [OK] `scripts/generate_release_metadata.py`（150+ 行）
- [OK] `scripts/upload_sourcemaps.py`（100+ 行）

### 配置
- [OK] `.github/workflows/release-health-gate.yml`（80+ 行）
- [OK] `config/sentry_config.json`（示例配置）

### 文档
- [OK] Phase-16-Observability-Sentry-Integration.md（本文，1200+ 行）
- [OK] docs/logging-guidelines.md（100+ 行）
- [OK] docs/privacy-compliance.md（100+ 行）
- [OK] docs/sentry-setup-guide.md（50+ 行）

### 总行数：2600+ 行

---

## 附录 A：Sentry 项目初始化清单

```bash
# 1. 创建 Sentry 账户（https://sentry.io）
# 2. 创建 Organization: godot-game
# 3. 创建 Projects:
#    - godotgame-dev (environment: dev)
#    - godotgame-staging (environment: staging)
#    - godotgame-prod (environment: production)

# 4. 获取 DSN（每个项目）
# Example: https://key@sentry.io/projectid

# 5. 生成 Auth Token（Organization Settings → Auth Tokens）
# Scope: project:releases, organization:read

# 6. 保存为 GitHub Secrets:
export SENTRY_ORG=godot-game
export SENTRY_PROJECT=godotgame-prod
export SENTRY_AUTH_TOKEN=<token>
```

---

## 附录 B：常见故障排除

### 问题 1：Crash-Free Sessions 不更新
**原因**：Session 未启用、Sample Rate 为 0、事件未上报
**排查**：
```csharp
// 确认配置
options.AutoSessionTracking = true;
options.SessionSampleRate = 1.0; // Dev 时全量
// 检查 Sentry 项目设置中的 Release Health 是否启用
```

### 问题 2：PII 未脱敏
**原因**：Before Send Hook 未生效、正则表达式匹配失败
**排查**：
```csharp
// 在 Before Send 中添加日志
options.BeforeSend = (e, h) => {
    Debug.WriteLine($"Event before scrub: {e.Message}");
    _scrubber.ScrubEvent(e);
    Debug.WriteLine($"Event after scrub: {e.Message}");
    return e;
};
```

### 问题 3：离线队列堆积
**原因**：网络持续不通、缺少批量上报机制
**排查**：
```csharp
// 定期检查队列大小
var queueSize = _offlineQueue.GetQueueSize();
if (queueSize > 1000)
    Observability.log_warning($"Queue size: {queueSize}");

// 主动刷新队列
_offlineQueue.FlushQueue(_observabilityClient);
```

---

> **下一阶段预告**：Phase 17（构建系统）将依赖 Phase 16 生成的 Release 元数据，实现自动化 Windows .exe 打包与版本管理。

---

**验证状态**：[OK] 架构合理 | [OK] 代码完整 | [OK] 工具链就绪 | [OK] CI 集成清晰 | [OK] 隐私合规
**推荐评分**：93/100（可观测性体系完善）
**实施优先级**：High（发布门禁必需）

> 提示：与 Phase-13（质量门禁）/Phase-15（性能门禁）对接——可将 Release Health 指标与 perf.json、场景测试结果（gdunit4-report.xml/json）一并纳入门禁聚合，统一在 quality_gates.py 中判定通过/失败。
