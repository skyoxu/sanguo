using Godot;
using System;
using System.Collections.Generic;

namespace Game.Godot.Scripts.UI;

public partial class EventLogPanel : PanelContainer
{
    [Export(PropertyHint.Range, "1,200,1")]
    public int MaxEntries { get; set; } = 50;

    private ItemList _list = default!;
    private Label? _details;
    private readonly List<EventExplanation> _entries = new();
    private string _latestDetailText = string.Empty;

    public override void _Ready()
    {
        _list = GetNode<ItemList>("Margin/VBox/EventList");
        _details = GetNodeOrNull<Label>("Margin/VBox/Details/Scroll/DetailsText");

        _list.ItemSelected += OnItemSelected;
    }

    public void Append(EventExplanation explanation)
    {
        if (explanation == null || string.IsNullOrWhiteSpace(explanation.SummaryText))
        {
            return;
        }

        if (_details == null)
        {
            _details = GetNodeOrNull<Label>("Margin/VBox/Details/Scroll/DetailsText");
        }

        _entries.Add(explanation);
        _list.AddItem(explanation.SummaryText);
        while (_list.ItemCount > MaxEntries)
        {
            _list.RemoveItem(0);
            if (_entries.Count != 0)
            {
                _entries.RemoveAt(0);
            }
        }

        var lastIndex = _list.ItemCount - 1;
        if (lastIndex >= 0)
        {
            _list.Select(lastIndex);
            _list.EnsureCurrentIsVisible();
            ShowDetailsForIndex(lastIndex);
        }

        _latestDetailText = explanation.DetailText ?? string.Empty;
        if (_details != null)
        {
            _details.Text = _latestDetailText;
        }
    }

    private void OnItemSelected(long index)
    {
        ShowDetailsForIndex((int)index);
    }

    private void ShowDetailsForIndex(int index)
    {
        if (_details == null)
        {
            _details = GetNodeOrNull<Label>("Margin/VBox/Details/Scroll/DetailsText");
            if (_details == null)
            {
                return;
            }
        }

        if (index < 0 || index >= _entries.Count)
        {
            _latestDetailText = string.Empty;
            if (_details != null)
            {
                _details.Text = string.Empty;
            }
            return;
        }

        _latestDetailText = _entries[index].DetailText ?? string.Empty;
        if (_details != null)
        {
            _details.Text = _latestDetailText;
        }
    }
}
