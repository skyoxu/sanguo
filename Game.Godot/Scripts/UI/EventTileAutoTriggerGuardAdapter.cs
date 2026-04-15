using System;
using System.Collections.Generic;
using Game.Core.Services.Sanguo;
using Godot;

namespace Game.Godot.Scripts.UI;

public partial class EventTileAutoTriggerGuardAdapter : RefCounted
{
    private readonly EventTileAutoTriggerEnforcementModule module = new();
    private readonly Dictionary<string, string> localizedEventNames = new(StringComparer.OrdinalIgnoreCase)
    {
        ["rebellion"] = "Rebellion Uprising",
        ["flood"] = "Great Flood",
    };

    public bool InEventResolution => module.IsAwaitingMandatoryEventResolution;

    public bool SkipEnabled => module.IsSkipEnabled;

    public bool EndTurnEnabled => module.IsEndTurnEnabled;

    public bool ShopEnabled => module.IsShopEnabled;

    public string PopupText { get; private set; } = string.Empty;

    public string TriggeredEventName { get; private set; } = string.Empty;

    public string PopupTitle { get; set; } = "Event Triggered";

    public void LandOnTile(string tileKind, string eventId)
    {
        if (!string.Equals(tileKind, "event", StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        module.OnPlayerLanded(EventTileType.Event);
        if (module.IsAwaitingMandatoryEventResolution)
        {
            UpdatePresentation(eventId);
        }
    }

    public void EnterResolution(string eventId)
    {
        module.OnPlayerLanded(EventTileType.Event);
        if (module.IsAwaitingMandatoryEventResolution)
        {
            UpdatePresentation(eventId);
        }
    }

    public bool TrySkip() => module.TrySkip();

    public bool TryEndTurn() => module.TryEndTurn();

    public bool TryOpenShop() => module.TryOpenShop();

    private void UpdatePresentation(string eventId)
    {
        TriggeredEventName = LocalizeEventName(eventId);
        PopupText = $"{PopupTitle}: {TriggeredEventName}";
    }

    private string LocalizeEventName(string eventId)
    {
        if (string.IsNullOrWhiteSpace(eventId))
        {
            return "Unknown Event";
        }

        return localizedEventNames.TryGetValue(eventId, out var value)
            ? value
            : "Unknown Event";
    }
}
