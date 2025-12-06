using Godot;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace Game.Godot.Scripts.Perf;

public partial class PerformanceTracker : Node
{
    [Export] public bool Enabled { get; set; } = true;
    [Export] public int WindowFrames { get; set; } = 300;
    [Export] public float FlushIntervalSec { get; set; } = 1.0f;

    private readonly List<double> _frameMs = new();
    private Timer _timer = default!;

    public override void _Ready()
    {
        if (!Enabled) return;
        SetProcess(true);
        _timer = new Timer { WaitTime = FlushIntervalSec, OneShot = false, Autostart = true };
        AddChild(_timer);
        _timer.Timeout += OnFlush;
    }

    public override void _Process(double delta)
    {
        if (!Enabled) return;
        var ms = Math.Max(0, delta * 1000.0);
        _frameMs.Add(ms);
        if (_frameMs.Count > WindowFrames)
            _frameMs.RemoveRange(0, _frameMs.Count - WindowFrames);
    }

    private void OnFlush()
    {
        if (!Enabled || _frameMs.Count < 5) return;
        var metrics = Compute();
        // Console marker for smoke parser
        GD.Print($"[PERF] frames={metrics.frames} avg_ms={metrics.avg_ms:F2} p50_ms={metrics.p50_ms:F2} p95_ms={metrics.p95_ms:F2} p99_ms={metrics.p99_ms:F2}");
        // Write JSON file
        try
        {
            var dir = ProjectSettings.GlobalizePath("user://logs/perf");
            Directory.CreateDirectory(dir);
            var json = JsonSerializer.Serialize(metrics);
            File.WriteAllText(Path.Combine(dir, "perf.json"), json);
        }
        catch { }
    }

    private (int frames, double avg_ms, double p50_ms, double p95_ms, double p99_ms) Compute()
    {
        var frames = _frameMs.Count;
        var avg = _frameMs.Average();
        var sorted = _frameMs.OrderBy(v => v).ToArray();
        double P(double q)
        {
            if (sorted.Length == 0) return 0;
            var pos = q * (sorted.Length - 1);
            var lo = (int)Math.Floor(pos);
            var hi = (int)Math.Ceiling(pos);
            if (lo == hi) return sorted[lo];
            var w = pos - lo;
            return sorted[lo] * (1 - w) + sorted[hi] * w;
        }
        return (frames, avg, P(0.5), P(0.95), P(0.99));
    }
}

