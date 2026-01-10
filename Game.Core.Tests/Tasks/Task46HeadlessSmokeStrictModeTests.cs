using System;
using System.Diagnostics;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task46HeadlessSmokeStrictModeTests
{
    // ACC:T46.3
    [Fact]
    public void ShouldReturnZero_WhenStrictModeAndMarkerIsEmittedByProcess()
    {
        var result = RunSmokeHeadless(
            mode: "strict",
            fakeStdoutLine: "[TEMPLATE_SMOKE_READY] Main scene initialized",
            fakeStderrLine: null,
            timeoutSec: 5);

        result.ExitCode.Should().Be(0);
        result.HeadlessLogText.Should().Contain("[SMOKE] strict-passed");
        result.HeadlessLogText.Should().NotContain("[SMOKE] strict-failed");
    }

    // ACC:T46.3
    [Fact]
    public void ShouldReturnNonZeroAndMarkStrictFailed_WhenStrictModeAndNoMarkersAreEmitted()
    {
        var result = RunSmokeHeadless(
            mode: "strict",
            fakeStdoutLine: "Some other output",
            fakeStderrLine: null,
            timeoutSec: 5);

        result.ExitCode.Should().NotBe(0);
        result.HeadlessLogText.Should().Contain("[SMOKE] strict-failed");
    }

    // ACC:T46.3
    [Fact]
    public void ShouldReturnNonZeroAndMarkTimeout_WhenStrictModeAndProcessTimesOut()
    {
        var result = RunSmokeHeadless(
            mode: "strict",
            fakeStdoutLine: null,
            fakeStderrLine: null,
            timeoutSec: 1,
            simulateTimeout: true);

        result.ExitCode.Should().NotBe(0);
        result.StdoutText.Should().Contain("timeout reached", "timeout should be observable in runner stdout");
        result.HeadlessLogText.Should().Contain("[SMOKE] timeout");
        result.HeadlessLogText.Should().Contain("[SMOKE] strict-failed");
    }

    private static SmokeRunResult RunSmokeHeadless(
        string mode,
        string? fakeStdoutLine,
        string? fakeStderrLine,
        int timeoutSec,
        bool simulateTimeout = false)
    {
        var repoRoot = FindRepoRootFrom(AppContext.BaseDirectory);
        var tempDir = Path.Combine(Path.GetTempPath(), $"sanguo-smoke-test-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDir);

        var fakeGodotCmd = Path.Combine(tempDir, "fake_godot.cmd");
        File.WriteAllText(fakeGodotCmd, BuildFakeGodotCmd(fakeStdoutLine, fakeStderrLine, simulateTimeout), System.Text.Encoding.ASCII);

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
        psi.ArgumentList.Add(mode);
        psi.ArgumentList.Add("--godot-bin");
        psi.ArgumentList.Add(fakeGodotCmd);
        psi.ArgumentList.Add("--project-path");
        psi.ArgumentList.Add(".");
        psi.ArgumentList.Add("--scene");
        psi.ArgumentList.Add("res://Game.Godot/Scenes/Main.tscn");
        psi.ArgumentList.Add("--timeout-sec");
        psi.ArgumentList.Add(timeoutSec.ToString(System.Globalization.CultureInfo.InvariantCulture));

        using var proc = Process.Start(psi);
        proc.Should().NotBeNull();

        var stdout = proc!.StandardOutput.ReadToEnd();
        var stderr = proc.StandardError.ReadToEnd();
        proc.WaitForExit(30_000);

        var headlessLogPath = ExtractHeadlessLogPathOrThrow(stdout);
        var fullHeadlessLogPath = Path.Combine(repoRoot, headlessLogPath);
        File.Exists(fullHeadlessLogPath).Should().BeTrue($"headless log must be written at {fullHeadlessLogPath}");

        var headlessText = File.ReadAllText(fullHeadlessLogPath);
        return new SmokeRunResult(proc.ExitCode, stdout, stderr, headlessText);
    }

    private static string BuildFakeGodotCmd(string? stdoutLine, string? stderrLine, bool simulateTimeout)
    {
        var lines = new System.Collections.Generic.List<string>
        {
            "@echo off",
            "setlocal",
        };

        if (simulateTimeout)
        {
            lines.Add("ping -n 6 127.0.0.1 > nul");
        }

        if (!string.IsNullOrWhiteSpace(stdoutLine))
        {
            lines.Add($"echo {stdoutLine}");
        }

        if (!string.IsNullOrWhiteSpace(stderrLine))
        {
            lines.Add($"echo {stderrLine} 1>&2");
        }

        lines.Add("exit /b 0");
        return string.Join("\r\n", lines) + "\r\n";
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

    private sealed record SmokeRunResult(int ExitCode, string StdoutText, string StderrText, string HeadlessLogText);
}

