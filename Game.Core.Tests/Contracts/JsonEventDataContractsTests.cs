using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts;
using Xunit;

namespace Game.Core.Tests.Contracts;

public sealed class JsonEventDataContractsTests
{
    [Fact]
    public void ShouldCarryJsonString_WhenUsingRawJsonEventData()
    {
        var payload = new RawJsonEventData("{\"a\":1}");
        payload.Json.Should().Be("{\"a\":1}");
        payload.Should().BeAssignableTo<IEventData>();
    }

    [Fact]
    public void ShouldProduceJsonElement_WhenJsonElementEventDataIsCreatedFromObject()
    {
        var payload = JsonElementEventData.FromObject(new { a = 1 });
        payload.Should().BeAssignableTo<IEventData>();

        payload.Value.ValueKind.Should().Be(JsonValueKind.Object);
        payload.Value.GetProperty("a").GetInt32().Should().Be(1);
    }
}
