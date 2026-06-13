using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task214CompletionResultDeterministicResourceTests
{
    // ACC:T214.1 ACC:T214.2 ACC:T214.3 ACC:T214.5 ACC:T214.6 ACC:T214.9 ACC:T214.10
    [Fact]
    public void ShouldExposeStableUiStateReadModel_WhenPart2CompletionResultIsProduced()
    {
        var input = new Part2CompletionResultResourceReadInput(
            PlayerId: "p1",
            ResourceId: "grain",
            ResourceDelta: 120,
            ProgressionId: "market",
            ProgressionDelta: 2,
            CompletionSequence: 7);

        var first = Part2CompletionResultResourceReader.ReadDeterministicResource(input);
        var second = Part2CompletionResultResourceReader.ReadDeterministicResource(input);

        first.Accepted.Should().BeTrue();
        first.State.Should().NotBeNull();
        first.ResourceOutcome.Should().Be("resource:grain:+120");
        first.ProgressionOutcome.Should().Be("progression:market:+2");
        first.PlayerReadableSummary.Should().Be("resource:grain:+120;progression:market:+2;sequence:7");
        first.State.ResourceOutcome.Should().Be(first.ResourceOutcome);
        first.State.ProgressionOutcome.Should().Be(first.ProgressionOutcome);
        first.State.PlayerReadableSummary.Should().Be(first.PlayerReadableSummary);
        first.CompletionResultKey.Should().Be("p1|grain|120|market|2|7");
        second.Should().BeEquivalentTo(first);
    }

    // ACC:T214.4 ACC:T214.7 ACC:T214.8
    [Fact]
    public void ShouldKeepUiStateReadModelUnchanged_WhenInputIsInvalid()
    {
        var baseline = Part2CompletionResultResourceReader.EmptyState;
        var invalidInput = new Part2CompletionResultResourceReadInput(
            PlayerId: "p1",
            ResourceId: "",
            ResourceDelta: 10,
            ProgressionId: "market",
            ProgressionDelta: 1,
            CompletionSequence: 2);

        var result = Part2CompletionResultResourceReader.ReadDeterministicResource(invalidInput, baseline);

        result.Accepted.Should().BeFalse();
        result.ReasonCode.Should().Be(Part2CompletionResultResourceReader.InvalidInputReason);
        result.State.Should().Be(baseline);
        result.ResourceOutcome.Should().BeEmpty();
        result.ProgressionOutcome.Should().BeEmpty();
    }

    // ACC:T214.11 ACC:T214.12
    [Fact]
    public void ShouldExposeTraceableAuditFields_WhenImplementationRemainsPureCore()
    {
        var input = new Part2CompletionResultResourceReadInput(
            PlayerId: "p1",
            ResourceId: "coin",
            ResourceDelta: -25,
            ProgressionId: "settlement",
            ProgressionDelta: 1,
            CompletionSequence: 3);

        var result = Part2CompletionResultResourceReader.ReadDeterministicResource(input);

        typeof(Part2CompletionResultResourceReader).Assembly.GetReferencedAssemblies()
            .Should().NotContain(assembly => assembly.Name == "GodotSharp" || assembly.Name == "GodotSharpEditor");
        result.EvidenceRefs.Should().Contain("ACC:T214");
        result.PlayerReadableSummary.Should().Contain("resource");
        result.PlayerReadableSummary.Should().Contain("progression");
    }
}
