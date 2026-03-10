using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class ArchitectureHotspotsGateScriptTests
{
    private static readonly Encoding Utf8NoBom = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);

    [Fact]
    public void ShouldPass_WhenHotspotWithinBudget()
    {
        var repoRoot = FindRepoRoot();
        var runId = Guid.NewGuid().ToString("N");
        var tempDir = Path.Combine(repoRoot, "logs", "ci", DateTime.UtcNow.ToString("yyyy-MM-dd"), "arch-hotspot-script", runId);
        Directory.CreateDirectory(tempDir);

        var sourcePath = Path.Combine(tempDir, "SamplePass.cs");
        File.WriteAllText(sourcePath, "public class A {\n    public void M() {}\n}\n", Utf8NoBom);

        var configPath = Path.Combine(tempDir, "config.json");
        var config = new
        {
            hotspots = new[]
            {
                new { path = sourcePath, max_lines = 20, max_methods = 5 },
            },
        };
        File.WriteAllText(configPath, JsonSerializer.Serialize(config), Utf8NoBom);

        var summaryPath = Path.Combine(tempDir, "summary-pass.json");
        var result = RunScript(repoRoot, configPath, summaryPath);

        result.ExitCode.Should().Be(0, result.CombinedOutput);
        result.Status.Should().Be("ok");
    }

    [Fact]
    public void ShouldFail_WhenHotspotExceedsBudget()
    {
        var repoRoot = FindRepoRoot();
        var runId = Guid.NewGuid().ToString("N");
        var tempDir = Path.Combine(repoRoot, "logs", "ci", DateTime.UtcNow.ToString("yyyy-MM-dd"), "arch-hotspot-script", runId);
        Directory.CreateDirectory(tempDir);

        var sourcePath = Path.Combine(tempDir, "SampleFail.cs");
        File.WriteAllText(
            sourcePath,
            "public class A {\n    public void M1() {}\n    public void M2() {}\n    public void M3() {}\n}\n",
            Utf8NoBom);

        var configPath = Path.Combine(tempDir, "config.json");
        var config = new
        {
            hotspots = new[]
            {
                new { path = sourcePath, max_lines = 3, max_methods = 2 },
            },
        };
        File.WriteAllText(configPath, JsonSerializer.Serialize(config), Utf8NoBom);

        var summaryPath = Path.Combine(tempDir, "summary-fail.json");
        var result = RunScript(repoRoot, configPath, summaryPath);

        result.ExitCode.Should().Be(1, result.CombinedOutput);
        result.Status.Should().Be("fail");
    }

    private static (int ExitCode, string Status, string CombinedOutput) RunScript(string repoRoot, string configPath, string summaryPath)
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
        psi.ArgumentList.Add("scripts/python/check_architecture_hotspots.py");
        psi.ArgumentList.Add("--config");
        psi.ArgumentList.Add(configPath);
        psi.ArgumentList.Add("--out");
        psi.ArgumentList.Add(summaryPath);
        psi.Environment["PYTHONIOENCODING"] = "utf-8";
        psi.Environment["PYTHONUTF8"] = "1";

        using var proc = Process.Start(psi);
        proc.Should().NotBeNull();
        var stdout = proc!.StandardOutput.ReadToEnd();
        var stderr = proc.StandardError.ReadToEnd();
        proc.WaitForExit(30_000).Should().BeTrue($"stdout={stdout} stderr={stderr}");

        File.Exists(summaryPath).Should().BeTrue($"stdout={stdout} stderr={stderr}");
        using var doc = JsonDocument.Parse(File.ReadAllText(summaryPath, Utf8NoBom));
        var status = doc.RootElement.GetProperty("status").GetString() ?? string.Empty;
        return (proc.ExitCode, status, stdout + Environment.NewLine + stderr);
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
