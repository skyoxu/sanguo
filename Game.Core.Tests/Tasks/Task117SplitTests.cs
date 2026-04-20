using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public class Task117SplitTests
{
    // ACC:T117.1
    [Fact]
    public void ShouldMatchDeterministicObjectiveSnapshot_WhenSeedAndModeAreFixed()
    {
        var firstRun = SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot(
            seed: 117001,
            modeName: "Campaign",
            roundIndex: 1);
        var secondRun = SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot(
            seed: 117001,
            modeName: "Campaign",
            roundIndex: 1);

        firstRun.Should().Be(secondRun,
            "same seed and mode constraints should produce identical per-round objective output");
    }

    [Fact]
    public void ShouldProduceDifferentSnapshot_WhenRoundChangesUnderSameSeedAndMode()
    {
        var roundOne = SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot(
            seed: 117001,
            modeName: "Campaign",
            roundIndex: 1);
        var roundTwo = SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot(
            seed: 117001,
            modeName: "Campaign",
            roundIndex: 2);

        roundOne.Should().NotBe(roundTwo,
            "per-round objective generation must vary deterministically by round under the same seed and mode");
    }

    [Fact]
    public void ShouldProduceDifferentSnapshot_WhenModeChangesUnderSameSeedAndRound()
    {
        var campaignSnapshot = SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot(
            seed: 117001,
            modeName: "Campaign",
            roundIndex: 1);
        var skirmishSnapshot = SanguoObjectiveGenerationDeterminismEngine.GenerateObjectiveSnapshot(
            seed: 117001,
            modeName: "Skirmish",
            roundIndex: 1);

        campaignSnapshot.Should().NotBe(skirmishSnapshot,
            "objective generation must remain deterministic under mode constraints, not hard-coded for one mode only");
    }
}
