using System;

namespace Game.Core.Utilities;

public static class SecureSavePathPolicy
{
    public static bool TryResolveForRead(string path, out string resolved, out string reason)
    {
        return TryResolveByIntent(path, intent: "read", out resolved, out reason);
    }

    public static bool TryResolveForWrite(string path, out string resolved, out string reason)
    {
        return TryResolveByIntent(path, intent: "write", out resolved, out reason);
    }

    public static bool TryResolve(string root, string input, out string resolved)
    {
        resolved = string.Empty;

        if (string.IsNullOrWhiteSpace(root) || string.IsNullOrWhiteSpace(input))
        {
            return false;
        }

        var normalizedRoot = NormalizeGodotPath(root);
        if (!normalizedRoot.StartsWith("user://", StringComparison.Ordinal))
        {
            return false;
        }

        var normalizedInput = NormalizeGodotPath(input);

        if (normalizedInput.StartsWith("user://", StringComparison.Ordinal))
        {
            if (!IsUnderRoot(normalizedRoot, normalizedInput))
            {
                return false;
            }

            var relative = normalizedInput.Length == normalizedRoot.Length
                ? string.Empty
                : normalizedInput[(normalizedRoot.Length + 1)..];

            if (!TryNormalizeRelativeSegments(relative, out var safeRelative))
            {
                return false;
            }

            resolved = $"{normalizedRoot}/{safeRelative}";
            return true;
        }

        if (IsDefinitelyAbsoluteNonGodotPath(normalizedInput))
        {
            return false;
        }

        if (!TryNormalizeRelativeSegments(normalizedInput, out var safeRelativePath))
        {
            return false;
        }

        resolved = $"{normalizedRoot}/{safeRelativePath}";
        return true;
    }

    private static bool TryResolveByIntent(string path, string intent, out string resolved, out string reason)
    {
        resolved = string.Empty;
        reason = "deny";

        if (string.IsNullOrWhiteSpace(path))
        {
            reason = "deny:empty_path";
            return false;
        }

        var normalized = NormalizeGodotPath(path);

        if (normalized.StartsWith("user://", StringComparison.Ordinal))
        {
            var rest = normalized["user://".Length..].TrimStart('/');
            if (!TryNormalizeRelativeSegments(rest, out var safeRelative))
            {
                reason = "deny:user_path_invalid_or_traversal";
                return false;
            }

            resolved = "user://" + safeRelative;
            reason = string.Equals(intent, "write", StringComparison.OrdinalIgnoreCase)
                ? "allow:user_path_allowed_write"
                : "allow:user_path_allowed_read";
            return true;
        }

        if (normalized.StartsWith("res://", StringComparison.Ordinal))
        {
            var rest = normalized["res://".Length..].TrimStart('/');
            if (!TryNormalizeRelativeSegments(rest, out var safeRelative))
            {
                reason = "deny:res_path_invalid_or_traversal";
                return false;
            }

            if (string.Equals(intent, "write", StringComparison.OrdinalIgnoreCase))
            {
                reason = "deny:res_path_not_writable";
                return false;
            }

            resolved = "res://" + safeRelative;
            reason = "allow:res_path_allowed_read";
            return true;
        }

        if (IsDefinitelyAbsoluteNonGodotPath(normalized))
        {
            reason = "deny:absolute_path_not_allowed";
            return false;
        }

        reason = "deny:unsupported_scheme";
        return false;
    }

    private static bool IsDefinitelyAbsoluteNonGodotPath(string path)
    {
        if (path.StartsWith("/", StringComparison.Ordinal))
        {
            return true;
        }

        if (path.Contains(':', StringComparison.Ordinal))
        {
            return true;
        }

        return false;
    }

    private static string NormalizeGodotPath(string path)
    {
        var s = path.Trim();
        s = s.Replace('\\', '/');

        if (s.StartsWith("user://", StringComparison.Ordinal))
        {
            var rest = s["user://".Length..];
            while (rest.Contains("//", StringComparison.Ordinal))
            {
                rest = rest.Replace("//", "/", StringComparison.Ordinal);
            }

            return ("user://" + rest).TrimEnd('/');
        }

        if (s.StartsWith("res://", StringComparison.Ordinal))
        {
            var rest = s["res://".Length..];
            while (rest.Contains("//", StringComparison.Ordinal))
            {
                rest = rest.Replace("//", "/", StringComparison.Ordinal);
            }

            return ("res://" + rest).TrimEnd('/');
        }

        while (s.Contains("//", StringComparison.Ordinal))
        {
            s = s.Replace("//", "/", StringComparison.Ordinal);
        }

        if (s.StartsWith("user:/", StringComparison.Ordinal))
        {
            s = "user://" + s["user:/".Length..];
        }

        if (s.StartsWith("res:/", StringComparison.Ordinal))
        {
            s = "res://" + s["res:/".Length..];
        }

        return s.TrimEnd('/');
    }

    private static bool IsUnderRoot(string normalizedRoot, string normalizedUserPath)
    {
        if (string.Equals(normalizedUserPath, normalizedRoot, StringComparison.Ordinal))
        {
            return false;
        }

        return normalizedUserPath.StartsWith(normalizedRoot + "/", StringComparison.Ordinal);
    }

    private static bool TryNormalizeRelativeSegments(string relative, out string normalized)
    {
        normalized = string.Empty;

        var s = (relative ?? string.Empty).Trim();
        s = s.Replace('\\', '/');

        if (string.IsNullOrWhiteSpace(s))
        {
            return false;
        }

        if (s.StartsWith("/", StringComparison.Ordinal))
        {
            return false;
        }

        var parts = s.Split('/', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length == 0)
        {
            return false;
        }

        foreach (var p in parts)
        {
            if (p == "." || p == "..")
            {
                return false;
            }
        }

        normalized = string.Join("/", parts);
        return normalized.Length > 0;
    }
}
