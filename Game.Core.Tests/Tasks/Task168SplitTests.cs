using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task168SplitTests
{
    private const string TaskSpecificEvidenceRef = "Game.Core.Tests/Tasks/Task168SplitTests.cs";

    // ACC:T168.1
    [Fact]
    [Trait("acceptance", "ACC:T168.1")]
    public void ShouldInvokeValidatorExactlyOnceViaPipelineEntry_AndEmitStandardizedDiagnostics_WhenCompatibilityValidationFails()
    {
        var validator = new CountingValidator(new AlwaysFailingCompatibilityValidator());
        var pipeline = new MigrationCompatibilityPipelineEntry(new MigrationCompatibilityCiHardGate(validator));
        var report = new MigrationCompatibilityReport(
            new[] { "Assertions", "Gates", "DeterministicTests" });
        var evidenceLinks = new[]
        {
            "logs/ci/2026-05-01/task168/assertions.json",
            TaskSpecificEvidenceRef,
        };

        var result = pipeline.RunHardGate(report, evidenceLinks, TaskSpecificEvidenceRef, rolloutMode: true);

        validator.CallCount.Should().Be(1, "pipeline entry must invoke validator exactly once for the current report");
        result.IsSuccess.Should().BeFalse();
        result.Diagnostics.Should().ContainSingle();

        var diagnostic = result.Diagnostics.Single();
        diagnostic.Code.Should().Be("COMPAT_VALIDATION_FAILED");
        diagnostic.Message.Should().StartWith("[compat-validator]");
    }

    // ACC:T168.2
    [Fact]
    [Trait("acceptance", "ACC:T168.2")]
    public void ShouldRefusePipelineAdvance_WhenCompatibilityValidationFails()
    {
        var gate = new MigrationCompatibilityCiHardGate(new DefaultCompatibilityValidator());
        var report = new MigrationCompatibilityReport(
            new[] { "Assertions", "Gates", "DeterministicTests" });
        var evidenceLinks = new[]
        {
            "logs/ci/2026-05-01/task168/assertions.json",
            TaskSpecificEvidenceRef,
        };

        var result = gate.Evaluate(report, evidenceLinks, TaskSpecificEvidenceRef);

        result.IsSuccess.Should().BeFalse("failed compatibility validation must stop CI stage progression");
        result.AdvanceAllowed.Should().BeFalse("pipeline must refuse to advance when hard-gate validation fails");
        result.ExitCode.Should().Be(1, "failed hard gate should map to non-zero pipeline exit code");
        result.StageState.Should().Be("blocked", "failed hard gate should produce a deterministic blocked stage state");
    }

    // ACC:T168.3
    [Fact]
    [Trait("acceptance", "ACC:T168.3")]
    public void ShouldReturnDeterministicDiagnostics_WhenSameInvalidReportIsValidatedTwice()
    {
        var gate = new MigrationCompatibilityCiHardGate(new DefaultCompatibilityValidator());
        var report = new MigrationCompatibilityReport(
            new[] { "Assertions", "Gates", "DeterministicTests" });
        var evidenceLinks = new[]
        {
            "logs/ci/2026-05-01/task168/assertions.json",
            TaskSpecificEvidenceRef,
        };

        var firstResult = gate.Evaluate(report, evidenceLinks, TaskSpecificEvidenceRef);
        var secondResult = gate.Evaluate(report, evidenceLinks, TaskSpecificEvidenceRef);

        firstResult.ExitCode.Should().Be(1);
        secondResult.ExitCode.Should().Be(1);
        firstResult.StageState.Should().Be(secondResult.StageState);
        firstResult.AdvanceAllowed.Should().BeFalse();
        secondResult.AdvanceAllowed.Should().BeFalse();
        firstResult.Diagnostics.Should().BeEquivalentTo(
            secondResult.Diagnostics,
            options => options.WithStrictOrdering());
    }

    // ACC:T168.4
    [Fact]
    [Trait("acceptance", "ACC:T168.4")]
    public void ShouldAllowPipelineAdvance_WhenCompatibilityValidationSucceeds()
    {
        var gate = new MigrationCompatibilityCiHardGate(new DefaultCompatibilityValidator());
        var report = new MigrationCompatibilityReport(
            new[] { "Assertions", "Gates", "ScenarioEvidence", "DeterministicTests" });
        var evidenceLinks = new[]
        {
            "logs/ci/2026-05-01/task168/assertions.json",
            "logs/ci/2026-05-01/task168/completeness.json",
            TaskSpecificEvidenceRef,
        };

        var result = gate.Evaluate(report, evidenceLinks, TaskSpecificEvidenceRef);

        result.IsSuccess.Should().BeTrue();
        result.AdvanceAllowed.Should().BeTrue();
        result.ExitCode.Should().Be(0);
        result.StageState.Should().Be("ready");
        result.Diagnostics.Should().BeEmpty();
    }

    // ACC:T168.5
    [Fact]
    [Trait("acceptance", "ACC:T168.5")]
    public void ShouldKeepHardGateBlockingInRolloutMode_WhenCompatibilityValidationFails()
    {
        var pipeline = new MigrationCompatibilityPipelineEntry(
            new MigrationCompatibilityCiHardGate(new AlwaysFailingCompatibilityValidator()));
        var report = new MigrationCompatibilityReport(
            new[] { "Assertions", "Gates", "DeterministicTests" });
        var evidenceLinks = new[]
        {
            "logs/ci/2026-05-01/task168/assertions.json",
            TaskSpecificEvidenceRef,
        };

        var result = pipeline.RunHardGate(report, evidenceLinks, TaskSpecificEvidenceRef, rolloutMode: true);

        result.IsSuccess.Should().BeFalse();
        result.AdvanceAllowed.Should().BeFalse();
        result.ExitCode.Should().Be(1);
        result.StageState.Should().Be("blocked");
    }

    private sealed class MigrationCompatibilityPipelineEntry(MigrationCompatibilityCiHardGate hardGate)
    {
        public MigrationCompatibilityCiHardGateResult RunHardGate(
            MigrationCompatibilityReport report,
            IReadOnlyCollection<string> evidenceLinks,
            string taskSpecificEvidenceRef,
            bool rolloutMode)
        {
            rolloutMode.Should().BeTrue("this split task models rollout mode as default-enabled for the target CI lane");
            return hardGate.Evaluate(report, evidenceLinks, taskSpecificEvidenceRef);
        }
    }

    private sealed class MigrationCompatibilityCiHardGate(ICompatibilityValidator validator)
    {
        public MigrationCompatibilityCiHardGateResult Evaluate(
            MigrationCompatibilityReport report,
            IReadOnlyCollection<string> evidenceLinks,
            string taskSpecificEvidenceRef)
        {
            var validation = validator.Validate(report, evidenceLinks, taskSpecificEvidenceRef);

            if (validation.IsComplete)
            {
                return new MigrationCompatibilityCiHardGateResult(
                    IsSuccess: true,
                    AdvanceAllowed: true,
                    ExitCode: 0,
                    StageState: "ready",
                    Diagnostics: Array.Empty<MigrationCompatibilityDiagnostic>());
            }

            var diagnostics = new[]
            {
                new MigrationCompatibilityDiagnostic(
                    "COMPAT_VALIDATION_FAILED",
                    $"[compat-validator] {validation.FailureOutput}")
            };

            return new MigrationCompatibilityCiHardGateResult(
                IsSuccess: false,
                AdvanceAllowed: false,
                ExitCode: 1,
                StageState: "blocked",
                Diagnostics: diagnostics);
        }
    }

    private sealed record MigrationCompatibilityCiHardGateResult(
        bool IsSuccess,
        bool AdvanceAllowed,
        int ExitCode,
        string StageState,
        IReadOnlyList<MigrationCompatibilityDiagnostic> Diagnostics);

    private sealed record MigrationCompatibilityDiagnostic(string Code, string Message);

    private interface ICompatibilityValidator
    {
        MigrationCompatibilityCompletenessValidationResult Validate(
            MigrationCompatibilityReport report,
            IReadOnlyCollection<string> evidenceLinks,
            string taskSpecificEvidenceRef);
    }

    private sealed class DefaultCompatibilityValidator : ICompatibilityValidator
    {
        public MigrationCompatibilityCompletenessValidationResult Validate(
            MigrationCompatibilityReport report,
            IReadOnlyCollection<string> evidenceLinks,
            string taskSpecificEvidenceRef)
        {
            return MigrationCompatibilityCompletenessValidator.Validate(report, evidenceLinks, taskSpecificEvidenceRef);
        }
    }

    private sealed class AlwaysFailingCompatibilityValidator : ICompatibilityValidator
    {
        public MigrationCompatibilityCompletenessValidationResult Validate(
            MigrationCompatibilityReport report,
            IReadOnlyCollection<string> evidenceLinks,
            string taskSpecificEvidenceRef)
        {
            return new MigrationCompatibilityCompletenessValidationResult(
                IsComplete: false,
                FailureCodes: new[] { "forced_failure" },
                FailureOutput: "forced_failure");
        }
    }

    private sealed class CountingValidator(ICompatibilityValidator inner) : ICompatibilityValidator
    {
        public int CallCount { get; private set; }

        public MigrationCompatibilityCompletenessValidationResult Validate(
            MigrationCompatibilityReport report,
            IReadOnlyCollection<string> evidenceLinks,
            string taskSpecificEvidenceRef)
        {
            CallCount += 1;
            return inner.Validate(report, evidenceLinks, taskSpecificEvidenceRef);
        }
    }
}
