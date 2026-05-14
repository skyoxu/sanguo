using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task47QualityGatesArchitectureHotspotsTests
{
    private static readonly Encoding Utf8NoBom = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);

    [Fact]
    public void ShouldFailProcess_WhenArchitectureHotspotsGateFails()
    {
        var repoRoot = FindRepoRoot();
        var date = DateTime.UtcNow.ToString("yyyy-MM-dd");
        var runId = Guid.NewGuid().ToString("N");
        var outDir = Path.Combine(repoRoot, "logs", "ci", date, "task47-arch-hotspots", runId);
        Directory.CreateDirectory(outDir);

        var dotnetSummaryPath = Path.Combine(outDir, "dotnet-summary.json");
        WriteDotnetSummary(dotnetSummaryPath);

        var result = RunQualityGates(
            repoRoot,
            outDir,
            dotnetSummaryPath,
            additionalEnv: new()
            {
                ["QUALITY_GATES_TEST_CI_PIPELINE_RC"] = "0",
                ["QUALITY_GATES_TEST_ARCH_HOTSPOTS_RC"] = "3",
            });

        result.ExitCode.Should().Be(1);
        result.Status.Should().Be("fail");
        result.ArchitectureHotspotsRc.Should().Be(3);
    }

    private static void WriteDotnetSummary(string path)
    {
        var payload = new
        {
            status = "ok",
            threshold_ok = true,
            coverage = new
            {
                line_pct = 100.0,
                branch_pct = 100.0,
                lines_min = 90.0,
                branches_min = 85.0,
            },
        };

        var json = JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(path, json, Utf8NoBom);
    }

    private static (int ExitCode, string Status, int ArchitectureHotspotsRc) RunQualityGates(
        string repoRoot,
        string outDir,
        string dotnetSummaryJson,
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
        psi.ArgumentList.Add("--require-arch-hotspots");

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
        proc.Should().NotBeNull();
        var stdout = proc!.StandardOutput.ReadToEnd();
        var stderr = proc.StandardError.ReadToEnd();
        proc.WaitForExit(30_000).Should().BeTrue($"stdout={stdout} stderr={stderr}");

        var summaryPath = Path.Combine(outDir, "quality-gates-summary.json");
        File.Exists(summaryPath).Should().BeTrue($"stdout={stdout} stderr={stderr}");
        using var doc = JsonDocument.Parse(File.ReadAllText(summaryPath, Utf8NoBom));
        var root = doc.RootElement;
        var status = root.GetProperty("status").GetString() ?? string.Empty;
        var archRc = root.GetProperty("architecture_hotspots").GetProperty("rc").GetInt32();
        return (proc.ExitCode, status, archRc);
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found.");
    }
}
