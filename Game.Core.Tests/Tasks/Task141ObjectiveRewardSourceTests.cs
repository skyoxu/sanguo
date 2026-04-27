using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task141ObjectiveRewardSourceTests
{
    // ACC:T141.1
    [Fact]
    public void ShouldEmitDeterministicSourceTagsAndEvidence_WhenRewardsComeFromEventEliteAndBoss()
    {
        var emissions = new[]
        {
            new ObjectiveRewardSourceEmission("event", "reward_evt_1", 10),
            new ObjectiveRewardSourceEmission("elite", "reward_elite_1", 20),
            new ObjectiveRewardSourceEmission("boss", "reward_boss_1", 30),
        };

        var actual = ObjectiveRewardSourceIntegration.BuildDeterministicEvidence(emissions);

        actual.SourceTags.Should().Equal("event", "elite", "boss");
        actual.EvidenceSignature.Should().Be("R8:event|elite|boss");
    }

    [Fact]
    public void ShouldProduceStableEvidence_WhenInputOrderAndPayloadAreIdentical()
    {
        var emissions = new[]
        {
            new ObjectiveRewardSourceEmission("event", "reward_evt_1", 10),
            new ObjectiveRewardSourceEmission("elite", "reward_elite_1", 20),
            new ObjectiveRewardSourceEmission("boss", "reward_boss_1", 30),
        };

        var first = ObjectiveRewardSourceIntegration.BuildDeterministicEvidence(emissions);
        var second = ObjectiveRewardSourceIntegration.BuildDeterministicEvidence(emissions);

        first.Should().BeEquivalentTo(second);
    }

    [Fact]
    public void ShouldIgnoreUnsupportedSources_WhenBuildingDeterministicEvidence()
    {
        var emissions = new[]
        {
            new ObjectiveRewardSourceEmission("event", "reward_evt_1", 10),
            new ObjectiveRewardSourceEmission("unknown", "reward_unknown_1", 99),
        };

        var actual = ObjectiveRewardSourceIntegration.BuildDeterministicEvidence(emissions);

        actual.SourceTags.Should().Equal("event");
        actual.EvidenceSignature.Should().Be("R8:event");
    }

}
