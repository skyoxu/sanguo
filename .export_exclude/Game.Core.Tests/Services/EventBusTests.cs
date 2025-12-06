using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public class EventBusTests
{
    [Fact]
    public async Task Publish_ShouldInvokeSubscribers()
    {
        var bus = new InMemoryEventBus();
        var received = new List<DomainEvent>();
        using var sub = bus.Subscribe(evt => { received.Add(evt); return Task.CompletedTask; });
        await bus.PublishAsync(new DomainEvent("test.event", "unit", new { a = 1 }, DateTime.UtcNow, "id-1"));
        received.Should().HaveCount(1);
        received[0].Type.Should().Be("test.event");
    }

    [Fact]
    public async Task Unsubscribe_ShouldStopReceiving()
    {
        var bus = new InMemoryEventBus();
        var count = 0;
        var disp = bus.Subscribe(evt => { count++; return Task.CompletedTask; });
        await bus.PublishAsync(new DomainEvent("a", "", null, DateTime.UtcNow, "1"));
        disp.Dispose();
        await bus.PublishAsync(new DomainEvent("b", "", null, DateTime.UtcNow, "2"));
        count.Should().Be(1);
    }
}

