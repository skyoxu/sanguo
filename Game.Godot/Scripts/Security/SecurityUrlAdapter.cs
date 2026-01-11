using Game.Core.Security;
using Godot;
using System;

namespace Game.Godot.Scripts.Security;

public static class SecurityUrlAdapter
{
    private const string AllowedExternalHostsEnvVar = "ALLOWED_EXTERNAL_HOSTS";
    private const string AllowInsecureDefaultsEnvVar = "GD_ALLOW_INSECURE_DEFAULTS";

    public static bool TryOpenExternalUrl(string url, string caller, out string reason)
    {
        var allowedHostsCsv = System.Environment.GetEnvironmentVariable(AllowedExternalHostsEnvVar);
        var allowInsecureDefaults = IsInsecureDefaultsEnabled();

        if (!SecurityUrlPolicy.TryValidateExternalUrl(url, allowedHostsCsv, allowInsecureDefaults, out reason))
        {
            SecurityAuditWriter.TryAppendSecurityAudit(
                action: "SECURITY_URL_DENIED",
                reason: reason,
                target: $"url={url}",
                caller: caller,
                eventType: "security.url.open.denied",
                eventSource: nameof(SecurityUrlAdapter),
                eventId: Guid.NewGuid().ToString("N"));
            return false;
        }

        try
        {
            OS.ShellOpen(url);
            reason = "allow:url_opened";
            return true;
        }
        catch (Exception ex)
        {
            reason = "deny:os_shell_open_failed:" + ex.GetType().Name;
            SecurityAuditWriter.TryAppendSecurityAudit(
                action: "SECURITY_URL_DENIED",
                reason: reason,
                target: $"url={url}",
                caller: caller,
                eventType: "security.url.open.failed",
                eventSource: nameof(SecurityUrlAdapter),
                eventId: Guid.NewGuid().ToString("N"));
            return false;
        }
    }

    private static bool IsInsecureDefaultsEnabled()
    {
        var raw = (System.Environment.GetEnvironmentVariable(AllowInsecureDefaultsEnvVar) ?? "0").Trim();
        return string.Equals(raw, "1", StringComparison.OrdinalIgnoreCase);
    }
}

