using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task78RewardDraftEngineTests
{
    // ACC:T78.1
    [Fact]
    [Trait("acceptance", "ACC:T78.1")]
    public void ShouldReturnDeterministicRewardDraftCandidates_WhenInputsRepeat()
    {
        var first = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: 78,
            source: "task78_reward_draft",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);
        var second = RewardDraftCandidateDeterminismEngine.GenerateDraftCandidates(
            seed: 78,
            source: "task78_reward_draft",
            choiceCount: 3,
            actionCardsCatalog: null,
            relicsCatalog: null);

        first.Should().HaveCount(3);
        second.Should().HaveCount(3);
        second.Should().Equal(first);
        first.Should().OnlyHaveUniqueItems();
    }
}

