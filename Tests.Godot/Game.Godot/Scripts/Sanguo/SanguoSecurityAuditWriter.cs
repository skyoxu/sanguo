using Godot;
using System;
using System.IO;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

internal static class SanguoSecurityAuditWriter
{
    internal static void TryAppendSecurityAudit(
        string action,
        string reason,
        string target,
        string caller,
        string eventType,
        string eventSource,
        string eventId)
    {
        try
        {
            var dir = ProjectSettings.GlobalizePath("user://logs/security");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, "security-audit.jsonl");

            var record = new
            {
                ts = DateTimeOffset.UtcNow.ToString("O"),
                action,
                reason,
                target,
                caller,
                event_type = eventType,
                event_source = eventSource,
                event_id = eventId,
            };

            File.AppendAllText(path, JsonSerializer.Serialize(record) + System.Environment.NewLine);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"SanguoSecurityAuditWriter: write failed: {ex.Message}");
        }
    }
}

