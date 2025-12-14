using System;
using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Contracts;
using Game.Core.Ports;
using Game.Core.Services;
using Xunit;
using System.Threading.Tasks;

namespace Game.Core.Tests.Services;

public class EventBusTests
{
    private sealed class CapturingErrorReporter : IErrorReporter
    {
        public List<(string Message, Exception Ex, IReadOnlyDictionary<string, string>? Context)> Exceptions { get; } = new();
        public List<(string Level, string Message, IReadOnlyDictionary<string, string>? Context)> Messages { get; } = new();

        public void CaptureMessage(string level, string message, IReadOnlyDictionary<string, string>? context = null)
            => Messages.Add((level, message, context));

        public void CaptureException(string message, Exception ex, IReadOnlyDictionary<string, string>? context = null)
            => Exceptions.Add((message, ex, context));
    }

    [Fact]
    public async Task PublishInvokesSubscribersAndUnsubscribeWorks()
    {
        var bus = new InMemoryEventBus();
        int called = 0;
        var sub = bus.Subscribe(async e => { called++; await Task.CompletedTask; });

        await bus.PublishAsync(new DomainEvent(
            Type: "test.evt",
            Source: nameof(EventBusTests),
            Data: JsonElementEventData.FromObject(new { ok = true }),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString()
        ));

        called.Should().Be(1);
        sub.Dispose();

        await bus.PublishAsync(new DomainEvent(
            Type: "test.evt2",
            Source: nameof(EventBusTests),
            Data: null,
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString()
        ));
        called.Should().Be(1);
    }

    [Fact]
    public async Task SubscriberExceptionIsSwallowedAndOthersStillCalled()
    {
        var reporter = new CapturingErrorReporter();
        var bus = new InMemoryEventBus(reporter: reporter);
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
        ok.Should().Be(1);
        reporter.Exceptions.Should().ContainSingle();
        reporter.Exceptions[0].Message.Should().Be("eventbus.handler.exception");
        reporter.Exceptions[0].Context.Should().NotBeNull();
    }
}
