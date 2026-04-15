using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task91SplitTests
{
    private const int TaskId = 91;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedMandatoryAccIds =
    {
        "A-013",
        "A-014",
        "A-015",
        "A-016",
        "A-017",
        "A-018",
        "A-019",
        "A-020",
    };

    // ACC:T91.1
    [Fact]
    [Trait("acceptance", "ACC:T91.1")]
    public void ShouldRegisterRequiredStableGateUnits_WhenEnumeratingCoreAssertionRunner()
    {
        var gateUnits = CoreAssertionGateRunner.GetRequiredGateUnits();

        var mandatoryAccIds = gateUnits
            .Where(static unit => unit.IsMandatory)
            .Select(unit => unit.AccId)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static id => id, StringComparer.Ordinal)
            .ToArray();

        mandatoryAccIds.Should().Equal(
            ExpectedMandatoryAccIds,
            "the core assertion runner split must register exactly A-013~A-020 as mandatory gate units.");
    }

    // ACC:T91.2
    [Fact]
    [Trait("acceptance", "ACC:T91.2")]
    public void ShouldRejectOutOfScopeMandatoryGateUnits_WhenValidatingSplitScope()
    {
        var simulatedGateUnits = new[]
        {
            new CoreAssertionGateUnit("A-013", "A-013.ReplayTrustHash", "ReplayTrustHashPersistence", true),
            new CoreAssertionGateUnit("A-021", "A-021.Unexpected", "UnexpectedMandatoryCheck", true),
            new CoreAssertionGateUnit("A-019", "A-019.AuditRotationCap", "AuditFallbackAndRotation", true),
        };

        var simulatedOutOfScopeIds = FindOutOfScopeMandatoryIds(simulatedGateUnits);
        simulatedOutOfScopeIds.Should().ContainSingle().Which.Should().Be("A-021");

        var actualGateUnits = CoreAssertionGateRunner.GetRequiredGateUnits();
        var actualOutOfScopeIds = FindOutOfScopeMandatoryIds(actualGateUnits);
        actualOutOfScopeIds.Should().BeEmpty(
            "this split must not register mandatory gate units outside A-013~A-020.");
    }

    // ACC:T91.3
    [Fact]
    [Trait("acceptance", "ACC:T91.3")]
    public void ShouldReturnFailingExitAndSerializableSummary_WhenAnyRequiredAssertionFails()
    {
        var result = CoreAssertionGateRunner.RunWithForcedFailures(new[] { "A-013" });

        result.ExitCode.Should().NotBe(0, "runner must fail the process when any required assertion fails.");
        result.Status.Should().Be("fail");
        result.MachineReadableSummaryJson.Should().NotBeNullOrWhiteSpace();

        using var doc = JsonDocument.Parse(result.MachineReadableSummaryJson);
        var root = doc.RootElement;
        root.GetProperty("status").GetString().Should().Be("fail");

        var records = root.GetProperty("records").EnumerateArray().ToArray();
        foreach (var record in records)
        {
            var state = record.GetProperty("state").GetString();
            (string.Equals(state, CoreAssertionGateRunner.StatePass, StringComparison.Ordinal) ||
             string.Equals(state, CoreAssertionGateRunner.StateFail, StringComparison.Ordinal) ||
             string.Equals(state, CoreAssertionGateRunner.StateSkipped, StringComparison.Ordinal))
                .Should()
                .BeTrue("summary records should only use pass/fail/skipped states");

            (!string.IsNullOrWhiteSpace(record.GetProperty("stable_id").GetString()) &&
             !string.IsNullOrWhiteSpace(record.GetProperty("check").GetString()))
                .Should()
                .BeTrue("summary record stable_id/check should be non-empty");

            record.TryGetProperty("mandatory", out _)
                .Should()
                .BeTrue("summary record should include mandatory field");
        }

        var mandatoryByAccId = CoreAssertionGateRunner.GetRequiredGateUnits()
            .ToDictionary(unit => unit.AccId, unit => unit.IsMandatory, StringComparer.Ordinal);
        foreach (var record in records)
        {
            var accId = record.GetProperty("acc_id").GetString() ?? string.Empty;
            var mandatory = record.GetProperty("mandatory").GetBoolean();
            (mandatoryByAccId.TryGetValue(accId, out var expected) && expected == mandatory)
                .Should()
                .BeTrue("summary record mandatory field should match runner gate unit metadata");
        }

        records.Should().Contain(record =>
            string.Equals(record.GetProperty("state").GetString(), CoreAssertionGateRunner.StateFail, StringComparison.OrdinalIgnoreCase));
        records.Should().Contain(record =>
            !string.IsNullOrWhiteSpace(record.GetProperty("message").GetString()) &&
            record.GetProperty("message").GetString()!.Length >= 10);
    }

    // ACC:T91.4
    [Fact]
    [Trait("acceptance", "ACC:T91.4")]
    public void ShouldExposeAuditableGranularity_WhenEnumeratingMandatoryGateChecks()
    {
        var gateUnits = CoreAssertionGateRunner.GetRequiredGateUnits();
        gateUnits.Should().NotBeEmpty("runner must expose auditable gate-unit enumeration.");

        var mandatoryGateUnits = gateUnits.Where(static unit => unit.IsMandatory).ToArray();
        mandatoryGateUnits.Should().NotBeEmpty("auditable checks must include mandatory assertions.");

        var groupsByCheckName = mandatoryGateUnits
            .GroupBy(unit => unit.CheckName, StringComparer.Ordinal)
            .ToArray();

        groupsByCheckName.Should().OnlyContain(group => !string.IsNullOrWhiteSpace(group.Key));
        groupsByCheckName.Should().HaveCountGreaterThan(1, "a monolithic runner with one opaque check is not acceptable.");
        groupsByCheckName.Should().OnlyContain(group =>
            group.Select(unit => unit.AccId).Distinct(StringComparer.Ordinal).Count() <= 2,
            "each check should map to one assertion or a tightly related pair.");
    }

    // ACC:T91.5
    [Fact]
    [Trait("acceptance", "ACC:T91.5")]
    public void ShouldReuseExistingPipelineEvidencePath_WhenResolvingCoreRunnerEntrypoints()
    {
        var repoRoot = FindRepoRoot();
        var runGateBundlePath = Path.Combine(repoRoot, "scripts", "python", "run_gate_bundle.py");
        var runReviewPipelinePath = Path.Combine(repoRoot, "scripts", "sc", "run_review_pipeline.py");
        var pipelinePlanPath = Path.Combine(repoRoot, "scripts", "sc", "_pipeline_plan.py");
        var acceptanceCheckPath = Path.Combine(repoRoot, "scripts", "sc", "acceptance_check.py");
        var devCliPath = Path.Combine(repoRoot, "scripts", "python", "dev_cli.py");
        var task91SplitTestsPath = Path.Combine(repoRoot, "Game.Core.Tests", "Tasks", "Task91SplitTests.cs");

        File.Exists(runGateBundlePath).Should().BeTrue();
        File.Exists(runReviewPipelinePath).Should().BeTrue();
        File.Exists(pipelinePlanPath).Should().BeTrue();
        File.Exists(acceptanceCheckPath).Should().BeTrue();
        File.Exists(devCliPath).Should().BeTrue();
        File.Exists(task91SplitTestsPath).Should().BeTrue();

        var combined = new StringBuilder()
            .AppendLine(File.ReadAllText(runGateBundlePath))
            .AppendLine(File.ReadAllText(runReviewPipelinePath))
            .ToString();
        var pipelinePlan = File.ReadAllText(pipelinePlanPath);
        var acceptanceCheck = File.ReadAllText(acceptanceCheckPath);
        var devCli = File.ReadAllText(devCliPath);
        var task91SplitTests = File.ReadAllText(task91SplitTestsPath);

        combined.Should().Contain("logs/ci", "runner artifacts must remain in existing CI evidence paths.");
        combined.Should().Contain("summary.json", "runner integration must emit summary artifact through existing pipeline.");
        combined.Should().Contain(
            "scripts/sc/acceptance_check.py",
            "review pipeline must keep calling the acceptance entrypoint.");
        pipelinePlan.Should().Contain(
            "scripts/sc/test.py",
            "pipeline plan must keep executing task-scoped tests before reviewer stages.");
        pipelinePlan.Should().Contain(
            "--task-id",
            "pipeline test/acceptance commands should remain task-scoped.");
        pipelinePlan.Should().Contain(
            "--out-per-task",
            "acceptance command builder should keep task-scoped evidence routing enabled.");
        acceptanceCheck.Should().Contain(
            "sc-acceptance-check-task-",
            "acceptance check runtime must emit task-scoped evidence directories.");
        combined.Should().NotContain(
            "logs/core-assertion",
            "runner must not introduce a parallel reporting channel.");
        devCli.Should().Contain(
            "run-acceptance-preflight",
            "dev_cli should keep acceptance preflight entrypoint available for chapter workflows.");
        task91SplitTests.Should().Contain(
            "CoreAssertionGateRunner.Run(",
            "task-scoped tests should keep binding the split runner success path.");
        task91SplitTests.Should().Contain(
            "CoreAssertionGateRunner.RunWithForcedFailures(",
            "task-scoped tests should keep binding the split runner failure path.");

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptanceRefs.Should().Contain("A-013~A-020");
            testRefs.Should().Contain("Game.Core.Tests/Tasks/Task91SplitTests.cs");
        }

        var result = CoreAssertionGateRunner.Run();
        using var doc = JsonDocument.Parse(result.MachineReadableSummaryJson);
        var actualAccIds = doc.RootElement.GetProperty("records")
            .EnumerateArray()
            .Where(record => record.GetProperty("mandatory").GetBoolean())
            .Select(record => record.GetProperty("acc_id").GetString() ?? string.Empty)
            .Where(static id => !string.IsNullOrWhiteSpace(id))
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static id => id, StringComparer.Ordinal)
            .ToArray();

        actualAccIds.Should().Equal(
            ExpectedMandatoryAccIds,
            "runner evidence must contain task 91 mandatory assertion records (A-013~A-020).");
    }

    // ACC:T91.6
    [Fact]
    [Trait("acceptance", "ACC:T91.6")]
    public void ShouldKeepTaskSpecificDeterministicEvidence_WhenReadingTask91FromTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");
            var testStrategy = ReadStringArray(task, "test_strategy");

            acceptanceRefs.Should().Equal("A-013~A-020");
            acceptance.Should().HaveCount(6);
            acceptance.Should().OnlyContain(item =>
                item.Contains("Game.Core.Tests/Tasks/Task91SplitTests.cs", StringComparison.Ordinal));

            testRefs.Should().Contain("Game.Core.Tests/Tasks/Task91SplitTests.cs");
            testStrategy.Should().Contain("Task-specific deterministic tests.");
        }
    }

    // ACC:T91.3
    [Fact]
    [Trait("acceptance", "ACC:T91.3")]
    public void ShouldReturnPassingExitAndSerializableSummary_WhenAllRequiredAssertionsPass()
    {
        var result = CoreAssertionGateRunner.Run();

        result.ExitCode.Should().Be(0);
        result.Status.Should().Be("ok");

        using var doc = JsonDocument.Parse(result.MachineReadableSummaryJson);
        var root = doc.RootElement;
        root.GetProperty("status").GetString().Should().Be("ok");

        var records = root.GetProperty("records").EnumerateArray().ToArray();
        records.Should().HaveCount(ExpectedMandatoryAccIds.Length);
        records.Should().OnlyContain(record =>
            string.Equals(record.GetProperty("state").GetString(), CoreAssertionGateRunner.StatePass, StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T91.3
    [Fact]
    [Trait("acceptance", "ACC:T91.3")]
    public void ShouldEmitSkippedState_WhenEvidenceSourceIsDisabledForCurrentRun()
    {
        var result = CoreAssertionGateRunner.Run(CoreAssertionGateExecutionInputs.AllPassing with
        {
            EnableRetentionWindowEvidence = false,
        });

        result.ExitCode.Should().Be(0, "disabled evidence should emit skipped rather than hard fail");
        result.Status.Should().Be("ok");

        using var doc = JsonDocument.Parse(result.MachineReadableSummaryJson);
        var records = doc.RootElement.GetProperty("records").EnumerateArray().ToArray();
        records.Should().Contain(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-017", StringComparison.Ordinal) &&
            string.Equals(record.GetProperty("state").GetString(), CoreAssertionGateRunner.StateSkipped, StringComparison.Ordinal));
    }

    // ACC:T91.1
    [Fact]
    [Trait("acceptance", "ACC:T91.1")]
    public void ShouldBindAccT_WhenContractOrderingRulesRefIsRequiredByRunnerUnits()
    {
        var accIds = CoreAssertionGateRunner.GetRequiredGateUnits()
            .Select(unit => unit.AccId)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static id => id, StringComparer.Ordinal)
            .ToArray();

        accIds.Should().Equal(
            ExpectedMandatoryAccIds,
            "contract ordering references for task 91 should stay aligned with full mandatory scope A-013~A-020.");
    }

    // ACC:T91.5
    [Fact]
    [Trait("acceptance", "ACC:T91.5")]
    public void ShouldBindAccT_WhenContractEventsRefIsRequiredByPipelineEvidencePath()
    {
        var result = CoreAssertionGateRunner.Run();
        var semanticFailResult = CoreAssertionGateRunner.Run(CoreAssertionGateExecutionInputs.AllPassing with
        {
            HasContractCompatibilityEvidence = false,
        });
        using var doc = JsonDocument.Parse(result.MachineReadableSummaryJson);
        var records = doc.RootElement.GetProperty("records").EnumerateArray().ToArray();
        using var failDoc = JsonDocument.Parse(semanticFailResult.MachineReadableSummaryJson);
        var failRecords = failDoc.RootElement.GetProperty("records").EnumerateArray().ToArray();

        records.Should().Contain(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-020", StringComparison.Ordinal) &&
            string.Equals(record.GetProperty("state").GetString(), CoreAssertionGateRunner.StatePass, StringComparison.Ordinal) &&
            !string.IsNullOrWhiteSpace(record.GetProperty("stable_id").GetString()) &&
            !string.IsNullOrWhiteSpace(record.GetProperty("check").GetString()));

        semanticFailResult.ExitCode.Should().NotBe(0);
        semanticFailResult.Status.Should().Be("fail");
        failRecords.Should().Contain(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-020", StringComparison.Ordinal) &&
            string.Equals(record.GetProperty("state").GetString(), CoreAssertionGateRunner.StateFail, StringComparison.Ordinal) &&
            record.GetProperty("message").GetString()!.Contains("disabled by inputs", StringComparison.Ordinal));
    }

    private static IReadOnlyList<string> FindOutOfScopeMandatoryIds(IEnumerable<CoreAssertionGateUnit> gateUnits)
    {
        var requiredIds = new HashSet<string>(ExpectedMandatoryAccIds, StringComparer.Ordinal);

        return gateUnits
            .Where(static unit => unit.IsMandatory)
            .Select(unit => unit.AccId)
            .Where(id => !requiredIds.Contains(id))
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static id => id, StringComparer.Ordinal)
            .ToArray();
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

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private static JsonElement GetTaskByTaskmasterId(string repoRoot, string fileName, int taskmasterId)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        foreach (var task in doc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var idProperty) &&
                idProperty.ValueKind == JsonValueKind.Number &&
                idProperty.TryGetInt32(out var idValue) &&
                idValue == taskmasterId)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task {taskmasterId} not found in {fileName}.");
    }

    private static string[] ReadStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property)
            .Should().BeTrue($"Task {TaskId} must contain '{propertyName}'.");

        property.ValueKind.Should().Be(JsonValueKind.Array);

        return property
            .EnumerateArray()
            .Select(static item => item.GetString() ?? string.Empty)
            .ToArray();
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] relativeParts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(relativeParts).ToArray());
        var text = File.ReadAllText(path);
        return JsonDocument.Parse(text);
    }
}
