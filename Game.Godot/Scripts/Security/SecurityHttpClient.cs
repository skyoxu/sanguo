using Godot;
using System;
using System.Linq;
using System.Text.Json;

namespace Game.Godot.Scripts.Security;

public partial class SecurityHttpClient : Node
{
    [Signal] public delegate void RequestBlockedEventHandler(string reason, string url);

    private const string AllowedExternalHostsEnvVar = "ALLOWED_EXTERNAL_HOSTS";
    private const string AllowInsecureDefaultsEnvVar = "GD_ALLOW_INSECURE_DEFAULTS";

    [Export] public string[] AllowedDomains { get; set; } = Array.Empty<string>();
    [Export] public string[] AllowedMethods { get; set; } = new[] { "GET", "POST" };
    [Export] public bool EnforceHttps { get; set; } = true;
    [Export] public int MaxBodyBytes { get; set; } = 10_000_000; // 10 MB

    public bool Validate(string method, string url, string? contentType = null, int bodyBytes = 0)
    {
        method = (method ?? "").Trim().ToUpperInvariant();
        if (!AllowedMethods.Contains(method))
            return Block("METHOD_DENIED", url, $"method={method}");

        if (string.IsNullOrWhiteSpace(url))
            return Block("URL_EMPTY", url, "empty");

        if (url.StartsWith("file://", StringComparison.OrdinalIgnoreCase))
            return Block("URL_PROTOCOL_DENIED", url, "file://");

        if (EnforceHttps && !url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            return Block("URL_PROTOCOL_DENIED", url, "not https");

        try
        {
            var uri = new Uri(url);
            var host = uri.Host ?? string.Empty;
            var allowlist = ResolveAllowedDomains();
            if (allowlist.Length == 0)
            {
                if (IsInsecureDefaultsEnabled())
                {
                    Audit("HTTP_ALLOWED_INSECURE_DEFAULTS", url, $"method={method}");
                    return true;
                }

                return Block("URL_ALLOWLIST_NOT_CONFIGURED", url, "allowlist_not_configured");
            }

            var allowed = allowlist.Any(d => IsHostAllowed(host, d));
            if (!allowed)
                return Block("URL_DOMAIN_DENIED", url, $"host={host}");
        }
        catch
        {
            return Block("URL_PARSE_ERROR", url, "invalid uri");
        }

        if (method == "POST")
        {
            if (string.IsNullOrWhiteSpace(contentType))
                return Block("POST_NO_CONTENT_TYPE", url, "missing content-type");
            if (bodyBytes > MaxBodyBytes)
                return Block("POST_BODY_TOO_LARGE", url, $"bytes={bodyBytes}");
        }

        Audit("HTTP_ALLOWED", url, $"method={method}");
        return true;
    }

    private string[] ResolveAllowedDomains()
    {
        var configured = (AllowedDomains ?? Array.Empty<string>())
            .Select(x => (x ?? string.Empty).Trim().Trim('.'))
            .Where(x => !string.IsNullOrWhiteSpace(x))
            .ToArray();
        if (configured.Length > 0)
        {
            return configured;
        }

        var csv = (System.Environment.GetEnvironmentVariable(AllowedExternalHostsEnvVar) ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(csv))
        {
            return Array.Empty<string>();
        }

        return csv
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(x => (x ?? string.Empty).Trim().Trim('.'))
            .Where(x => !string.IsNullOrWhiteSpace(x))
            .ToArray();
    }

    private static bool IsInsecureDefaultsEnabled()
    {
        var raw = (System.Environment.GetEnvironmentVariable(AllowInsecureDefaultsEnvVar) ?? "0").Trim();
        return string.Equals(raw, "1", StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsHostAllowed(string host, string allowed)
    {
        if (string.IsNullOrWhiteSpace(host) || string.IsNullOrWhiteSpace(allowed))
        {
            return false;
        }

        if (string.Equals(host, allowed, StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }

        return host.EndsWith("." + allowed, StringComparison.OrdinalIgnoreCase);
    }

    private bool Block(string evt, string url, string reason)
    {
        EmitSignal(SignalName.RequestBlocked, reason, url);
        Audit(evt, url, reason);
        return false;
    }

    private void Audit(string eventType, string resource, string reason)
    {
        try
        {
            var entry = new { ts = DateTime.UtcNow.ToString("O"), event_type = eventType, url = resource, reason, source = nameof(SecurityHttpClient) };
            var line = JsonSerializer.Serialize(entry);
            SecurityFileAdapter.TryAppendLine("user://logs/security/audit-http.jsonl", line, caller: "SecurityHttpClient.Audit", out _);
        }
        catch { /* ignore audit failures */ }
    }
}

