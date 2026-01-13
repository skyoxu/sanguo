using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task52EventTriggerOrderTests
{
    // ACC:T52.2
    [Fact]
    public void TurnScopeKey_ShouldBeCorrelationId()
    {
        SanguoEventOrderingRules.TurnScopeKey.Should().Be("CorrelationId");
    }
}

