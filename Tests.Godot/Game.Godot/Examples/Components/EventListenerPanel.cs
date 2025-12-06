using Godot;
using Game.Godot.Scripts.Utils;

namespace Game.Godot.Examples.Components;

public partial class EventListenerPanel : ControlWithSignals
{
    private Label _label = default!;
    private int _count;

    public override void _Ready()
    {
        _label = GetNode<Label>("VBox/Count");
        _label.Text = "0";
    }

    // Optional lifecycle: called by ScreenNavigator after instance added
    public void Enter()
    {
        var bus = GetNodeOrNull("/root/EventBus");
        if (bus != null)
        {
            Signals.Connect(bus, "DomainEventEmitted", new Callable(this, nameof(OnDomainEventEmitted)));
        }
    }

    private void OnDomainEventEmitted(string type, string source, string dataJson, string id, string specVersion, string dataContentType, string timestampIso)
    {
        if (type == "screen.demo.ping")
        {
            _count++;
            _label.Text = _count.ToString();
        }
    }
}
