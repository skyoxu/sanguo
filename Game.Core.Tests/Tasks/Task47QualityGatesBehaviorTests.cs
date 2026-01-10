using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task47QualityGatesBehaviorTests
{
    private static readonly Encoding Utf8NoBom = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);

    // acceptance: ACC:T47.2
    [Fact]
    public void ShouldFailProcess_WhenCoverageBelowThresholdAndCoverageIsHardGate()
    {
        var repoRoot = FindRepoRoot();
        var date = DateTime.UtcNow.ToString("yyyy-MM-dd");
        var runId = Guid.NewGuid().ToString("N");
        var outDir = Path.Combine(repoRoot, "logs", "ci", date, "task47-behavior", runId, "hard");
        Directory.CreateDirectory(outDir);

        var dotnetSummaryPath = Path.Combine(outDir, "dotnet-summary.json");
        WriteDotnetSummary(
            dotnetSummaryPath,
            status: "coverage_failed",
            thresholdOk: false,
            linePct: 89.99,
            branchPct: 85.00,
            linesMin: 90.00,
            branchesMin: 85.00
        );

        var result = RunQualityGates(
            repoRoot,
            outDir,
            dotnetSummaryPath,
            additionalArgs: Array.Empty<string>(),
            additionalEnv: new()
            {
                ["QUALITY_GATES_TEST_CI_PIPELINE_RC"] = "0",
            }
        );

        result.ExitCode.Should().Be(1, "coverage hard gate should fail the process when below threshold");
        result.Summary.Status.Should().Be("fail");
        result.Summary.CoverageMode.Should().Be("hard");
        result.Summary.DotnetStatus.Should().Be("coverage_failed");
        result.Summary.DotnetThresholdOk.Should().BeFalse();
        result.Summary.DotnetCoverageLinesMin.Should().Be(90.0);
        result.Summary.DotnetCoverageBranchesMin.Should().Be(85.0);
    }

    // acceptance: ACC:T47.2
    [Fact]
    public void ShouldSucceedProcess_WhenCoverageBelowThresholdAndCoverageIsSoftGate()
    {
        var repoRoot = FindRepoRoot();
        var date = DateTime.UtcNow.ToString("yyyy-MM-dd");
        var runId = Guid.NewGuid().ToString("N");
        var outDir = Path.Combine(repoRoot, "logs", "ci", date, "task47-behavior", runId, "soft");
        Directory.CreateDirectory(outDir);

        var dotnetSummaryPath = Path.Combine(outDir, "dotnet-summary.json");
        WriteDotnetSummary(
            dotnetSummaryPath,
            status: "coverage_failed",
            thresholdOk: false,
            linePct: 89.99,
            branchPct: 85.00,
            linesMin: 90.00,
            branchesMin: 85.00
        );

        var result = RunQualityGates(
            repoRoot,
            outDir,
            dotnetSummaryPath,
            additionalArgs: new[] { "--coverage-soft" },
            additionalEnv: new()
            {
                ["QUALITY_GATES_TEST_CI_PIPELINE_RC"] = "0",
            }
        );

        result.ExitCode.Should().Be(0, "coverage soft gate should not fail the process (but still report failure in summary)");
        result.Summary.Status.Should().Be("ok");
        result.Summary.CoverageMode.Should().Be("soft");
        result.Summary.DotnetStatus.Should().Be("coverage_failed");
        result.Summary.DotnetThresholdOk.Should().BeFalse();
    }

    // acceptance: ACC:T47.3
    [Fact]
    public void ShouldFailProcess_WhenGdUnitHardGateFails_AndWriteRunSummaryPath()
    {
        var repoRoot = FindRepoRoot();
        var date = DateTime.UtcNow.ToString("yyyy-MM-dd");
        var runId = Guid.NewGuid().ToString("N");
        var outDir = Path.Combine(repoRoot, "logs", "ci", date, "task47-behavior", runId, "gdunit");
        Directory.CreateDirectory(outDir);

        var dotnetSummaryPath = Path.Combine(outDir, "dotnet-summary.json");
        WriteDotnetSummary(
            dotnetSummaryPath,
            status: "ok",
            thresholdOk: true,
            linePct: 99.99,
            branchPct: 99.99,
            linesMin: 90.00,
            branchesMin: 85.00
        );

        var gdunitRunSummaryPath = Path.Combine(outDir, "gdunit-run-summary.json");
        File.WriteAllText(
            gdunitRunSummaryPath,
            "{\"status\":\"fail\",\"suite\":\"gdunit-hard\",\"tests\":1,\"failed\":1}",
            Utf8NoBom
        );

        var result = RunQualityGates(
            repoRoot,
            outDir,
            dotnetSummaryPath,
            additionalArgs: new[] { "--gdunit-hard" },
            additionalEnv: new()
            {
                ["QUALITY_GATES_TEST_CI_PIPELINE_RC"] = "0",
                ["QUALITY_GATES_TEST_GDUNIT_RC"] = "5",
                ["QUALITY_GATES_TEST_GDUNIT_RUN_SUMMARY_JSON"] = gdunitRunSummaryPath,
                ["QUALITY_GATES_TEST_GDUNIT_REPORT_DIR"] = Path.Combine(outDir, "gdunit-hard-report"),
            }
        );

        result.ExitCode.Should().Be(1, "gdunit hard gate failure should fail the process");
        result.Summary.Status.Should().Be("fail");
        result.Summary.GdUnitEnabled.Should().BeTrue();
        result.Summary.GdUnitRc.Should().Be(5);
        result.Summary.GdUnitRunSummaryPath.Should().Be(gdunitRunSummaryPath);
        result.Summary.GdUnitRunSummaryRaw.Should().Contain("\"suite\"");
    }

    private static void WriteDotnetSummary(
        string path,
        string status,
        bool thresholdOk,
        double linePct,
        double branchPct,
        double linesMin,
        double branchesMin)
    {
        var payload = new
        {
            status,
            threshold_ok = thresholdOk,
            coverage = new
            {
                line_pct = linePct,
                branch_pct = branchPct,
                lines_min = linesMin,
                branches_min = branchesMin,
            },
        };

        var json = JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(path, json, Utf8NoBom);
    }

    private static QualityGatesRunResult RunQualityGates(
        string repoRoot,
        string outDir,
        string dotnetSummaryJson,
        string[] additionalArgs,
        System.Collections.Generic.Dictionary<string, string> additionalEnv)
    {
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
        psi.ArgumentList.Add("scripts/python/quality_gates.py");
        psi.ArgumentList.Add("all");
        psi.ArgumentList.Add("--godot-bin");
        psi.ArgumentList.Add("C:\\dummy\\godot.exe");
        psi.ArgumentList.Add("--solution");
        psi.ArgumentList.Add("Game.sln");
        psi.ArgumentList.Add("--configuration");
        psi.ArgumentList.Add("Debug");

        foreach (var a in additionalArgs)
        {
            psi.ArgumentList.Add(a);
        }

        psi.Environment["PYTHONIOENCODING"] = "utf-8";
        psi.Environment["PYTHONUTF8"] = "1";
        psi.Environment["QUALITY_GATES_TEST_MODE"] = "1";
        psi.Environment["QUALITY_GATES_TEST_OUT_DIR"] = outDir;
        psi.Environment["QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON"] = dotnetSummaryJson;

        foreach (var kv in additionalEnv)
        {
            psi.Environment[kv.Key] = kv.Value;
        }

        using var proc = Process.Start(psi);
        proc.Should().NotBeNull("quality_gates.py should be runnable via py -3");

        var stdout = proc!.StandardOutput.ReadToEnd();
        var stderr = proc.StandardError.ReadToEnd();
        proc.WaitForExit(30_000).Should().BeTrue($"quality_gates.py should exit in time. stdout={stdout} stderr={stderr}");

        var summaryPath = Path.Combine(outDir, "quality-gates-summary.json");
        File.Exists(summaryPath)
            .Should()
            .BeTrue($"Expected quality-gates summary to exist at {summaryPath}. stdout={stdout} stderr={stderr}");

        var summary = ReadSummary(summaryPath);
        return new QualityGatesRunResult(proc.ExitCode, summary, stdout, stderr);
    }

    private static QualityGatesSummary ReadSummary(string path)
    {
        var text = File.ReadAllText(path, Utf8NoBom);
        using var doc = JsonDocument.Parse(text);
        var root = doc.RootElement;

        root.TryGetProperty("status", out var statusProp).Should().BeTrue();
        root.TryGetProperty("coverage_mode", out var covModeProp).Should().BeTrue();

        root.TryGetProperty("dotnet", out var dotnet).Should().BeTrue();
        dotnet.TryGetProperty("status", out var dotnetStatus).Should().BeTrue();
        dotnet.TryGetProperty("threshold_ok", out var dotnetThresholdOk).Should().BeTrue();
        dotnet.TryGetProperty("coverage", out var coverage).Should().BeTrue();

        double? linesMin = null;
        double? branchesMin = null;
        if (coverage.ValueKind == JsonValueKind.Object)
        {
            if (coverage.TryGetProperty("lines_min", out var linesMinProp) && linesMinProp.TryGetDouble(out var lm))
                linesMin = lm;
            if (coverage.TryGetProperty("branches_min", out var branchesMinProp) && branchesMinProp.TryGetDouble(out var bm))
                branchesMin = bm;
        }

        var gdunitEnabled = false;
        var gdunitRc = -1;
        var gdunitRunSummaryPath = string.Empty;
        var gdunitRunSummaryRaw = string.Empty;

        if (root.TryGetProperty("gdunit_hard", out var gdunit) && gdunit.ValueKind == JsonValueKind.Object)
        {
            if (gdunit.TryGetProperty("enabled", out var enabledProp) && enabledProp.ValueKind == JsonValueKind.True)
                gdunitEnabled = true;
            if (gdunit.TryGetProperty("rc", out var rcProp) && rcProp.TryGetInt32(out var rci))
                gdunitRc = rci;
            if (gdunit.TryGetProperty("run_summary_path", out var rspProp) && rspProp.ValueKind == JsonValueKind.String)
                gdunitRunSummaryPath = rspProp.GetString() ?? string.Empty;
            if (gdunit.TryGetProperty("run_summary", out var rsProp) && rsProp.ValueKind != JsonValueKind.Undefined)
                gdunitRunSummaryRaw = rsProp.GetRawText();
        }

        return new QualityGatesSummary(
            statusProp.GetString() ?? string.Empty,
            covModeProp.GetString() ?? string.Empty,
            dotnetStatus.GetString() ?? string.Empty,
            dotnetThresholdOk.ValueKind == JsonValueKind.True,
            linesMin,
            branchesMin,
            gdunitEnabled,
            gdunitRc,
            gdunitRunSummaryPath,
            gdunitRunSummaryRaw
        );
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var tm = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(tm))
                return dir.FullName;
            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private readonly record struct QualityGatesSummary(
        string Status,
        string CoverageMode,
        string DotnetStatus,
        bool DotnetThresholdOk,
        double? DotnetCoverageLinesMin,
        double? DotnetCoverageBranchesMin,
        bool GdUnitEnabled,
        int GdUnitRc,
        string GdUnitRunSummaryPath,
        string GdUnitRunSummaryRaw);

    private readonly record struct QualityGatesRunResult(
        int ExitCode,
        QualityGatesSummary Summary,
        string Stdout,
        string Stderr);
}

