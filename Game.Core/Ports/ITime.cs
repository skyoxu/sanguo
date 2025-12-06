namespace Game.Core.Ports;

public interface ITime
{
    /// Returns time elapsed since last update in seconds.
    double DeltaSeconds { get; }
}

