using System.Collections.Generic;

namespace Game.Core.Services.Sanguo;

public enum EventTileType
{
    Normal = 0,
    Event = 1,
}

public sealed class EventTileAutoTriggerEnforcementModule
{
    private readonly List<string> auditTrail = new();

    public bool IsAwaitingMandatoryEventResolution { get; private set; }

    public bool IsTurnClosed { get; private set; }

    public bool IsSkipEnabled { get; private set; } = true;

    public bool IsEndTurnEnabled { get; private set; } = true;

    public bool IsShopEnabled { get; private set; } = true;

    public IReadOnlyList<string> AuditTrail => auditTrail;

    public void OnPlayerLanded(EventTileType tileType)
    {
        auditTrail.Add("PlayerLanded");

        if (tileType == EventTileType.Event)
        {
            IsAwaitingMandatoryEventResolution = true;
            IsTurnClosed = false;
            IsSkipEnabled = false;
            IsEndTurnEnabled = false;
            IsShopEnabled = false;
            auditTrail.Add("MandatoryEventResolutionEntered");
            return;
        }

        IsAwaitingMandatoryEventResolution = false;
        IsTurnClosed = true;
        IsSkipEnabled = true;
        IsEndTurnEnabled = true;
        IsShopEnabled = true;
        auditTrail.Add("TurnEnded");
    }

    public bool TrySkip() => !IsAwaitingMandatoryEventResolution && IsSkipEnabled;

    public bool TryEndTurn() => !IsAwaitingMandatoryEventResolution && IsEndTurnEnabled;

    public bool TryOpenShop() => !IsAwaitingMandatoryEventResolution && IsShopEnabled;
}
