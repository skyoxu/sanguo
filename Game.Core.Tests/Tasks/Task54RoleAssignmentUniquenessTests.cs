using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task54RoleAssignmentUniquenessTests
{
    // ACC:T54.1
    [Fact]
    public void GameStartConfig_CharacterAssignments_ShouldBeExpressibleAsDictionary()
    {
        var cfg = new GameStartConfig(
            "map001",
            4,
            10000,
            10,
            1,
            new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["p1"] = "c1",
                ["ai-1"] = "c2",
                ["ai-2"] = "c3",
                ["ai-3"] = "c4",
            });

        cfg.CharacterAssignments.Keys.Should().OnlyHaveUniqueItems();
        cfg.CharacterAssignments.Values.Should().OnlyHaveUniqueItems();
    }
}
