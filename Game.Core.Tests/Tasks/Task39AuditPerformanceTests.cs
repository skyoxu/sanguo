using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task39AuditPerformanceTests
{
    private static readonly Encoding Utf8NoBom = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false);

    // ACC:T39.1
    // ADR: ADR-0015 (performance budgets), ADR-0005 (quality gates)
    [Fact]
    public void ShouldFailPerfValidation_WhenP95ExceedsBudget()
    {
        var repoRoot = FindRepoRoot();
        var date = "2099-01-01";

        var perfDir = Path.Combine(repoRoot, "logs", "perf", date);
        Directory.CreateDirectory(perfDir);

        var perfSummaryPath = Path.Combine(perfDir, "summary.json");
        File.WriteAllText(
            perfSummaryPath,
            "{\"p95_ms\":25.0,\"p50_ms\":10.0,\"avg_ms\":12.0,\"p99_ms\":40.0,\"frames\":120}",
            Utf8NoBom
        );

        var ciDir = Path.Combine(repoRoot, "logs", "ci", date);
        Directory.CreateDirectory(ciDir);

        var outPath = Path.Combine(ciDir, "quality-gates-perf.json");

        var result = RunPy(
            repoRoot,
            new[]
            {
                "-3",
                "scripts/python/validate_perf.py",
                "--date",
                date,
                "--out",
                outPath,
                "--max-p95-ms",
                "17",
            }
        );

        result.ExitCode.Should().Be(1, $"perf validation should fail when p95_ms exceeds max_p95_ms. stdout={result.Stdout} stderr={result.Stderr}");
        File.Exists(outPath).Should().BeTrue("validator should write a JSON artifact even on failure");

        using var doc = JsonDocument.Parse(File.ReadAllText(outPath, Utf8NoBom));
        doc.RootElement.ValueKind.Should().Be(JsonValueKind.Object);
        doc.RootElement.TryGetProperty("ok", out _).Should().BeTrue("artifact should contain an 'ok' field");
    }

    // ACC:T39.2
    // ADR: ADR-0019 (security baseline), ADR-0005 (quality gates)
    [Fact]
    public void ShouldFailAuditJsonlValidation_WhenAnyLineIsMissingRequiredField()
    {
        var repoRoot = FindRepoRoot();
        var date = "2099-01-01";

        var ciDir = Path.Combine(repoRoot, "logs", "ci", date);
        Directory.CreateDirectory(ciDir);

        var auditPath = Path.Combine(ciDir, "security-audit.jsonl");
        File.WriteAllText(
            auditPath,
            "{\"ts\":\"2099-01-01T00:00:00Z\",\"action\":\"open_url\",\"reason\":\"deny\",\"target\":\"https://example.com\",\"caller\":\"Task39AuditPerformanceTests\"}\n"
            + "{\"ts\":\"2099-01-01T00:00:01Z\",\"action\":\"open_url\",\"reason\":\"deny\",\"target\":\"https://example.com\"}\n",
            Utf8NoBom
        );

        var outPath = Path.Combine(ciDir, "quality-gates-audit.json");

        var result = RunPy(
            repoRoot,
            new[]
            {
                "-3",
                "scripts/python/validate_audit_logs.py",
                "--date",
                date,
                "--out",
                outPath,
            }
        );

        result.ExitCode.Should().Be(1, $"audit JSONL validator should fail when required fields are missing. stdout={result.Stdout} stderr={result.Stderr}");
        File.Exists(outPath).Should().BeTrue("validator should write a JSON artifact even on failure");

        using var doc = JsonDocument.Parse(File.ReadAllText(outPath, Utf8NoBom));
        doc.RootElement.ValueKind.Should().Be(JsonValueKind.Object);
        doc.RootElement.TryGetProperty("ok", out _).Should().BeTrue("artifact should contain an 'ok' field");
    }

    [Fact]
    public void ShouldFailAuditJsonlValidation_WhenAnyLineIsInvalidJson()
    {
        var repoRoot = FindRepoRoot();
        var date = "2099-01-02";

        var ciDir = Path.Combine(repoRoot, "logs", "ci", date);
        Directory.CreateDirectory(ciDir);

        var auditPath = Path.Combine(ciDir, "security-audit.jsonl");
        File.WriteAllText(
            auditPath,
            "{\n",
            Utf8NoBom
        );

        var outPath = Path.Combine(ciDir, "quality-gates-audit.json");

        var result = RunPy(
            repoRoot,
            new[]
            {
                "-3",
                "scripts/python/validate_audit_logs.py",
                "--date",
                date,
                "--out",
                outPath,
            }
        );

        result.ExitCode.Should().Be(1, "audit JSONL validator should fail when any line is invalid JSON");
        File.Exists(outPath).Should().BeTrue("validator should write a JSON artifact even on failure");

        using var doc = JsonDocument.Parse(File.ReadAllText(outPath, Utf8NoBom));
        doc.RootElement.GetProperty("ok").GetBoolean().Should().BeFalse();
        doc.RootElement.TryGetProperty("results", out var results).Should().BeTrue();
        results.ValueKind.Should().Be(JsonValueKind.Array);
        results.GetArrayLength().Should().Be(1);
        results[0].GetProperty("error").GetString().Should().NotBeNull();
        results[0].GetProperty("error").GetString()!.Should().StartWith("invalid_json:");
    }

    [Fact]
    public void ShouldPassAuditJsonlValidation_WhenAllLinesHaveRequiredFields()
    {
        var repoRoot = FindRepoRoot();
        var date = "2099-01-03";

        var ciDir = Path.Combine(repoRoot, "logs", "ci", date);
        Directory.CreateDirectory(ciDir);

        var auditPath = Path.Combine(ciDir, "security-audit.jsonl");
        File.WriteAllText(
            auditPath,
            "{"
            + "\"ts\":\"2099-01-03T00:00:00Z\","
            + "\"action\":\"open_url\","
            + "\"reason\":\"deny\","
            + "\"target\":\"https://example.com\","
            + "\"caller\":\"Task39AuditPerformanceTests\""
            + "}\n",
            Utf8NoBom
        );

        var outPath = Path.Combine(ciDir, "quality-gates-audit.json");

        var result = RunPy(
            repoRoot,
            new[]
            {
                "-3",
                "scripts/python/validate_audit_logs.py",
                "--date",
                date,
                "--out",
                outPath,
            }
        );

        result.ExitCode.Should().Be(0, "audit JSONL validator should succeed when all lines have required fields");
        File.Exists(outPath).Should().BeTrue();

        using var doc = JsonDocument.Parse(File.ReadAllText(outPath, Utf8NoBom));
        doc.RootElement.GetProperty("ok").GetBoolean().Should().BeTrue();
    }

    [Fact]
    public void ShouldPassPerfValidation_WhenP95WithinBudget()
    {
        var repoRoot = FindRepoRoot();
        var date = "2099-01-04";

        var perfDir = Path.Combine(repoRoot, "logs", "perf", date);
        Directory.CreateDirectory(perfDir);

        var perfSummaryPath = Path.Combine(perfDir, "summary.json");
        File.WriteAllText(
            perfSummaryPath,
            "{\"p95_ms\":10.0,\"frames\":120}",
            Utf8NoBom
        );

        var ciDir = Path.Combine(repoRoot, "logs", "ci", date);
        Directory.CreateDirectory(ciDir);

        var outPath = Path.Combine(ciDir, "quality-gates-perf.json");

        var result = RunPy(
            repoRoot,
            new[]
            {
                "-3",
                "scripts/python/validate_perf.py",
                "--date",
                date,
                "--out",
                outPath,
                "--max-p95-ms",
                "17",
            }
        );

        result.ExitCode.Should().Be(0, "perf validation should succeed when p95_ms is within budget");
        File.Exists(outPath).Should().BeTrue();

        using var doc = JsonDocument.Parse(File.ReadAllText(outPath, Utf8NoBom));
        doc.RootElement.GetProperty("ok").GetBoolean().Should().BeTrue();
        doc.RootElement.GetProperty("p95_ms").GetDouble().Should().BeApproximately(10.0, 0.001);
    }

    // ACC:T39.3
    // ADR: ADR-0005 (quality gates)
    [Fact]
    public void GivenInvalidPerfAndAudit_WhenRunningQualityGatesAll_ThenProcessFailsAndWritesArtifactPaths()
    {
        var repoRoot = FindRepoRoot();
        var date = DateTime.Today.ToString("yyyy-MM-dd");

        var perfDir = Path.Combine(repoRoot, "logs", "perf", date);
        Directory.CreateDirectory(perfDir);
        File.WriteAllText(
            Path.Combine(perfDir, "summary.json"),
            "{\"p95_ms\":999.0,\"frames\":120}",
            Utf8NoBom
        );

        var ciDir = Path.Combine(repoRoot, "logs", "ci", date);
        Directory.CreateDirectory(ciDir);
        File.WriteAllText(
            Path.Combine(ciDir, "security-audit.jsonl"),
            "{\"ts\":\"2099-01-01T00:00:00Z\",\"action\":\"open_url\",\"reason\":\"deny\",\"target\":\"https://example.com\"}\n",
            Utf8NoBom
        );

        var runId = Guid.NewGuid().ToString("N");
        var taskOutDir = Path.Combine(ciDir, "task39", runId);
        Directory.CreateDirectory(taskOutDir);

        var dotnetSummaryPath = Path.Combine(taskOutDir, "dotnet-summary.json");
        File.WriteAllText(
            dotnetSummaryPath,
            "{\"status\":\"ok\",\"threshold_ok\":true,\"coverage\":{\"lines_min\":90.0,\"branches_min\":85.0}}",
            Utf8NoBom
        );

        var result = RunPy(
            repoRoot,
            new[]
            {
                "-3",
                "scripts/python/quality_gates.py",
                "all",
                "--solution",
                "Game.sln",
                "--configuration",
                "Debug",
                "--godot-bin",
                "C:/Dummy/Godot.exe",
            },
            additionalEnv: new()
            {
                ["QUALITY_GATES_TEST_MODE"] = "1",
                ["QUALITY_GATES_TEST_OUT_DIR"] = ciDir,
                ["QUALITY_GATES_TEST_CI_PIPELINE_RC"] = "0",
                ["QUALITY_GATES_TEST_DOTNET_SUMMARY_JSON"] = dotnetSummaryPath,
            }
        );

        result.ExitCode.Should().Be(1, $"quality_gates.py all should fail when perf/audit validation fails. stdout={result.Stdout} stderr={result.Stderr}");
        result.Stdout.Should().Contain("VALIDATE_PERF", "quality gates should emit a visible perf validation summary line");
        result.Stdout.Should().Contain("VALIDATE_AUDIT_LOGS", "quality gates should emit a visible audit JSONL validation summary line");

        var summaryPath = Path.Combine(ciDir, "quality-gates-summary.json");
        File.Exists(summaryPath).Should().BeTrue("quality_gates.py should write a stable summary artifact");

        using var summaryDoc = JsonDocument.Parse(File.ReadAllText(summaryPath, Utf8NoBom));
        summaryDoc.RootElement.TryGetProperty("artifacts", out var artifacts).Should().BeTrue("summary should include artifact paths");
        artifacts.ValueKind.Should().Be(JsonValueKind.Object);
        artifacts.TryGetProperty("quality_gates_perf", out _).Should().BeTrue("summary should include a perf validation artifact path");
        artifacts.TryGetProperty("quality_gates_audit", out _).Should().BeTrue("summary should include an audit JSONL validation artifact path");

        var perfArtifactPath = artifacts.GetProperty("quality_gates_perf").GetString();
        var auditArtifactPath = artifacts.GetProperty("quality_gates_audit").GetString();
        perfArtifactPath.Should().NotBeNullOrWhiteSpace();
        auditArtifactPath.Should().NotBeNullOrWhiteSpace();

        File.Exists(perfArtifactPath!).Should().BeTrue("perf validation should write an artifact file");
        File.Exists(auditArtifactPath!).Should().BeTrue("audit validation should write an artifact file");

        using var perfDoc = JsonDocument.Parse(File.ReadAllText(perfArtifactPath!, Utf8NoBom));
        perfDoc.RootElement.GetProperty("ok").GetBoolean().Should().BeFalse();
        perfDoc.RootElement.TryGetProperty("p95_ms", out _).Should().BeTrue();
        perfDoc.RootElement.TryGetProperty("max_p95_ms", out _).Should().BeTrue();

        using var auditDoc = JsonDocument.Parse(File.ReadAllText(auditArtifactPath!, Utf8NoBom));
        auditDoc.RootElement.GetProperty("ok").GetBoolean().Should().BeFalse();
        auditDoc.RootElement.TryGetProperty("required_keys", out _).Should().BeTrue();
        auditDoc.RootElement.TryGetProperty("results", out var auditResults).Should().BeTrue();
        auditResults.ValueKind.Should().Be(JsonValueKind.Array);
    }

    // ACC:T39.4
    [Fact]
    public void ShouldHaveExpectedMigrationDocs_WhenValidatingReferences()
    {
        var repoRoot = FindRepoRoot();

        var p13 = Path.Combine(repoRoot, "docs", "migration", "Phase-13-Quality-Gates-Backlog.md");
        var p15 = Path.Combine(repoRoot, "docs", "migration", "Phase-15-Performance-Budgets-and-Gates.md");

        File.Exists(p13).Should().BeTrue("expected migration doc referenced by acceptance");
        File.Exists(p15).Should().BeTrue("expected migration doc referenced by acceptance");

        new FileInfo(p13).Length.Should().BeGreaterThan(0, "expected doc to be non-empty");
        new FileInfo(p15).Length.Should().BeGreaterThan(0, "expected doc to be non-empty");
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

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json). ");
    }

    private static PyRunResult RunPy(string repoRoot, string[] args, System.Collections.Generic.Dictionary<string, string>? additionalEnv = null)
    {
        var psi = new ProcessStartInfo("py")
        {
            WorkingDirectory = repoRoot,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };

        foreach (var a in args)
        {
            psi.ArgumentList.Add(a);
        }

        psi.Environment["PYTHONIOENCODING"] = "utf-8";
        psi.Environment["PYTHONUTF8"] = "1";

        if (additionalEnv is not null)
        {
            foreach (var kv in additionalEnv)
            {
                psi.Environment[kv.Key] = kv.Value;
            }
        }

        using var proc = Process.Start(psi);
        proc.Should().NotBeNull("Python launcher 'py' should be available on Windows");

        var stdout = proc!.StandardOutput.ReadToEnd();
        var stderr = proc.StandardError.ReadToEnd();
        proc.WaitForExit(30_000).Should().BeTrue($"process should exit in time. stdout={stdout} stderr={stderr}");

        return new PyRunResult(proc.ExitCode, stdout, stderr);
    }

    private readonly record struct PyRunResult(int ExitCode, string Stdout, string Stderr);
}
