using System;
using System.Threading.Tasks;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Services;
using Xunit;

namespace Game.Core.Tests.Services;

public sealed class NullEventBusTests
{
    [Fact]
    public async Task PublishAsync_ShouldCompleteSuccessfully()
    {
        var evt = new DomainEvent(
            Type: "core.test.event",
            Source: "core.tests",
            Data: null,
            Timestamp: DateTime.UtcNow,
            Id: "evt-1");

        var task = NullEventBus.Instance.PublishAsync(evt);
        await task;
        task.IsCompletedSuccessfully.Should().BeTrue();
    }

    [Fact]
    public void Subscribe_ShouldReturnDisposable()
    {
        var sub = NullEventBus.Instance.Subscribe(_ => Task.CompletedTask);
        sub.Should().NotBeNull();
        sub.Invoking(x => x.Dispose()).Should().NotThrow();
    }
}

