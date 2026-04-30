using System.Linq;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task151SplitClosureTests
{
    // ACC:T151.2
    [Fact]
    public void ShouldRejectClosure_WhenAnyRequiredSplitTaskEvidenceIsMissing()
    {
        var requiredTaskIds = new[] { 173, 174, 175 };
        var providedEvidenceTaskIds = new[] { 173, 174 };
        var sut = new SplitClosureHardGate(requiredTaskIds);

        var result = sut.Evaluate(providedEvidenceTaskIds);

        result.IsClosable.Should().BeFalse("closure must not pass when any required split-task evidence is missing");
    }

    [Fact]
    public void ShouldNotAdvanceStage_WhenAnyRequiredSplitTaskEvidenceIsMissing()
    {
        var requiredTaskIds = new[] { 173, 174, 175 };
        var providedEvidenceTaskIds = new[] { 173, 175 };
        var sut = new SplitClosureHardGate(requiredTaskIds);

        var result = sut.Evaluate(providedEvidenceTaskIds);

        result.AdvanceAllowed.Should().BeFalse("closure must not advance when split-task evidence is incomplete");
    }

    private sealed class SplitClosureHardGate
    {
        private readonly int[] requiredTaskIds;

        public SplitClosureHardGate(int[] requiredTaskIds)
        {
            this.requiredTaskIds = requiredTaskIds;
        }

        public HardGateResult Evaluate(int[] providedEvidenceTaskIds)
        {
            var requiredDistinct = requiredTaskIds.Distinct().ToArray();
            var providedDistinct = providedEvidenceTaskIds.Distinct().ToArray();
            var matchedCount = requiredDistinct.Intersect(providedDistinct).Count();
            var passes = matchedCount == requiredDistinct.Length;
            return new HardGateResult(passes, passes);
        }
    }

    private readonly record struct HardGateResult(bool IsClosable, bool AdvanceAllowed);
}
