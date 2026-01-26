using FluentAssertions;
using Game.Core.Services;
using System;
using Xunit;

namespace Game.Core.Tests.Services;

public class SanguoGlobalEventSelectorTests
{
    [Fact]
    public void Select_ShouldThrow_WhenRngContextIdEmpty()
    {
        var selector = new SanguoGlobalEventSelector();
        Action act = () => selector.Select(rngContextId: "", roundNumber: 1, candidates: new[] { "e1" });
        act.Should().Throw<ArgumentException>().WithParameterName("rngContextId");
    }

    [Fact]
    public void Select_ShouldThrow_WhenRoundNumberInvalid()
    {
        var selector = new SanguoGlobalEventSelector();
        Action act = () => selector.Select(rngContextId: "s:1:1:x", roundNumber: 0, candidates: new[] { "e1" });
        act.Should().Throw<ArgumentOutOfRangeException>().WithParameterName("roundNumber");
    }

    [Fact]
    public void Select_ShouldThrow_WhenCandidatesEmptyAfterTrim()
    {
        var selector = new SanguoGlobalEventSelector();
        Action act = () => selector.Select(rngContextId: "s:1:1:x", roundNumber: 1, candidates: new[] { "", " " });
        act.Should().Throw<ArgumentException>().WithParameterName("candidates");
    }

    [Fact]
    public void Select_ShouldBeDeterministic_AndSortCandidates()
    {
        var selector = new SanguoGlobalEventSelector();
        var candidates = new[] { "b", "a", "c" };

        var r1 = selector.Select(rngContextId: "global:1:1:test", roundNumber: 3, candidates: candidates);
        var r2 = selector.Select(rngContextId: "global:1:1:test", roundNumber: 3, candidates: candidates);

        r1.PickedId.Should().Be(r2.PickedId);
        r1.PickedIndex.Should().Be(r2.PickedIndex);

        var expectedHash = SanguoDeterminism.ComputeCandidatesSortedIdsHash(candidates);
        r1.CandidatesSortedIdsHash.Should().Be(expectedHash);
        new[] { "a", "b", "c" }.Should().Contain(r1.PickedId);
    }
}

