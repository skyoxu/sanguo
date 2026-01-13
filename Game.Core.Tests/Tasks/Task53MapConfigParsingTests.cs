using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task53MapConfigParsingTests
{
    // ACC:T53.1
    [Fact]
    public void TileTypeConstants_ShouldIncludeEventAndEmpty()
    {
        SanguoTileDefinition.TileTypeEvent.Should().Be("event");
        SanguoTileDefinition.TileTypeEmpty.Should().Be("empty");
    }
}

