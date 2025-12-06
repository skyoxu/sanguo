using Godot;
using Game.Core.Ports;

namespace Game.Godot.Adapters;

public partial class LoggerAdapter : Node, ILogger
{
    public void Info(string message) => GD.Print("[INFO] "+message);
    public void Warn(string message) => GD.PushWarning("[WARN] "+message);
    public void Error(string message) => GD.PushError("[ERROR] "+message);
    public void Error(string message, System.Exception ex) => GD.PushError($"[ERROR] {message}: {ex}");
}

