using Godot;
using Game.Godot.Adapters;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public partial class CombatPanel : Control
{
    private Label _hp = default!;
    private Button _dmg5 = default!;
    private Button _dmg20 = default!;

    public override void _Ready()
    {
        _hp = GetNode<Label>("VBox/HpValue");
        _dmg5 = GetNode<Button>("VBox/Buttons/Dmg5");
        _dmg20 = GetNode<Button>("VBox/Buttons/Dmg20");

        _dmg5.Pressed += () => OnDamage(5);
        _dmg20.Pressed += () => OnDamage(20);

        var bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (bus != null)
        {
            bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, new Callable(this, nameof(OnDomainEventEmitted)));
        }
    }

    private void OnDamage(int amount)
    {
        var engine = GetNodeOrNull<Node>("/root/Main/EngineDemo");
        if (engine != null && engine.HasMethod("ApplyDamage"))
        {
            engine.Call("ApplyDamage", amount);
            return;
        }
        // Fallback: publish a simple damage event (HUD may not react)
        var bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        bus?.PublishSimple("player.damaged", "ui", "{\"amount\":%d}".Replace("%d", amount.ToString()));
    }

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        if (type == "core.health.updated" || type == "player.health.changed")
        {
            try
            {
                var doc = JsonDocument.Parse(dataJson);
                int v = 0;
                if (doc.RootElement.TryGetProperty("value", out var val)) v = val.GetInt32();
                else if (doc.RootElement.TryGetProperty("health", out var hp)) v = hp.GetInt32();
                _hp.Text = v.ToString();
            }
            catch { }
        }
    }
}

