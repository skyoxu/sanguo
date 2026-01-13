using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task51AppliedMultipliersSerializationTests
{
    // ACC:T51.3
    [Fact]
    public void AppliedMultipliers_ShouldRoundTrip_WithSystemTextJson()
    {
        var m = new AppliedMultipliers(
            1.5m,
            1.0m,
            0.5m,
            1.0m,
            0.75m,
            AppliedMultiplierSources.Character | AppliedMultiplierSources.ActionCard);

        var json = JsonSerializer.Serialize(m);
        var restored = JsonSerializer.Deserialize<AppliedMultipliers>(json);

        restored.Should().NotBeNull();
        restored!.Character.Should().Be(1.5m);
        restored.Building.Should().Be(1.0m);
        restored.Event.Should().Be(0.5m);
        restored.ActionCard.Should().Be(1.0m);
        restored.Effective.Should().Be(0.75m);
        restored.Sources.Should().Be(AppliedMultiplierSources.Character | AppliedMultiplierSources.ActionCard);
    }
}
