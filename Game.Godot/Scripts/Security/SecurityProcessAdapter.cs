using Game.Core.Security;
using Godot;
using System;

namespace Game.Godot.Scripts.Security;

public static class SecurityProcessAdapter
{
    private const string AllowedCommandsEnvVar = "ALLOWED_OS_EXECUTE_COMMANDS";

    public static bool TryExecute(string fileName, string[] args, bool blocking, string caller, out string reason)
    {
        var allowed = System.Environment.GetEnvironmentVariable(AllowedCommandsEnvVar);
        var isDevOrCi = IsDevOrCi();

        if (!SecurityProcessPolicy.TryValidateExecute(fileName, args ?? Array.Empty<string>(), isDevOrCi, allowed, out reason))
        {
            SecurityAuditWriter.TryAppendSecurityAudit(
                action: "SECURITY_PROCESS_DENIED",
                reason: reason,
                target: $"file={fileName}",
                caller: caller,
                eventType: "security.process.execute.denied",
                eventSource: nameof(SecurityProcessAdapter),
                eventId: Guid.NewGuid().ToString("N"));
            return false;
        }

        try
        {
            var arguments = args ?? Array.Empty<string>();

            if (!blocking)
            {
                var pid = OS.CreateProcess(fileName, arguments);
                reason = "allow:os_create_process_ok:pid=" + pid;
                return pid > 0;
            }

            var output = new global::Godot.Collections.Array();
            var exitCode = OS.Execute(fileName, arguments, output, readStderr: true);
            reason = "allow:os_execute_ok:exit_code=" + exitCode;
            return exitCode == 0;
        }
        catch (Exception ex)
        {
            reason = "deny:os_execute_failed:" + ex.GetType().Name;
            SecurityAuditWriter.TryAppendSecurityAudit(
                action: "SECURITY_PROCESS_DENIED",
                reason: reason,
                target: $"file={fileName}",
                caller: caller,
                eventType: "security.process.execute.failed",
                eventSource: nameof(SecurityProcessAdapter),
                eventId: Guid.NewGuid().ToString("N"));
            return false;
        }
    }

    private static bool IsDevOrCi()
    {
        if (Engine.IsEditorHint())
        {
            return true;
        }

        if (OS.HasFeature("CI"))
        {
            return true;
        }

        var ci = System.Environment.GetEnvironmentVariable("CI");
        return !string.IsNullOrWhiteSpace(ci);
    }
}
