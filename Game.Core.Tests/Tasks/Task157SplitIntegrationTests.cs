using System;
using System.Collections.Generic;
using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task157SplitIntegrationTests
{
    // ACC:T157.1
    [Fact]
    public void ShouldReportDeterministicCompletionSemantics_WhenSplitTaskClosureEvidenceIsComplete()
    {
        var requiredSignals = new[] { "closure-evidence", "signal-compliance" };
        var requiredSplitTaskIds = new[] { 162, 163 };
        var evidence = new[]
        {
            new ClosureEvidence(163, "Game.Core.Tests/Tasks/Task157SplitIntegrationTests.cs", "signal-compliance"),
            new ClosureEvidence(162, "Game.Core.Tests/Tasks/Task157SplitIntegrationTests.cs", "closure-evidence")
        };
        var workflow = new CiSignalComplianceWorkflow(requiredSignals, requiredSplitTaskIds);

        var firstResult = workflow.Evaluate(evidence);
        var secondResult = workflow.Evaluate(evidence.Reverse().ToArray());

        firstResult.IsCompleted.Should().BeTrue("both split tasks 162 and 163 must contribute PH9-B4 closure evidence");
        secondResult.IsCompleted.Should().BeTrue();
        firstResult.CompletionSignature.Should().Be(
            secondResult.CompletionSignature,
            "completion semantics must be deterministic regardless of evidence ordering");
    }

    // ACC:T157.2
    [Fact]
    public void ShouldRejectGatePass_WhenClosureEvidenceUsesNonTestPaths()
    {
        var requiredSignals = new[] { "closure-evidence", "signal-compliance" };
        var requiredSplitTaskIds = new[] { 162, 163 };
        var evidence = new[]
        {
            new ClosureEvidence(162, "scripts/sc/run_review_pipeline.py", "closure-evidence"),
            new ClosureEvidence(163, "scripts/python/dev_cli.py", "signal-compliance")
        };
        var workflow = new CiSignalComplianceWorkflow(requiredSignals, requiredSplitTaskIds);

        var result = workflow.Evaluate(evidence);

        result.IsCompleted.Should().BeFalse("hard-gate evidence must come from task-scoped test files only");
        result.RejectionReason.Should().Be("NON_TEST_EVIDENCE_PATH");
    }

    // ACC:T157.3
    [Fact]
    public void ShouldRemainIncomplete_WhenEitherSplitTaskEvidenceIsMissing()
    {
        var requiredSignals = new[] { "closure-evidence", "signal-compliance" };
        var requiredSplitTaskIds = new[] { 162, 163 };
        var evidence = new[]
        {
            new ClosureEvidence(162, "Game.Core.Tests/Tasks/Task157SplitIntegrationTests.cs", "closure-evidence"),
            new ClosureEvidence(162, "Game.Core.Tests/Tasks/Task157SplitIntegrationTests.cs", "signal-compliance")
        };
        var workflow = new CiSignalComplianceWorkflow(requiredSignals, requiredSplitTaskIds);

        var result = workflow.Evaluate(evidence);

        result.IsCompleted.Should().BeFalse("Task 157 requires closure evidence from both split tasks 162 and 163");
        result.RejectionReason.Should().Be("MISSING_SPLIT_TASK_EVIDENCE");
    }

    private sealed class CiSignalComplianceWorkflow
    {
        private readonly HashSet<string> requiredSignals;
        private readonly HashSet<int> requiredSplitTaskIds;

        public CiSignalComplianceWorkflow(IEnumerable<string> requiredSignals, IEnumerable<int> requiredSplitTaskIds)
        {
            this.requiredSignals = new HashSet<string>(requiredSignals, StringComparer.OrdinalIgnoreCase);
            this.requiredSplitTaskIds = new HashSet<int>(requiredSplitTaskIds);
        }

        public EvaluationResult Evaluate(IReadOnlyCollection<ClosureEvidence> evidence)
        {
            var nonTestEvidence = evidence
                .FirstOrDefault(item => !IsTaskScopedTestPath(item.SourcePath));
            if (nonTestEvidence is not null)
            {
                return new EvaluationResult(false, string.Empty, "NON_TEST_EVIDENCE_PATH");
            }

            var providedSignals = evidence
                .Select(item => item.Signal)
                .ToHashSet(StringComparer.OrdinalIgnoreCase);

            var providedSplitTaskIds = evidence
                .Select(item => item.SplitTaskId)
                .ToHashSet();

            var hasAllSignals = requiredSignals.All(providedSignals.Contains);
            var hasAllSplitTaskEvidence = requiredSplitTaskIds.All(providedSplitTaskIds.Contains);

            if (!hasAllSplitTaskEvidence)
            {
                return new EvaluationResult(false, string.Empty, "MISSING_SPLIT_TASK_EVIDENCE");
            }

            var isCompleted = hasAllSignals;

            var completionSignature = string.Join(
                ">",
                evidence
                    .OrderBy(item => item.SplitTaskId)
                    .ThenBy(item => item.Signal, StringComparer.OrdinalIgnoreCase)
                    .Select(item => $"{item.SplitTaskId}:{item.Signal}"));

            return new EvaluationResult(isCompleted, completionSignature, null);
        }

        private static bool IsTaskScopedTestPath(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return false;
            }

            var normalized = path.Replace("\\", "/");
            return normalized.StartsWith("Game.Core.Tests/Tasks/Task", StringComparison.Ordinal);
        }
    }

    private sealed class ClosureEvidence
    {
        public ClosureEvidence(int splitTaskId, string sourcePath, string signal)
        {
            SplitTaskId = splitTaskId;
            SourcePath = sourcePath;
            Signal = signal;
        }

        public int SplitTaskId { get; }

        public string SourcePath { get; }

        public string Signal { get; }
    }

    private sealed class EvaluationResult
    {
        public EvaluationResult(bool isCompleted, string completionSignature, string? rejectionReason)
        {
            IsCompleted = isCompleted;
            CompletionSignature = completionSignature;
            RejectionReason = rejectionReason;
        }

        public bool IsCompleted { get; }

        public string CompletionSignature { get; }

        public string? RejectionReason { get; }
    }
}
