using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Xunit.Sdk;

namespace Game.Core.Tests.Tasks;

internal static class Task1PreflightEvidenceGuard
{
    private const string StrictEnvName = "TASK1_PREFLIGHT_REQUIRED";
    private const string SolutionFileName = "Game.sln";

    internal static bool TryGetLatestArtifact(out Task1PreflightArtifact artifact, out string reason)
    {
        var repoRoot = FindRepoRoot();
        var ciRoot = Path.Combine(repoRoot, "logs", "ci");
        if (!Directory.Exists(ciRoot))
        {
            artifact = default;
            reason = "missing logs/ci directory";
            return false;
        }

        foreach (var dir in Directory.GetDirectories(ciRoot).OrderByDescending(Path.GetFileName, StringComparer.OrdinalIgnoreCase))
        {
            var taskJsonPath = Path.Combine(dir, "task-0001.json");
            var evidenceDirectory = Path.Combine(dir, "env-evidence");
            if (File.Exists(taskJsonPath) && Directory.Exists(evidenceDirectory))
            {
                artifact = new Task1PreflightArtifact(repoRoot, Path.GetFileName(dir) ?? string.Empty, taskJsonPath, evidenceDirectory);
                reason = string.Empty;
                return true;
            }
        }

        artifact = default;
        reason = "missing task-0001.json and env-evidence in logs/ci/<date>";
        return false;
    }

    internal static void EnsureOrSkip(string reason)
    {
        if (!ShouldEnforcePreflight())
        {
            return;
        }

        throw new XunitException(
            "Task1 preflight evidence is required but missing. " +
            reason +
            " Set TASK1_PREFLIGHT_REQUIRED=0 (or unset) to suppress in non-Task1 runs.");
    }

    private static bool ShouldEnforcePreflight()
    {
        var raw = Environment.GetEnvironmentVariable(StrictEnvName);
        if (string.IsNullOrWhiteSpace(raw))
        {
            return false;
        }

        return raw.Equals("1", StringComparison.OrdinalIgnoreCase)
               || raw.Equals("true", StringComparison.OrdinalIgnoreCase)
               || raw.Equals("yes", StringComparison.OrdinalIgnoreCase)
               || raw.Equals("on", StringComparison.OrdinalIgnoreCase);
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, SolutionFileName)))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new InvalidOperationException(
            "Unable to locate repository root containing " + SolutionFileName + ".");
    }
}

internal readonly record struct Task1PreflightArtifact(
    string RepoRoot,
    string DateSegment,
    string TaskJsonPath,
    string EvidenceDirectory);
