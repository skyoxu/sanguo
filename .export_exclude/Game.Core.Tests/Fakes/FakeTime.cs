using Game.Core.Ports;

namespace Game.Core.Tests.Fakes;

public class FakeTime : ITime
{
    public double DeltaSeconds { get; set; }
}

