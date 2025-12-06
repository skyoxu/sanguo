using Godot;
using System;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace Game.Godot.Scripts.Security;

public partial class SecurityHttpClient : Node
{
    [Signal] public delegate void RequestBlockedEventHandler(string reason, string url);

    [Export] public string[] AllowedDomains { get; set; } = new[] { "example.com", "sentry.io" };
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
            var allowed = AllowedDomains.Any(d => host.EndsWith(d, StringComparison.OrdinalIgnoreCase));
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
            var line = JsonSerializer.Serialize(entry) + System.Environment.NewLine;
            var dir = ProjectSettings.GlobalizePath("user://logs/security");
            Directory.CreateDirectory(dir);
            File.AppendAllText(System.IO.Path.Combine(dir, "audit-http.jsonl"), line);
        }
        catch { /* ignore audit failures */ }
    }
}

