using Godot;
using System;

namespace Game.Godot.Scripts.UI;

public partial class EventLogPanel : PanelContainer
{
    [Export(PropertyHint.Range, "1,200,1")]
    public int MaxEntries { get; set; } = 50;

    private ItemList _list = default!;

    public override void _Ready()
    {
        _list = GetNode<ItemList>("Margin/VBox/EventList");
    }

    public void Append(string message)
    {
        if (string.IsNullOrWhiteSpace(message))
        {
            return;
        }

        _list.AddItem(message);
        while (_list.ItemCount > MaxEntries)
        {
            _list.RemoveItem(0);
        }

        _list.EnsureCurrentIsVisible();
    }
}

