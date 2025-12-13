using System;
using Game.Core.Contracts;
using Game.Core.Services;
using Xunit;
using System.Threading.Tasks;

namespace Game.Core.Tests.Services;

public class EventBusTests
{
    [Fact]
    public async Task PublishInvokesSubscribersAndUnsubscribeWorks()
    {
        var bus = new InMemoryEventBus();
        int called = 0;
        var sub = bus.Subscribe(async e => { called++; await Task.CompletedTask; });

        await bus.PublishAsync(new DomainEvent(
            Type: "test.evt",
            Source: nameof(EventBusTests),
            Data: new { ok = true },
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString()
        ));

        Assert.Equal(1, called);
        sub.Dispose();

        await bus.PublishAsync(new DomainEvent(
            Type: "test.evt2",
            Source: nameof(EventBusTests),
            Data: null,
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString()
        ));
        Assert.Equal(1, called);
    }

    [Fact]
    public async Task SubscriberExceptionIsSwallowedAndOthersStillCalled()
    {
        var bus = new InMemoryEventBus();
        int ok = 0;
        bus.Subscribe(_ => throw new InvalidOperationException("boom"));
        bus.Subscribe(_ => { ok++; return Task.CompletedTask; });

        await bus.PublishAsync(new DomainEvent(
            Type: "evt",
            Source: nameof(EventBusTests),
            Data: null,
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString()
        ));
        Assert.Equal(1, ok);
    }
}
