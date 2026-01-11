using Godot;
using System;
using System.Collections.Generic;
using System.Text.Json;

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
        try
        {
            const string userDir = "user://logs/security";
            const string userPath = userDir + "/security-audit.jsonl";

            var absDir = ProjectSettings.GlobalizePath(userDir).Replace('\\', '/');
            DirAccess.MakeDirRecursiveAbsolute(absDir);

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

            var exists = FileAccess.FileExists(userPath);
            using var f = FileAccess.Open(userPath, exists ? FileAccess.ModeFlags.ReadWrite : FileAccess.ModeFlags.Write);
            if (f == null)
            {
                throw new InvalidOperationException("FileAccess.Open returned null");
            }

            if (exists)
            {
                f.SeekEnd();
            }

            f.StoreString(JsonSerializer.Serialize(record) + System.Environment.NewLine);
            f.Flush();
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SecurityAuditWriter: write failed: {ex.Message}");
        }
    }
}
