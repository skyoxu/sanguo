using System;
using System.Globalization;
using System.IO;
using System.Diagnostics;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task46HeadlessSmokeNonStrictTests
{
    private const string TemplateSmokeReadyMarker = "[TEMPLATE_SMOKE_READY]";
    private const string DbOpenedMarker = "[DB] opened";

    // ACC:T46.2
    [Fact]
    public void ShouldPass_WhenExitCodeIsZeroEvenIfMarkersMissingInLooseMode()
    {
        var stdout = "";
        var stderr = "";

        ContainsRequiredMarkers(stdout).Should().BeFalse();
        EvaluateLooseMode(exitCode: 0, stdout, stderr).Should().BeTrue();
    }

    [Fact]
    public void ShouldBuildSmokeOutputDirectory_WhenGivenUtcDate()
    {
        var date = new DateTime(2030, 1, 2, 0, 0, 0, DateTimeKind.Utc);
        var relative = BuildSmokeRelativeOutputDir(date);

        relative.Should().NotBeNullOrWhiteSpace();
        relative.Should().Contain($"logs{Path.DirectorySeparatorChar}ci{Path.DirectorySeparatorChar}");
        relative.Should().EndWith($"{Path.DirectorySeparatorChar}smoke");
        relative.Should().Contain("2030-01-02");

        TemplateSmokeReadyMarker.Should().NotBeNullOrWhiteSpace();
        DbOpenedMarker.Should().NotBeNullOrWhiteSpace();
    }

    // ACC:T46.2
    [Fact]
    public void ShouldReturnZeroAndWriteLogs_WhenLooseModeAndNoMarkersAreEmitted()
    {
        var repoRoot = FindRepoRootFrom(AppContext.BaseDirectory);
        var tempDir = Path.Combine(Path.GetTempPath(), $"sanguo-smoke-test-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDir);

        var fakeGodotCmd = Path.Combine(tempDir, "fake_godot_no_output.cmd");
        File.WriteAllText(fakeGodotCmd, "@echo off\r\nexit /b 0\r\n", System.Text.Encoding.ASCII);

        var psi = new ProcessStartInfo
        {
            FileName = "py",
            WorkingDirectory = repoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        psi.ArgumentList.Add("-3");
        psi.ArgumentList.Add("scripts/python/smoke_headless.py");
        psi.ArgumentList.Add("--mode");
        psi.ArgumentList.Add("loose");
        psi.ArgumentList.Add("--godot-bin");
        psi.ArgumentList.Add(fakeGodotCmd);
        psi.ArgumentList.Add("--project-path");
        psi.ArgumentList.Add(".");
        psi.ArgumentList.Add("--scene");
        psi.ArgumentList.Add("res://Game.Godot/Scenes/Main.tscn");
        psi.ArgumentList.Add("--timeout-sec");
        psi.ArgumentList.Add("5");

        using var proc = Process.Start(psi);
        proc.Should().NotBeNull();

        var stdout = proc!.StandardOutput.ReadToEnd();
        _ = proc.StandardError.ReadToEnd();
        proc.WaitForExit(30_000);

        proc.ExitCode.Should().Be(0, "loose mode must not gate on missing markers");

        var headlessLogPath = ExtractHeadlessLogPathOrThrow(stdout);
        var fullHeadlessLogPath = Path.Combine(repoRoot, headlessLogPath);
        File.Exists(fullHeadlessLogPath).Should().BeTrue($"headless log must be written at {fullHeadlessLogPath}");
    }

    private static bool EvaluateLooseMode(int exitCode, string stdout, string stderr)
    {
        _ = stdout;
        _ = stderr;

        return exitCode == 0;
    }

    private static bool ContainsRequiredMarkers(string stdout)
    {
        if (stdout is null)
        {
            return false;
        }

        return stdout.Contains(TemplateSmokeReadyMarker, StringComparison.Ordinal)
            || stdout.Contains(DbOpenedMarker, StringComparison.Ordinal);
    }

    private static string BuildSmokeRelativeOutputDir(DateTime utcDate)
    {
        var date = utcDate.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        return Path.Combine("logs", "ci", date, "smoke");
    }

    private static string ExtractHeadlessLogPathOrThrow(string stdout)
    {
        const string marker = "[smoke_headless] log saved at ";
        var idx = stdout.IndexOf(marker, StringComparison.Ordinal);
        idx.Should().BeGreaterThanOrEqualTo(0, "smoke runner must print the headless log location");

        var start = idx + marker.Length;
        var end = stdout.IndexOf(" (out=", start, StringComparison.Ordinal);
        end.Should().BeGreaterThan(start, "smoke runner must print '(out=...)' after log path");

        return stdout[start..end].Trim();
    }

    private static string FindRepoRootFrom(string startDir)
    {
        var dir = new DirectoryInfo(startDir);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "Game.sln")))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Unable to locate repo root (Game.sln not found).");
    }
}
