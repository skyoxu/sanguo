using Godot;
using System;
using System.IO;
using System.Text.Json;

namespace Game.Godot.Scripts.Obs;

public partial class SentryClient : Node
{
    [Export] public bool Enabled { get; set; } = false;
    [Export] public string Dsn { get; set; } = string.Empty;

    public override void _Ready()
    {
        if (string.IsNullOrWhiteSpace(Dsn))
        {
            var env = System.Environment.GetEnvironmentVariable("SENTRY_DSN");
            if (!string.IsNullOrWhiteSpace(env))
            {
                Dsn = env;
                // 注意：模板默认不进行网络发送，仅作为启用占位标记
                if (!Enabled) Enabled = false;
            }
        }
    }

    public bool CaptureMessage(string level, string message, System.Collections.Generic.Dictionary<string, object>? context = null)
    {
        try
        {
            var evt = new
            {
                ts = DateTime.UtcNow.ToString("O"),
                type = "message",
                level = level,
                message = message,
                context = context ?? new System.Collections.Generic.Dictionary<string, object>(),
                dsn_present = !string.IsNullOrWhiteSpace(Dsn),
                enabled = Enabled
            };
            WriteLocal(evt);
            return true;
        }
        catch (Exception ex)
        {
            GD.PushWarning($"[SentryClient] CaptureMessage failed: {ex.Message}");
            return false;
        }
    }

    public bool CaptureException(string exceptionMessage, System.Collections.Generic.Dictionary<string, object>? context = null)
    {
        try
        {
            var evt = new
            {
                ts = DateTime.UtcNow.ToString("O"),
                type = "exception",
                message = exceptionMessage,
                context = context ?? new System.Collections.Generic.Dictionary<string, object>(),
                dsn_present = !string.IsNullOrWhiteSpace(Dsn),
                enabled = Enabled
            };
            WriteLocal(evt);
            return true;
        }
        catch (Exception ex)
        {
            GD.PushWarning($"[SentryClient] CaptureException failed: {ex.Message}");
            return false;
        }
    }

    private void WriteLocal(object evt)
    {
        var dir = ProjectSettings.GlobalizePath("user://logs/sentry");
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, $"events-{DateTime.UtcNow:yyyyMMdd}.jsonl");
        var json = JsonSerializer.Serialize(evt);
        File.AppendAllText(path, json + System.Environment.NewLine);
    }
}
