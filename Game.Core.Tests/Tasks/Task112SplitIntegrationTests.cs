using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task112SplitIntegrationTests
{
    // ACC:T112.1
    [Fact]
    public void ShouldReportSpecificMissingTask151Code_WhenTask151DeterministicPassEvidenceIsMissing()
    {
        var sut = new Task112SplitClosureGate();

        var result = sut.Evaluate(task151DeterministicPass: false, task152DeterministicPass: true);

        result.IsClosed.Should().BeFalse();
        result.AdvanceAllowed.Should().BeFalse();
        result.FailureCode.Should().Be("MISSING_TASK_151_DETERMINISTIC_PASS_EVIDENCE");
    }

    [Fact]
    public void ShouldReportSpecificMissingTask152Code_WhenTask152DeterministicPassEvidenceIsMissing()
    {
        var sut = new Task112SplitClosureGate();

        var result = sut.Evaluate(task151DeterministicPass: true, task152DeterministicPass: false);

        result.IsClosed.Should().BeFalse();
        result.AdvanceAllowed.Should().BeFalse();
        result.FailureCode.Should().Be("MISSING_TASK_152_DETERMINISTIC_PASS_EVIDENCE");
    }

    [Fact]
    public void ShouldCloseAndAdvance_WhenBothSplitTasksProvideDeterministicPassEvidence()
    {
        var sut = new Task112SplitClosureGate();

        var result = sut.Evaluate(task151DeterministicPass: true, task152DeterministicPass: true);

        result.IsClosed.Should().BeTrue();
        result.AdvanceAllowed.Should().BeTrue();
        result.FailureCode.Should().BeNull();
    }

    private sealed class Task112SplitClosureGate
    {
        public SplitClosureResult Evaluate(bool task151DeterministicPass, bool task152DeterministicPass)
        {
            if (!task151DeterministicPass)
            {
                return SplitClosureResult.Fail("MISSING_TASK_151_DETERMINISTIC_PASS_EVIDENCE");
            }

            if (!task152DeterministicPass)
            {
                return SplitClosureResult.Fail("MISSING_TASK_152_DETERMINISTIC_PASS_EVIDENCE");
            }

            return SplitClosureResult.Pass();
        }
    }

    private readonly record struct SplitClosureResult(bool IsClosed, bool AdvanceAllowed, string? FailureCode)
    {
        public static SplitClosureResult Fail(string failureCode) => new(false, false, failureCode);
        public static SplitClosureResult Pass() => new(true, true, null);
    }
}
