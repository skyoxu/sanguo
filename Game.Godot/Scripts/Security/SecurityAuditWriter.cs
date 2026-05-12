using Godot;
using System;
using System.Collections.Generic;
using System.Text.Json;
using Game.Core.Security;

namespace Game.Godot.Scripts.Security;

internal static class SecurityAuditWriter
{
    internal static void TryAppendSecurityAudit(
        string action,
        string reason,
        string target,
        string caller,
        string? eventType = null,
        string? eventSource = null,
        string? eventId = null,
        object? details = null)
    {
        const string fallbackDir = "user://logs/security";
        const string fallbackPath = fallbackDir + "/security-audit.jsonl";
        var primaryPath = LooksLikeSinkPath(target) ? target : fallbackPath;

        try
        {
            var record = new Dictionary<string, object?>
            {
                ["ts"] = DateTimeOffset.UtcNow.ToString("O"),
                ["action"] = action,
                ["reason"] = reason,
                ["target"] = target,
                ["caller"] = caller,
            };

            if (!string.IsNullOrWhiteSpace(eventType))
            {
                record["event_type"] = eventType;
            }

            if (!string.IsNullOrWhiteSpace(eventSource))
            {
                record["event_source"] = eventSource;
            }

            if (!string.IsNullOrWhiteSpace(eventId))
            {
                record["event_id"] = eventId;
            }

            if (details != null)
            {
                record["details"] = details;
            }

            var line = JsonSerializer.Serialize(record) + System.Environment.NewLine;
            var written = SecurityAuditFallbackPolicy.TryWriteWithFallback(
                primarySinkPath: primaryPath,
                fallbackSinkPath: fallbackPath,
                tryWrite: path => TryWriteLine(path, line),
                warningSink: message => GD.PushWarning($"SecurityAuditWriter: {message}"));

            if (!written)
            {
                GD.PushWarning("SecurityAuditWriter: both primary and fallback audit writes failed.");
            }
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SecurityAuditWriter: write failed: {ex.Message}");
        }
    }

    private static bool TryWriteLine(string sinkPath, string line)
    {
        if (sinkPath.Replace('\\', '/').StartsWith("res://", StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        EnsureDirectory(sinkPath);
        var exists = FileAccess.FileExists(sinkPath);
        using var file = FileAccess.Open(sinkPath, exists ? FileAccess.ModeFlags.ReadWrite : FileAccess.ModeFlags.Write);
        if (file == null)
        {
            return false;
        }

        if (exists)
        {
            file.SeekEnd();
        }

        file.StoreString(line);
        file.Flush();
        return true;
    }

    private static void EnsureDirectory(string sinkPath)
    {
        var normalized = sinkPath.Replace('\\', '/');
        var idx = normalized.LastIndexOf('/');
        if (idx <= 0)
        {
            return;
        }

        var dirPath = normalized[..idx];
        var absDir = ProjectSettings.GlobalizePath(dirPath).Replace('\\', '/');
        DirAccess.MakeDirRecursiveAbsolute(absDir);
    }

    private static bool LooksLikeSinkPath(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return false;
        }

        var normalized = value.Replace('\\', '/').Trim();
        return normalized.StartsWith("user://", StringComparison.OrdinalIgnoreCase)
            || normalized.StartsWith("res://", StringComparison.OrdinalIgnoreCase)
            || normalized.EndsWith(".jsonl", StringComparison.OrdinalIgnoreCase)
            || normalized.EndsWith(".log", StringComparison.OrdinalIgnoreCase)
            || normalized.EndsWith(".txt", StringComparison.OrdinalIgnoreCase);
    }
}
