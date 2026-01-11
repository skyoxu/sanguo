using System;
using System.Collections.Generic;
using System.IO;

namespace Game.Core.Security;

public static class SecurityProcessPolicy
{
    public static bool TryValidateExecute(
        string fileName,
        string[] args,
        bool isDevOrCi,
        string? allowedCommandsCsv,
        out string reason)
    {
        reason = "deny";

        if (!isDevOrCi)
        {
            reason = "deny:disabled_outside_dev_or_ci";
            return false;
        }

        if (string.IsNullOrWhiteSpace(fileName))
        {
            reason = "deny:empty_command";
            return false;
        }

        var baseName = Path.GetFileName(fileName.Trim());
        if (!string.Equals(baseName, fileName.Trim(), StringComparison.OrdinalIgnoreCase))
        {
            reason = "deny:path_not_allowed";
            return false;
        }

        var allowList = ParseCsv(allowedCommandsCsv);
        if (allowList.Count == 0)
        {
            reason = "deny:allowlist_not_configured";
            return false;
        }

        foreach (var allowed in allowList)
        {
            if (string.Equals(baseName, allowed, StringComparison.OrdinalIgnoreCase))
            {
                reason = "allow:command_allowlisted";
                return true;
            }
        }

        reason = "deny:command_not_allowlisted";
        return false;
    }

    public static bool TryValidateProcess(
        string fileName,
        string[] args,
        bool isDevOrCi,
        string? allowedCommandsCsv,
        out string reason)
        => TryValidateExecute(fileName, args, isDevOrCi, allowedCommandsCsv, out reason);

    public static bool TryValidate(
        string fileName,
        string[] args,
        bool isDevOrCi,
        string? allowedCommandsCsv,
        out string reason)
        => TryValidateExecute(fileName, args, isDevOrCi, allowedCommandsCsv, out reason);

    private static List<string> ParseCsv(string? csv)
    {
        var list = new List<string>();
        var s = (csv ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(s))
        {
            return list;
        }

        foreach (var raw in s.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            var item = (raw ?? string.Empty).Trim();
            if (string.IsNullOrWhiteSpace(item))
            {
                continue;
            }

            list.Add(item);
        }

        return list;
    }
}

