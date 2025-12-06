using Godot;
using Game.Godot.Adapters;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public partial class ScorePanel : Control
{
    private Label _score = default!;
    private Button _add10 = default!;
    private Button _add50 = default!;

    public override void _Ready()
    {
        _score = GetNode<Label>("VBox/ScoreValue");
        _add10 = GetNode<Button>("VBox/Buttons/Add10");
        _add50 = GetNode<Button>("VBox/Buttons/Add50");

        _add10.Pressed += () => OnAdd(10);
        _add50.Pressed += () => OnAdd(50);

        var bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (bus != null)
        {
            bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, new Callable(this, nameof(OnDomainEventEmitted)));
        }
    }

    private void OnAdd(int amount)
    {
        var engine = GetNodeOrNull<Node>("/root/Main/EngineDemo");
        if (engine != null && engine.HasMethod("AddScore"))
        {
            engine.Call("AddScore", amount);
            return;
        }
        // Fallback: publish UI event
        var bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        bus?.PublishSimple("core.score.updated", "ui", "{\"value\":%d}".Replace("%d", amount.ToString()));
    }

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        if (type == "core.score.updated" || type == "score.changed")
        {
            try
            {
                var doc = JsonDocument.Parse(dataJson);
                int v = 0;
                if (doc.RootElement.TryGetProperty("value", out var val)) v = val.GetInt32();
                else if (doc.RootElement.TryGetProperty("score", out var sc)) v = sc.GetInt32();
                _score.Text = v.ToString();
            }
            catch { }
        }
    }
}

