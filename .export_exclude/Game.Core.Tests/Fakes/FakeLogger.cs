using Game.Core.Ports;

namespace Game.Core.Tests.Fakes;

public class FakeLogger : ILogger
{
    public readonly List<string> Infos = new();
    public readonly List<string> Warns = new();
    public readonly List<string> Errors = new();

    public void Info(string message) => Infos.Add(message);
    public void Warn(string message) => Warns.Add(message);
    public void Error(string message) => Errors.Add(message);
    public void Error(string message, Exception ex) => Errors.Add(message + ": " + ex.GetType().Name);
}

