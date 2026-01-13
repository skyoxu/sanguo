using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task55StartingMoneyComputationTests
{
    // ACC:T55.2
    [Theory]
    [InlineData(5000)]
    [InlineData(10000)]
    [InlineData(20000)]
    public void GameStartConfig_StartingMoneyPreset_ShouldAllowExpectedPresets(int preset)
    {
        var cfg = new GameStartConfig(
            "map001",
            4,
            preset,
            10,
            1,
            new System.Collections.Generic.Dictionary<string, string>());

        cfg.StartingMoneyPreset.Should().Be(preset);
    }
}
