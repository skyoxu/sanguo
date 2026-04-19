using System.Collections.Generic;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task129SplitTests
{
    // ACC:T129.1
    [Fact]
    public void ShouldResolveCampDurabilityFatalBeforeR3AndA001_WhenEventsCollide()
    {
        var events = new[]
        {
            GlobalEvent.ExampleNonFatalB,
            GlobalEvent.R3Resolution,
            GlobalEvent.ExampleNonFatalA,
            GlobalEvent.A001PostEffect,
            GlobalEvent.CampDurabilityFatal
        };

        var resolved = GlobalPriorityResolver.Resolve(events);

        resolved.Should().Equal(
            GlobalEvent.CampDurabilityFatal,
            GlobalEvent.ExampleNonFatalB,
            GlobalEvent.R3Resolution,
            GlobalEvent.ExampleNonFatalA,
            GlobalEvent.A001PostEffect);
    }

    // ACC:T129.2
    [Fact]
    public void ShouldKeepOriginalOrderForNonFatalEvents_WhenNoFatalDurabilityExists()
    {
        var events = new[]
        {
            GlobalEvent.A001PostEffect,
            GlobalEvent.R3Resolution
        };

        var resolved = GlobalPriorityResolver.Resolve(events);

        resolved.Should().Equal(
            GlobalEvent.A001PostEffect,
            GlobalEvent.R3Resolution);
    }

    private enum GlobalEvent
    {
        CampDurabilityFatal,
        ExampleNonFatalA,
        ExampleNonFatalB,
        R3Resolution,
        A001PostEffect
    }

    private static class GlobalPriorityResolver
    {
        public static IReadOnlyList<GlobalEvent> Resolve(IEnumerable<GlobalEvent> events)
        {
            return CampDurabilityFatalPreemption.Resolve(
                events,
                static evt => evt == GlobalEvent.CampDurabilityFatal);
        }
    }
}
