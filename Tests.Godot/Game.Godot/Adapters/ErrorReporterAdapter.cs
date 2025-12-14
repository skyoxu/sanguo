using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Godot;
using Game.Core.Ports;
using Game.Godot.Scripts.Obs;

namespace Game.Godot.Adapters;

public partial class ErrorReporterAdapter : Node, IErrorReporter
{
    public SentryClient? Sentry { get; set; }

    public void CaptureMessage(string level, string message, IReadOnlyDictionary<string, string>? context = null)
    {
        try
        {
            var ctx = ToObjectDictionary(context);
            if (Sentry is not null)
            {
                Sentry.CaptureMessage(level, message, ctx);
                return;
            }

            WriteLocal(new
            {
                ts = DateTime.UtcNow.ToString("O"),
                type = "message",
                level,
                message,
                context = ctx,
            });
        }
        catch (Exception ex)
        {
            GD.PushWarning($"[ErrorReporter] CaptureMessage failed: {ex.Message}");
        }
    }

    public void CaptureException(string message, Exception ex, IReadOnlyDictionary<string, string>? context = null)
    {
        try
        {
            var ctx = ToObjectDictionary(context);
            ctx["exception_type"] = ex.GetType().FullName ?? ex.GetType().Name;
            ctx["exception_message"] = ex.Message;
            ctx["stacktrace"] = ex.ToString();

            if (Sentry is not null)
            {
                Sentry.CaptureException(message, ctx);
                return;
            }

            WriteLocal(new
            {
                ts = DateTime.UtcNow.ToString("O"),
                type = "exception",
                level = "error",
                message,
                context = ctx,
            });
        }
        catch (Exception localEx)
        {
            GD.PushWarning($"[ErrorReporter] CaptureException failed: {localEx.Message}");
        }
    }

    private static Dictionary<string, object> ToObjectDictionary(IReadOnlyDictionary<string, string>? context)
    {
        var d = new Dictionary<string, object>();
        if (context is null) return d;
        foreach (var kv in context)
            d[kv.Key] = kv.Value;
        return d;
    }

    private static void WriteLocal(object evt)
    {
        var dir = ProjectSettings.GlobalizePath("user://logs/obs");
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, $"errors-{DateTime.UtcNow:yyyyMMdd}.jsonl");
        var json = JsonSerializer.Serialize(evt);
        File.AppendAllText(path, json + System.Environment.NewLine);
    }
}
