using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain event: core.sanguo.region.captured
/// Description: Emitted when a player captures a region by owning all cities in the region.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t64-regions.md.
/// </remarks>
public sealed record SanguoRegionCaptured(
    string GameId,
    string RegionId,
    string OwnerId,
    IReadOnlyList<string> CityIds,
    string ReasonCode,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    public const string ReasonCaptured = "captured";

    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.region.captured";
}

/// <summary>
/// Domain event: core.sanguo.region.lost
/// Description: Emitted when a region capture status is lost.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-t64-regions.md.
/// </remarks>
public sealed record SanguoRegionLost(
    string GameId,
    string RegionId,
    string OwnerId,
    string ReasonCode,
    string? TriggerCityId,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    public const string ReasonLostLastCity = "lost_last_city";
    public const string ReasonOwnerChanged = "owner_changed";

    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.region.lost";
}
