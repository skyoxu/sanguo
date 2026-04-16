using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task163SplitTests
{
    // ACC:T163.1
    [Fact]
    [Trait("acceptance", "ACC:T163.1")]
    public void ShouldWireSignalComplianceHardGateInFastModePipeline_WhenReadingGateBundleScript()
    {
        var repoRoot = FindRepoRoot();
        var runGateBundlePath = Path.Combine(repoRoot, "scripts", "python", "run_gate_bundle.py");

        File.Exists(runGateBundlePath).Should().BeTrue();

        var script = File.ReadAllText(runGateBundlePath);

        script.Should().Contain(
            "signal_compliance_workflow_hard_gate",
            "fast-mode CI should wire signal compliance report verification as a dedicated hard gate");
    }

    // ACC:T163.2
    [Fact]
    [Trait("acceptance", "ACC:T163.2")]
    public void ShouldFailWithReportMissing_WhenSignalComplianceReportDoesNotExist()
    {
        using var harness = new SignalComplianceHardGateHarness();

        var run = harness.Run("missing-report");
        var result = SingleResult(run.Summary);

        run.ExitCode.Should().Be(1);
        run.Summary.GetProperty("status").GetString().Should().Be("fail");
        run.Summary.GetProperty("failed").GetInt32().Should().Be(1);
        result.GetProperty("reason").GetString().Should().Be("report_missing");
    }

    // ACC:T163.2
    [Fact]
    [Trait("acceptance", "ACC:T163.2")]
    public void ShouldFailWithTaskIdMismatch_WhenReportTaskDoesNotMatchCurrentTask()
    {
        using var harness = new SignalComplianceHardGateHarness();
        harness.WriteReport(
            new
            {
                task_id = "T999",
                evidence_paths = new[] { "logs/ci/signal-compliance/T999/report.json" },
                is_compliant = true,
            });

        var run = harness.Run("task-id-mismatch");
        var result = SingleResult(run.Summary);

        run.ExitCode.Should().Be(1);
        result.GetProperty("reason").GetString().Should().Be("task_id_mismatch");
    }

    // ACC:T163.2
    [Fact]
    [Trait("acceptance", "ACC:T163.2")]
    public void ShouldFailWithMissingEvidencePath_WhenReportDoesNotDeclareEvidence()
    {
        using var harness = new SignalComplianceHardGateHarness();
        harness.WriteReport(
            new
            {
                task_id = "T163",
                is_compliant = true,
            });

        var run = harness.Run("missing-evidence");
        var result = SingleResult(run.Summary);

        run.ExitCode.Should().Be(1);
        result.GetProperty("reason").GetString().Should().Be("missing_evidence_path");
    }

    // ACC:T163.2
    [Fact]
    [Trait("acceptance", "ACC:T163.2")]
    public void ShouldFailWithMissingIsCompliant_WhenReportOmitsComplianceFlag()
    {
        using var harness = new SignalComplianceHardGateHarness();
        harness.WriteReport(
            new
            {
                task_id = "T163",
                evidence_paths = new[] { "logs/ci/signal-compliance/T163/report.json" },
            });

        var run = harness.Run("missing-is-compliant");
        var result = SingleResult(run.Summary);

        run.ExitCode.Should().Be(1);
        result.GetProperty("reason").GetString().Should().Be("missing_is_compliant");
    }

    // ACC:T163.3
    [Fact]
    [Trait("acceptance", "ACC:T163.3")]
    public void ShouldEmitDeterministicFailureDiagnostics_WhenReportIsNonCompliant()
    {
        using var harness = new SignalComplianceHardGateHarness();
        harness.WriteReport(
            new
            {
                task_id = "T163",
                evidence_paths = new[] { "logs/ci/signal-compliance/T163/report.json" },
                is_compliant = false,
            });

        var first = harness.Run("non-compliant-first");
        var second = harness.Run("non-compliant-second");
        var firstResult = SingleResult(first.Summary);
        var secondResult = SingleResult(second.Summary);

        first.ExitCode.Should().Be(1);
        second.ExitCode.Should().Be(1);
        firstResult.GetProperty("reason").GetString().Should().Be("non_compliant");
        secondResult.GetProperty("reason").GetString().Should().Be("non_compliant");
        firstResult.GetProperty("evidence_path").GetString().Should().Be(secondResult.GetProperty("evidence_path").GetString());
        firstResult.GetProperty("evidence_paths").EnumerateArray().Select(static item => item.GetString()).Should().Equal(
            secondResult.GetProperty("evidence_paths").EnumerateArray().Select(static item => item.GetString()),
            "failure diagnostics must be stable across identical report inputs");
    }

    private static string FindRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            var markerPath = Path.Combine(directory.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(markerPath))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new InvalidOperationException("Could not locate repository root from test base directory.");
    }

    private static JsonElement SingleResult(JsonElement summary)
    {
        var results = summary.GetProperty("results").EnumerateArray().ToArray();
        results.Should().HaveCount(1);
        return results[0];
    }

    private sealed class SignalComplianceHardGateHarness : IDisposable
    {
        private readonly string _repoRoot;
        private readonly string _workRoot;
        private readonly string _tasksBackPath;
        private readonly string _tasksGameplayPath;
        private readonly string _reportsRoot;

        public SignalComplianceHardGateHarness()
        {
            _repoRoot = FindRepoRoot();
            _workRoot = Path.Combine(Path.GetTempPath(), $"task163-hard-gate-{Guid.NewGuid():N}");
            _tasksBackPath = Path.Combine(_workRoot, "tasks_back.json");
            _tasksGameplayPath = Path.Combine(_workRoot, "tasks_gameplay.json");
            _reportsRoot = Path.Combine(_workRoot, "reports");

            Directory.CreateDirectory(_workRoot);
            Directory.CreateDirectory(_reportsRoot);
            WriteTaskFile(_tasksBackPath);
            WriteTaskFile(_tasksGameplayPath);
        }

        public void WriteReport(object payload)
        {
            var reportPath = Path.Combine(_reportsRoot, "T163", "signal-compliance-report.json");
            var reportDir = Path.GetDirectoryName(reportPath);
            reportDir.Should().NotBeNullOrWhiteSpace();
            Directory.CreateDirectory(reportDir!);
            var json = JsonSerializer.Serialize(payload);
            File.WriteAllText(reportPath, json);
        }

        public GateRunResult Run(string runName)
        {
            var summaryPath = Path.Combine(_workRoot, $"summary-{runName}.json");
            var scriptPath = Path.Combine(_repoRoot, "scripts", "python", "check_signal_compliance_workflow_hard_gate.py");

            var psi = new ProcessStartInfo("py")
            {
                WorkingDirectory = _repoRoot,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
            };
            psi.ArgumentList.Add("-3");
            psi.ArgumentList.Add(scriptPath);
            psi.ArgumentList.Add("--task-files");
            psi.ArgumentList.Add(_tasksBackPath);
            psi.ArgumentList.Add(_tasksGameplayPath);
            psi.ArgumentList.Add("--reports-root");
            psi.ArgumentList.Add(_reportsRoot);
            psi.ArgumentList.Add("--out");
            psi.ArgumentList.Add(summaryPath);

            using var process = Process.Start(psi);
            process.Should().NotBeNull();
            var stdout = process!.StandardOutput.ReadToEnd();
            var stderr = process.StandardError.ReadToEnd();
            process.WaitForExit();

            File.Exists(summaryPath).Should().BeTrue($"hard gate must emit a summary file. stdout={stdout} stderr={stderr}");
            var summary = JsonDocument.Parse(File.ReadAllText(summaryPath)).RootElement.Clone();

            return new GateRunResult(process.ExitCode, stdout, stderr, summary);
        }

        public void Dispose()
        {
            if (Directory.Exists(_workRoot))
            {
                Directory.Delete(_workRoot, recursive: true);
            }
        }

        private static void WriteTaskFile(string path)
        {
            var payload = JsonSerializer.Serialize(
                new[]
                {
                    new
                    {
                        taskmaster_id = 163,
                        status = "done",
                    },
                });
            File.WriteAllText(path, payload);
        }
    }

    private sealed record GateRunResult(int ExitCode, string Stdout, string Stderr, JsonElement Summary);
}
