using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task53MapConfigValidationTests
{
    // ACC:T53.2
    [Fact]
    public void MapValidator_ShouldAcceptEventTileType()
    {
        var map = new SanguoMapDefinition(
            "map001",
            1,
            new List<SanguoTileDefinition>
            {
                new(
                    0,
                    "event",
                    "e1",
                    "事件格",
                    "states00",
                    0m,
                    0m,
                    new[] { "random_event" }),
            }
        );

        SanguoMapDefinitionValidator.TryValidate(map, out var errors).Should().BeTrue();
        errors.Should().BeEmpty();
    }
}
