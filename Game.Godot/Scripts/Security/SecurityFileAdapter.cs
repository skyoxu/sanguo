using Game.Core.Utilities;
using Godot;
using System;

namespace Game.Godot.Scripts.Security;

public static class SecurityFileAdapter
{
    public static bool TryReadText(string path, string caller, out string text, out string reason)
    {
        text = string.Empty;

        if (!SecureSavePathPolicy.TryResolveForRead(path, out var resolved, out reason))
        {
            AuditDenied("SECURITY_FILE_READ_DENIED", reason, path, caller);
            return false;
        }

        if (!FileAccess.FileExists(resolved))
        {
            reason = "deny:file_missing";
            return false;
        }

        try
        {
            using var f = FileAccess.Open(resolved, FileAccess.ModeFlags.Read);
            if (f == null)
            {
                reason = "deny:file_open_failed";
                AuditDenied("SECURITY_FILE_READ_DENIED", reason, resolved, caller);
                return false;
            }

            text = f.GetAsText();
            reason = "allow:file_read_ok";
            return true;
        }
        catch (Exception ex)
        {
            reason = "deny:file_read_exception:" + ex.GetType().Name;
            AuditDenied("SECURITY_FILE_READ_DENIED", reason, resolved, caller);
            return false;
        }
    }

    public static bool TryReadBytes(string path, string caller, out byte[] bytes, out string reason)
    {
        bytes = Array.Empty<byte>();

        if (!SecureSavePathPolicy.TryResolveForRead(path, out var resolved, out reason))
        {
            AuditDenied("SECURITY_FILE_READ_DENIED", reason, path, caller);
            return false;
        }

        if (!FileAccess.FileExists(resolved))
        {
            reason = "deny:file_missing";
            return false;
        }

        try
        {
            using var f = FileAccess.Open(resolved, FileAccess.ModeFlags.Read);
            if (f == null)
            {
                reason = "deny:file_open_failed";
                AuditDenied("SECURITY_FILE_READ_DENIED", reason, resolved, caller);
                return false;
            }

            bytes = f.GetBuffer((long)f.GetLength());
            reason = "allow:file_read_ok";
            return true;
        }
        catch (Exception ex)
        {
            reason = "deny:file_read_exception:" + ex.GetType().Name;
            AuditDenied("SECURITY_FILE_READ_DENIED", reason, resolved, caller);
            return false;
        }
    }

    public static bool TryWriteText(string path, string content, string caller, out string reason)
    {
        if (!SecureSavePathPolicy.TryResolveForWrite(path, out var resolved, out reason))
        {
            AuditDenied("SECURITY_FILE_WRITE_DENIED", reason, path, caller);
            return false;
        }

        if (!resolved.StartsWith("user://", StringComparison.Ordinal))
        {
            reason = "deny:write_requires_user_scheme";
            AuditDenied("SECURITY_FILE_WRITE_DENIED", reason, resolved, caller);
            return false;
        }

        try
        {
            EnsureUserDirectoryExists(resolved);
            using var f = FileAccess.Open(resolved, FileAccess.ModeFlags.Write);
            if (f == null)
            {
                reason = "deny:file_open_failed";
                AuditDenied("SECURITY_FILE_WRITE_DENIED", reason, resolved, caller);
                return false;
            }

            f.StoreString(content ?? string.Empty);
            f.Flush();
            reason = "allow:file_write_ok";
            return true;
        }
        catch (Exception ex)
        {
            reason = "deny:file_write_exception:" + ex.GetType().Name;
            AuditDenied("SECURITY_FILE_WRITE_DENIED", reason, resolved, caller);
            return false;
        }
    }

    public static bool TryAppendLine(string path, string line, string caller, out string reason)
    {
        var payload = (line ?? string.Empty) + System.Environment.NewLine;
        return TryAppendText(path, payload, caller, out reason);
    }

    public static bool TryAppendText(string path, string content, string caller, out string reason)
    {
        if (!SecureSavePathPolicy.TryResolveForWrite(path, out var resolved, out reason))
        {
            AuditDenied("SECURITY_FILE_APPEND_DENIED", reason, path, caller);
            return false;
        }

        if (!resolved.StartsWith("user://", StringComparison.Ordinal))
        {
            reason = "deny:append_requires_user_scheme";
            AuditDenied("SECURITY_FILE_APPEND_DENIED", reason, resolved, caller);
            return false;
        }

        try
        {
            EnsureUserDirectoryExists(resolved);
            var exists = FileAccess.FileExists(resolved);
            using var f = FileAccess.Open(resolved, exists ? FileAccess.ModeFlags.ReadWrite : FileAccess.ModeFlags.Write);
            if (f == null)
            {
                reason = "deny:file_open_failed";
                AuditDenied("SECURITY_FILE_APPEND_DENIED", reason, resolved, caller);
                return false;
            }

            if (exists)
            {
                f.SeekEnd();
            }

            f.StoreString(content ?? string.Empty);
            f.Flush();
            reason = "allow:file_append_ok";
            return true;
        }
        catch (Exception ex)
        {
            reason = "deny:file_append_exception:" + ex.GetType().Name;
            AuditDenied("SECURITY_FILE_APPEND_DENIED", reason, resolved, caller);
            return false;
        }
    }

    public static bool TryDeleteFile(string path, string caller, out string reason)
    {
        if (!SecureSavePathPolicy.TryResolveForWrite(path, out var resolved, out reason))
        {
            AuditDenied("SECURITY_FILE_DELETE_DENIED", reason, path, caller);
            return false;
        }

        if (!resolved.StartsWith("user://", StringComparison.Ordinal))
        {
            reason = "deny:delete_requires_user_scheme";
            AuditDenied("SECURITY_FILE_DELETE_DENIED", reason, resolved, caller);
            return false;
        }

        try
        {
            if (!FileAccess.FileExists(resolved))
            {
                reason = "allow:file_missing";
                return true;
            }

            var abs = ProjectSettings.GlobalizePath(resolved);
            DirAccess.RemoveAbsolute(abs);
            reason = "allow:file_deleted";
            return true;
        }
        catch (Exception ex)
        {
            reason = "deny:file_delete_exception:" + ex.GetType().Name;
            AuditDenied("SECURITY_FILE_DELETE_DENIED", reason, resolved, caller);
            return false;
        }
    }

    private static void EnsureUserDirectoryExists(string userPath)
    {
        var abs = ProjectSettings.GlobalizePath(userPath);
        var dir = System.IO.Path.GetDirectoryName(abs);
        if (string.IsNullOrWhiteSpace(dir))
        {
            return;
        }

        DirAccess.MakeDirRecursiveAbsolute(dir.Replace('\\', '/'));
    }

    private static void AuditDenied(string action, string reason, string targetPath, string caller)
    {
        SecurityAuditWriter.TryAppendSecurityAudit(
            action: action,
            reason: reason,
            target: $"path={targetPath}",
            caller: caller,
            eventType: "security.file.access.denied",
            eventSource: nameof(SecurityFileAdapter),
            eventId: Guid.NewGuid().ToString("N"));
    }
}
