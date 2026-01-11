using Godot;
using System;


namespace Game.Godot.Scripts.Security;

public partial class SecurityAudit : Node
{
    public override void _Ready()
    {
        try
        {
            bool hasSqlite = false;
            try
            {
                // Avoid engine error log by checking class list before probing
                var classes = ClassDB.GetClassList();
                foreach (var c in classes)
                {
                    var s = c.ToString();
                    if (s == "SQLite") { hasSqlite = true; break; }
                }
            }
            catch { hasSqlite = false; }

            var details = new
            {
                app = GetAppNameSafe(),
                godot = Engine.GetVersionInfo()["string"].ToString(),
                db_backend = System.Environment.GetEnvironmentVariable("GODOT_DB_BACKEND") ?? "default",
                demo = (System.Environment.GetEnvironmentVariable("TEMPLATE_DEMO") ?? "0").ToLowerInvariant() == "1",
                plugin_sqlite = hasSqlite,
            };

            SecurityAuditWriter.TryAppendSecurityAudit(
                action: "SECURITY_BASELINE",
                reason: "ready",
                target: "user://logs/security/security-audit.jsonl",
                caller: "SecurityAudit._Ready",
                eventType: "security.baseline.ready",
                eventSource: nameof(SecurityAudit),
                eventId: Guid.NewGuid().ToString("N"),
                details: details);
        }
        catch (Exception ex)
        {
            GD.PushWarning($"[SecurityAudit] write failed: {ex.Message}");
        }
    }
    private static string GetAppNameSafe()
    {
        try
        {
            var v = ProjectSettings.GetSetting("application/config/name");
            return v.VariantType == Variant.Type.Nil ? "GodotGame" : v.AsString();
        }
        catch { return "GodotGame"; }
    }
}

