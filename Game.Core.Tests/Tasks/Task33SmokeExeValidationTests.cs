#nullable enable

using System;
using System.IO;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task33SmokeExeValidationTests
{
    // ADR references (context): ADR-0008, ADR-0011, ADR-0003, ADR-0015.

    private const string SmokeReadyMarker = "[TEMPLATE_SMOKE_READY]";

    // ACC:T33.4
    [Fact]
    public void ShouldDefineSmokeExeScriptContract_WhenReadingSmokeExePs1()
    {
        SmokeReadyMarker.Should().NotBeNullOrWhiteSpace();
        SmokeReadyMarker.Should().Contain("TEMPLATE_SMOKE_READY");

        var repoRoot = FindRepoRootFrom(AppContext.BaseDirectory);
        var scriptPath = Path.Combine(repoRoot, "scripts", "ci", "smoke_exe.ps1");
        File.Exists(scriptPath).Should().BeTrue($"smoke exe script must exist at {scriptPath}");

        var text = File.ReadAllText(scriptPath);

        text.Should().Contain("param(", "script must declare parameters");
        text.Should().Contain("$ExePath", "script must accept a target exe path");
        text.Should().Contain("TimeoutSec", "script must allow a configurable timeout");
        text.Should().Contain("logs/ci/", "script must emit evidence under logs/ci");
        text.Should().Contain("exe.log", "script must persist combined output");
        text.Should().Contain(SmokeReadyMarker, "script must support a stable readiness marker");
        text.Should().Contain("Write-Error", "script must surface missing exe as an error");
        text.Should().Contain("Start-Process", "script must launch the exe process");
        text.Should().Contain("SMOKE INCONCLUSIVE", "script must describe the inconclusive case");
        text.Should().Contain("exit 1", "script must fail with a non-zero exit code when smoke is inconclusive");
        text.Should().Contain("SMOKE PASS (process alive)", "script must allow a deterministic pass when the process stays alive without console output");
    }

    [Fact]
    public void ShouldInvokeSmokeExeFromQualityGate_WhenWithExportIsEnabled()
    {
        var repoRoot = FindRepoRootFrom(AppContext.BaseDirectory);
        var gatePath = Path.Combine(repoRoot, "scripts", "ci", "quality_gate.ps1");
        File.Exists(gatePath).Should().BeTrue($"quality gate script must exist at {gatePath}");

        var text = File.ReadAllText(gatePath);

        text.Should().Contain("WithExport", "quality gate must support export + smoke as an opt-in step");
        text.Should().Contain("export_windows.ps1", "quality gate must call the export script");
        text.Should().Contain("smoke_exe.ps1", "quality gate must call the smoke exe script");
        text.Should().Contain("build/Game.exe", "quality gate must use a stable default output path");
        text.Should().Contain(SmokeReadyMarker, "quality gate must describe the preferred smoke marker");
    }

    private static string FindRepoRootFrom(string startDir)
    {
        var dir = new DirectoryInfo(startDir);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "Game.sln")))
                return dir.FullName;

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Unable to locate repo root (Game.sln not found).");
    }
}
