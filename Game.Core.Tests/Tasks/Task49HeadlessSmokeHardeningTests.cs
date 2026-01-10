using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task49HeadlessSmokeHardeningTests
{
    // ACC:T49.1
    [Fact]
    public void ShouldExitWithoutTimeoutKill_WhenExitOnReadyEnabledAndGodotIsAvailable()
    {
        var godotBin = Environment.GetEnvironmentVariable("GODOT_BIN");
        if (string.IsNullOrWhiteSpace(godotBin) || !File.Exists(godotBin))
        {
            return;
        }

        var result = RunSmokeHeadlessRealGodot(
            mode: "strict",
            godotBin: godotBin,
            timeoutSec: 120,
            enableExitOnReady: true);

        result.ExitCode.Should().Be(0);
        result.HeadlessLogText.Should().Contain("[SMOKE] strict-passed");
        result.HeadlessLogText.Should().Contain("details exit_code=0 timed_out=False");
        result.HeadlessLogText.Should().NotContain("[SMOKE] timeout");
        result.StdoutText.Should().NotContain("timeout reached");
    }

    // ACC:T49.1
    [Fact]
    public void ShouldGuardExitOnReadyQuit_WhenReadingMainSceneScript()
    {
        var mainSceneScript = ReadRepoText("Game.Godot/Scripts/Main.gd");
        AssertQuitIsGuardedInReady(mainSceneScript);
    }

    // ACC:T49.1
    [Fact]
    public void ShouldQuitOnReadyInSmokeSession_WhenExitOnReadyEnabled()
    {
        var mainSceneScript = ReadRepoText("Game.Godot/Scripts/Main.gd");
        mainSceneScript.Should().Contain(
            "GD_SMOKE_EXIT_ON_READY",
            "the main scene must read the GD_SMOKE_EXIT_ON_READY switch to support self-terminating smoke sessions");
        mainSceneScript.Should().MatchRegex(
            @"GD_SMOKE_EXIT_ON_READY[\s\S]*(get_tree\(\)\.call_deferred\(\""quit\""\)|get_tree\(\)\.quit\()",
            "when exit-on-ready is enabled, the main scene must request scene tree quit after ready");
        AssertQuitIsGuardedInReady(mainSceneScript);

        var result = RunSmokeHeadless(
            mode: "strict",
            fakeStdoutLines:
            [
                "GD_SMOKE_EXIT_ON_READY=%GD_SMOKE_EXIT_ON_READY%",
                "[TEMPLATE_SMOKE_READY] Main scene initialized",
            ],
            timeoutSec: 5,
            fakeExitCode: 0,
            enableExitOnReady: true);

        result.ExitCode.Should().Be(0);
        result.HeadlessLogText.Should().Contain(
            "GD_SMOKE_EXIT_ON_READY=1",
            "the smoke runner must pass the exit-on-ready environment switch to the game process");
        result.HeadlessLogText.Should().Contain("[SMOKE] strict-passed");
        result.HeadlessLogText.Should().Contain("details exit_code=0 timed_out=False", "strict pass must be from a clean exit without timeout kill");
        result.HeadlessLogText.Should().NotContain("[SMOKE] timeout", "exit-on-ready smoke sessions should not rely on timeout kill");
        result.StdoutText.Should().NotContain("timeout reached", "exit-on-ready should complete without timeout");
    }

    // ACC:T49.2
    [Fact]
    public void ShouldFailStrictSmokeWithTimeoutReason_WhenExitOnReadyEnabledButProcessDoesNotExit()
    {
        var result = RunSmokeHeadless(
            mode: "strict",
            fakeStdoutLines:
            [
                "GD_SMOKE_EXIT_ON_READY=%GD_SMOKE_EXIT_ON_READY%",
                "[TEMPLATE_SMOKE_READY] Main scene initialized",
            ],
            timeoutSec: 1,
            fakeExitCode: 0,
            simulateTimeout: true,
            enableExitOnReady: true);

        result.ExitCode.Should().NotBe(0);
        result.StdoutText.Should().Contain("timeout reached");
        result.HeadlessLogText.Should().Contain("GD_SMOKE_EXIT_ON_READY=1");
        result.HeadlessLogText.Should().Contain("[SMOKE] strict-failed");
        result.HeadlessLogText.Should().Contain("reason=timeout");
        result.HeadlessLogText.Should().Contain("[SMOKE] timeout");
    }

    // ACC:T49.2
    [Theory]
    [InlineData("[TEMPLATE_SMOKE_READY] Main scene initialized", 3, false, "exit_code_nonzero")]
    [InlineData("Some other output", 0, false, "missing_marker")]
    [InlineData("[TEMPLATE_SMOKE_READY] Main scene initialized", 0, true, "timeout")]
    public void ShouldFailStrictSmokeWithExpectedReason_WhenGivenNegativeScenario(
        string stdoutLine,
        int fakeExitCode,
        bool simulateTimeout,
        string expectedReason)
    {
        var result = RunSmokeHeadless(
            mode: "strict",
            fakeStdoutLines: [stdoutLine],
            timeoutSec: 1,
            fakeExitCode: fakeExitCode,
            simulateTimeout: simulateTimeout);

        result.ExitCode.Should().NotBe(0);
        result.HeadlessLogText.Should().Contain("[SMOKE] strict-failed");
        result.HeadlessLogText.Should().Contain($"reason={expectedReason}");

        if (simulateTimeout)
        {
            result.StdoutText.Should().Contain("timeout reached", "timeout should be observable in runner stdout");
            result.HeadlessLogText.Should().Contain("[SMOKE] timeout");
        }
    }

    // ACC:T49.2
    [Fact]
    public void ShouldRequireMarkerAndZeroExitAndNoTimeout_WhenEvaluatingStrictSmokeVerdict()
    {
        var result = RunSmokeHeadless(
            mode: "strict",
            fakeStdoutLines: ["[DB] opened at user://data/game.db"],
            timeoutSec: 5,
            fakeExitCode: 0);

        result.ExitCode.Should().Be(0);
        result.HeadlessLogText.Should().Contain("[SMOKE] strict-passed");
        result.HeadlessLogText.Should().NotContain("[SMOKE] strict-failed");
    }

    // ACC:T49.3
    [Fact]
    public void ShouldDocumentStrictSmokeExitOnReadyExample_WhenReviewingWindowsQualityGateWorkflow()
    {
        var workflow = ReadRepoText(".github/workflows/windows-quality-gate.yml");

        workflow.Should().Contain(
            "GD_SMOKE_EXIT_ON_READY",
            "the workflow should include a comment example documenting the exit-on-ready switch");

        workflow.Should().MatchRegex(
            @"--mode\s+strict|--mode=strict|mode:\s*strict",
            "the workflow should include an example referencing strict smoke mode");

        HasYamlCommentLineContainingAll(workflow, "GD_SMOKE_EXIT_ON_READY", "strict")
            .Should().BeTrue("the workflow should include a comment line demonstrating strict smoke + exit-on-ready usage");
    }

    private static SmokeRunResult RunSmokeHeadless(
        string mode,
        IReadOnlyList<string> fakeStdoutLines,
        int timeoutSec,
        int fakeExitCode,
        bool simulateTimeout = false,
        bool enableExitOnReady = false)
    {
        var repoRoot = FindRepoRoot(AppContext.BaseDirectory)
            ?? FindRepoRoot(Directory.GetCurrentDirectory());
        repoRoot.Should().NotBeNull("repo root should be discoverable from the test execution directory");

        var tempDir = Path.Combine(Path.GetTempPath(), $"sanguo-smoke-test-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDir);

        var fakeGodotCmd = Path.Combine(tempDir, "fake_godot.cmd");
        File.WriteAllText(
            fakeGodotCmd,
            BuildFakeGodotCmd(fakeStdoutLines, fakeExitCode, simulateTimeout),
            System.Text.Encoding.ASCII);

        var psi = new ProcessStartInfo
        {
            FileName = "py",
            WorkingDirectory = repoRoot!.FullName,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        if (enableExitOnReady)
        {
            psi.Environment["GD_SMOKE_EXIT_ON_READY"] = "1";
        }

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
        var fullHeadlessLogPath = Path.Combine(repoRoot.FullName, headlessLogPath);
        File.Exists(fullHeadlessLogPath).Should().BeTrue($"headless log must be written at {fullHeadlessLogPath}");

        var headlessText = File.ReadAllText(fullHeadlessLogPath);
        return new SmokeRunResult(proc.ExitCode, stdout, stderr, headlessText);
    }

    private static SmokeRunResult RunSmokeHeadlessRealGodot(string mode, string godotBin, int timeoutSec, bool enableExitOnReady)
    {
        var repoRoot = FindRepoRoot(AppContext.BaseDirectory)
            ?? FindRepoRoot(Directory.GetCurrentDirectory());
        repoRoot.Should().NotBeNull("repo root should be discoverable from the test execution directory");

        var psi = new ProcessStartInfo
        {
            FileName = "py",
            WorkingDirectory = repoRoot!.FullName,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        if (enableExitOnReady)
        {
            psi.Environment["GD_SMOKE_EXIT_ON_READY"] = "1";
        }

        psi.ArgumentList.Add("-3");
        psi.ArgumentList.Add("scripts/python/smoke_headless.py");
        psi.ArgumentList.Add("--mode");
        psi.ArgumentList.Add(mode);
        psi.ArgumentList.Add("--godot-bin");
        psi.ArgumentList.Add(godotBin);
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
        proc.WaitForExit(180_000);

        var headlessLogPath = ExtractHeadlessLogPathOrThrow(stdout);
        var fullHeadlessLogPath = Path.Combine(repoRoot.FullName, headlessLogPath);
        File.Exists(fullHeadlessLogPath).Should().BeTrue($"headless log must be written at {fullHeadlessLogPath}");

        var headlessText = File.ReadAllText(fullHeadlessLogPath);
        return new SmokeRunResult(proc.ExitCode, stdout, stderr, headlessText);
    }

    private static string BuildFakeGodotCmd(IReadOnlyList<string> stdoutLines, int exitCode, bool simulateTimeout)
    {
        var lines = new List<string>
        {
            "@echo off",
            "setlocal",
        };

        foreach (var line in stdoutLines)
        {
            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }

            lines.Add($"echo {line}");
        }

        if (simulateTimeout)
        {
            lines.Add("ping -n 6 127.0.0.1 > nul");
        }

        lines.Add($"exit /b {exitCode.ToString(System.Globalization.CultureInfo.InvariantCulture)}");
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

    private static string ReadRepoText(string repoRelativePath)
    {
        var repoRoot = FindRepoRoot(AppContext.BaseDirectory)
            ?? FindRepoRoot(Directory.GetCurrentDirectory());

        repoRoot.Should().NotBeNull("repo root should be discoverable from the test execution directory");

        var fullPath = Path.Combine(
            repoRoot!.FullName,
            repoRelativePath.Replace('/', Path.DirectorySeparatorChar));

        File.Exists(fullPath).Should().BeTrue($"required file should exist: {repoRelativePath}");

        return File.ReadAllText(fullPath);
    }

    private static DirectoryInfo? FindRepoRoot(string startDirectory)
    {
        var current = new DirectoryInfo(startDirectory);

        for (var i = 0; i < 30 && current is not null; i++)
        {
            if (File.Exists(Path.Combine(current.FullName, "project.godot"))
                || File.Exists(Path.Combine(current.FullName, "AGENTS.md"))
                || Directory.Exists(Path.Combine(current.FullName, ".git")))
            {
                return current;
            }

            current = current.Parent;
        }

        return null;
    }

    private static bool HasYamlCommentLineContainingAll(string yaml, params string[] requiredSubstrings)
    {
        var lines = yaml.Replace("\r\n", "\n").Split('\n');

        foreach (var line in lines)
        {
            var trimmed = line.TrimStart();
            if (!trimmed.StartsWith("#", StringComparison.Ordinal))
            {
                continue;
            }

            var matchesAll = requiredSubstrings.All(
                s => trimmed.IndexOf(s, StringComparison.OrdinalIgnoreCase) >= 0);

            if (matchesAll)
            {
                return true;
            }
        }

        return false;
    }

    private static void AssertQuitIsGuardedInReady(string scriptText)
    {
        var lines = scriptText.Replace("\r\n", "\n").Split('\n');
        var readyLine = Array.FindIndex(lines, l => l.StartsWith("func _ready()", StringComparison.Ordinal));
        readyLine.Should().BeGreaterThanOrEqualTo(0, "Main.gd should define a _ready() function");

        var helperLine = Array.FindIndex(lines, l => l.StartsWith("func _is_smoke_exit_on_ready_enabled()", StringComparison.Ordinal));
        helperLine.Should().BeGreaterThanOrEqualTo(0, "Main.gd should define _is_smoke_exit_on_ready_enabled()");
        helperLine.Should().BeGreaterThan(readyLine, "helper should be defined after _ready()");

        var ifLine = Array.FindIndex(lines, l => l.Contains("if _is_smoke_exit_on_ready_enabled()", StringComparison.Ordinal));
        ifLine.Should().BeGreaterThan(readyLine);
        ifLine.Should().BeLessThan(helperLine);

        var quitLine = Array.FindIndex(lines, l => l.Contains("get_tree().call_deferred(\"quit\")", StringComparison.Ordinal));
        quitLine.Should().BeGreaterThan(ifLine);
        quitLine.Should().BeLessThan(helperLine);

        lines[ifLine].StartsWith("    if ", StringComparison.Ordinal).Should().BeTrue("the smoke-quit guard should be in _ready() block");
        lines[quitLine].StartsWith("        ", StringComparison.Ordinal).Should().BeTrue("the quit call must be indented under the guard if-statement");
    }

    private sealed record SmokeRunResult(int ExitCode, string StdoutText, string StderrText, string HeadlessLogText);
}
