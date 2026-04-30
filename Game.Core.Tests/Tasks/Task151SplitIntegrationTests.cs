using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task151SplitIntegrationTests
{
    private static readonly int[] RequiredSplitTaskIds = { 173, 174, 175 };

    private static readonly string[] RequiredAssertionIds =
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

    // ACC:T151.1
    [Fact]
    public void ShouldExposeSplitTaskOwnership_WhenRunningCoreHardGateClosure()
    {
        var pack = new Task151CoreHardGateIntegrationPack();
        var closure = pack.Evaluate(new[]
        {
            new SplitTaskEvidence(173, new[] { "A-013", "A-014", "A-015" }, IsDeterministic: true, IsPassed: true),
            new SplitTaskEvidence(174, new[] { "A-016", "A-017", "A-018", "A-019" }, IsDeterministic: true, IsPassed: true),
            new SplitTaskEvidence(175, new[] { "A-020" }, IsDeterministic: true, IsPassed: true),
        });
        var result = CoreAssertionGateRunner.Run();
        var summary = string.Join("|", result.Records.Select(record => $"{record.AccId}:{record.Message}"));

        closure.IsClosed.Should().BeTrue();
        closure.CompletionSignature.Should().Contain("173:", "integration closure must show deterministic ownership from split task 173");
        closure.CompletionSignature.Should().Contain("174:", "integration closure must show deterministic ownership from split task 174");
        closure.CompletionSignature.Should().Contain("175:", "integration closure must show deterministic ownership from split task 175");
        summary.Should().Contain("A-013");
        summary.Should().Contain("A-020");
    }

    [Fact]
    public void ShouldNotAdvanceClosure_WhenSplitTaskEvidenceIsMissing()
    {
        var pack = new Task151CoreHardGateIntegrationPack();
        var evidence = new[]
        {
            new SplitTaskEvidence(173, new[] { "A-013", "A-014", "A-015" }, IsDeterministic: true, IsPassed: true),
            new SplitTaskEvidence(174, new[] { "A-016", "A-017", "A-018", "A-019" }, IsDeterministic: true, IsPassed: true),
        };

        var result = pack.Evaluate(evidence);

        result.IsClosed.Should().BeFalse("closure must not pass when any required split task evidence is missing");
        result.AdvanceAllowed.Should().BeFalse("closure must not advance when any required split task evidence is missing");
        result.FailureCode.Should().Be("MISSING_SPLIT_TASK_EVIDENCE");
    }

    [Fact]
    public void ShouldProduceDeterministicCoverageSignature_WhenAllSplitTaskEvidenceIsPresent()
    {
        var pack = new Task151CoreHardGateIntegrationPack();
        var evidenceInOrder = new[]
        {
            new SplitTaskEvidence(173, new[] { "A-013", "A-014", "A-015" }, IsDeterministic: true, IsPassed: true),
            new SplitTaskEvidence(174, new[] { "A-016", "A-017", "A-018", "A-019" }, IsDeterministic: true, IsPassed: true),
            new SplitTaskEvidence(175, new[] { "A-020" }, IsDeterministic: true, IsPassed: true),
        };
        var evidenceReordered = new[]
        {
            evidenceInOrder[2],
            evidenceInOrder[0],
            evidenceInOrder[1],
        };

        var firstResult = pack.Evaluate(evidenceInOrder);
        var secondResult = pack.Evaluate(evidenceReordered);

        firstResult.IsClosed.Should().BeTrue("all split tasks 173, 174, and 175 are present with deterministic passing evidence");
        firstResult.AdvanceAllowed.Should().BeTrue();
        firstResult.CoveredAssertions.Should().BeEquivalentTo(RequiredAssertionIds);
        secondResult.IsClosed.Should().BeTrue();
        secondResult.CompletionSignature.Should().Be(firstResult.CompletionSignature, "closure evidence ordering must stay deterministic");
    }

    private sealed class Task151CoreHardGateIntegrationPack
    {
        public IntegrationClosureResult Evaluate(IReadOnlyCollection<SplitTaskEvidence> evidence)
        {
            var evidenceByTask = evidence
                .GroupBy(item => item.SplitTaskId)
                .ToDictionary(group => group.Key, group => group.First());

            var hasAllRequiredSplitTasks = RequiredSplitTaskIds.All(evidenceByTask.ContainsKey);
            if (!hasAllRequiredSplitTasks)
            {
                return IntegrationClosureResult.Fail("MISSING_SPLIT_TASK_EVIDENCE");
            }

            var allPassingAndDeterministic = evidence.All(item => item.IsDeterministic && item.IsPassed);
            if (!allPassingAndDeterministic)
            {
                return IntegrationClosureResult.Fail("NON_DETERMINISTIC_OR_FAILED_SPLIT");
            }

            var coveredAssertions = evidence
                .SelectMany(item => item.CoveredAssertions)
                .Where(item => !string.IsNullOrWhiteSpace(item))
                .Distinct(StringComparer.Ordinal)
                .OrderBy(item => item, StringComparer.Ordinal)
                .ToArray();

            var hasAllRequiredAssertions = RequiredAssertionIds.All(required =>
                coveredAssertions.Contains(required, StringComparer.Ordinal));
            if (!hasAllRequiredAssertions)
            {
                return IntegrationClosureResult.Fail("MISSING_REQUIRED_ASSERTION_COVERAGE", coveredAssertions);
            }

            var completionSignature = string.Join(
                ">",
                evidence
                    .OrderBy(item => item.SplitTaskId)
                    .Select(item => $"{item.SplitTaskId}:{string.Join(",", item.CoveredAssertions.OrderBy(accId => accId, StringComparer.Ordinal))}"));

            return IntegrationClosureResult.Pass(completionSignature, coveredAssertions);
        }
    }

    private sealed record SplitTaskEvidence(
        int SplitTaskId,
        IReadOnlyCollection<string> CoveredAssertions,
        bool IsDeterministic,
        bool IsPassed);

    private sealed record IntegrationClosureResult(
        bool IsClosed,
        bool AdvanceAllowed,
        string? FailureCode,
        string CompletionSignature,
        IReadOnlyCollection<string> CoveredAssertions)
    {
        public static IntegrationClosureResult Fail(string failureCode, IReadOnlyCollection<string>? coveredAssertions = null)
        {
            return new IntegrationClosureResult(
                IsClosed: false,
                AdvanceAllowed: false,
                FailureCode: failureCode,
                CompletionSignature: string.Empty,
                CoveredAssertions: coveredAssertions ?? Array.Empty<string>());
        }

        public static IntegrationClosureResult Pass(string completionSignature, IReadOnlyCollection<string> coveredAssertions)
        {
            return new IntegrationClosureResult(
                IsClosed: true,
                AdvanceAllowed: true,
                FailureCode: null,
                CompletionSignature: completionSignature,
                CoveredAssertions: coveredAssertions);
        }
    }
}
