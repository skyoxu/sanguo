using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task57ActionCardPolicyTests
{
    // ACC:T57.1
    [Fact]
    public void ActionCardDefinition_ShouldOnlyUseMultiplierStepDelta()
    {
        var card = new SanguoActionCardDefinition(
            "ac001",
            "减税",
            "desc",
            -1);

        card.MultiplierStepDelta.Should().Be(-1);
    }
}
