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
    private sealed class CapturingLogger : ILogger
    {
        public List<(string Level, string Message, Exception? Ex)> Entries { get; } = new();
        public void Info(string message) => Entries.Add(("info", message, null));
        public void Warn(string message) => Entries.Add(("warn", message, null));
        public void Error(string message) => Entries.Add(("error", message, null));
        public void Error(string message, Exception ex) => Entries.Add(("error", message, ex));
    }
    private sealed class ThrowingLogger : ILogger
    {
        public void Info(string message) { }
        public void Warn(string message) { }
        public void Error(string message) => throw new InvalidOperationException("logger failed");
        public void Error(string message, Exception ex) => throw new InvalidOperationException("logger failed", ex);
    }
    private sealed class CapturingErrorReporter : IErrorReporter
    {
        public List<(string Message, Exception Ex, IReadOnlyDictionary<string, string>? Context)> Exceptions { get; } = new();
        public List<(string Level, string Message, IReadOnlyDictionary<string, string>? Context)> Messages { get; } = new();
        public void CaptureMessage(string level, string message, IReadOnlyDictionary<string, string>? context = null)
            => Messages.Add((level, message, context));
        public void CaptureException(string message, Exception ex, IReadOnlyDictionary<string, string>? context = null)
            => Exceptions.Add((message, ex, context));
    }
    private sealed class ThrowingErrorReporter : IErrorReporter
    {
        public void CaptureMessage(string level, string message, IReadOnlyDictionary<string, string>? context = null)
            => throw new InvalidOperationException("reporter failed");
        public void CaptureException(string message, Exception ex, IReadOnlyDictionary<string, string>? context = null)
            => throw new InvalidOperationException("reporter failed", ex);
    }
    // ACC:T8.1
    [Fact]
    public async Task ShouldInvokeSubscribersAndUnsubscribe_WhenPublishing()
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
    // ACC:T8.2
    [Fact]
    public async Task ShouldSwallowSubscriberExceptionAndContinue_WhenSubscriberThrows()
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
    // ACC:T8.3
    [Fact]
    public async Task ShouldLogAndReport_WhenSubscriberThrowsAndLoggerAndReporterProvided()
    {
        var logger = new CapturingLogger();
        var reporter = new CapturingErrorReporter();
        var bus = new InMemoryEventBus(logger: logger, reporter: reporter);
        bus.Subscribe(_ => throw new InvalidOperationException("boom"));
        await bus.PublishAsync(new DomainEvent(
            Type: "evt",
            Source: nameof(EventBusTests),
            Data: null,
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString()
        ));
        logger.Entries.Should().Contain(e => e.Level == "error" && e.Message.Contains("Event handler failed"));
        reporter.Exceptions.Should().ContainSingle();
        reporter.Exceptions[0].Context.Should().NotBeNull();
        reporter.Exceptions[0].Context!.Should().ContainKey("event_type");
        reporter.Exceptions[0].Context!.Should().ContainKey("event_source");
        reporter.Exceptions[0].Context!.Should().ContainKey("event_id");
    }
    // ACC:T8.4
    [Fact]
    public async Task ShouldSwallowSubscriberException_WhenLoggerAndReporterThrow()
    {
        var bus = new InMemoryEventBus(logger: new ThrowingLogger(), reporter: new ThrowingErrorReporter());
        bus.Subscribe(_ => throw new InvalidOperationException("boom"));
        Func<Task> act = () => bus.PublishAsync(new DomainEvent(
            Type: "evt",
            Source: nameof(EventBusTests),
            Data: null,
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString()
        ));
        await act.Should().NotThrowAsync();
    }
    [Fact]
    public async Task ShouldLog_WhenOnlyLoggerProvided()
    {
        var logger = new CapturingLogger();
        var bus = new InMemoryEventBus(logger: logger, reporter: null);
        bus.Subscribe(_ => throw new InvalidOperationException("boom"));
        await bus.PublishAsync(new DomainEvent(
            Type: "evt",
            Source: nameof(EventBusTests),
            Data: null,
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString()
        ));
        logger.Entries.Should().Contain(e => e.Level == "error" && e.Message.Contains("Event handler failed"));
    }
}
