using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Domain data: per-player money delta for a monthly settlement.
/// </summary>
/// <remarks>
/// This type is only used as part of <see cref="SanguoMonthSettled"/> data, not as a standalone CloudEvents type.
/// </remarks>
public sealed record PlayerSettlement(
    string PlayerId,
    decimal AmountDelta
);

/// <summary>
/// Domain event: core.sanguo.economy.month.settled
/// Description: Emitted after completing the month-end settlement for all players.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0006 (data storage), ADR-0005 (quality gates), ADR-0015 (performance budgets), ADR-0024 (Sanguo template lineage).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoMonthSettled(
    string GameId,
    int Year,
    int Month,
    IReadOnlyList<PlayerSettlement> PlayerSettlements,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.economy.month.settled";
}

/// <summary>
/// Domain event: core.sanguo.economy.season.event.applied
/// Description: Emitted when a quarterly environment event is applied to one or more regions/cities.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0006, ADR-0015, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoSeasonEventApplied(
    string GameId,
    int Year,
    int Season, // 1-4
    IReadOnlyList<string> AffectedRegionIds,
    decimal YieldMultiplier,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.economy.season.event.applied";
}

/// <summary>
/// Domain event: core.sanguo.economy.year.price.adjusted
/// Description: Emitted when the yearly land price adjustment is applied to a city.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0006, ADR-0015, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/_index.md.
/// </remarks>
public sealed record SanguoYearPriceAdjusted(
    string GameId,
    int Year,
    string CityId,
    decimal OldPrice,
    decimal NewPrice,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.economy.year.price.adjusted";
}

/// <summary>
/// Domain event: core.sanguo.city.bought
/// Description: Emitted when a player successfully buys a city.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004, ADR-0005, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-功能纵切-T2-三国大富翁闭环.md.
/// </remarks>
public sealed record SanguoCityBought(
    string GameId,
    string BuyerId,
    string CityId,
    decimal Price,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.city.bought";
}

/// <summary>
/// Domain event: core.sanguo.city.toll.paid
/// Description: Emitted when a player stops on another player's city and pays a toll.
/// </summary>
/// <remarks>
/// Amount semantics:
/// - Amount: money deducted from payer (may be higher than OwnerAmount when the owner hits the money cap).
/// - OwnerAmount: actual money credited to owner after cap is applied.
/// - TreasuryOverflow: overflow amount deposited into treasury due to owner money cap.
/// All amounts are expressed in major units.
/// 
/// Related ADRs: ADR-0004, ADR-0005, ADR-0024.
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-T2/08/08-功能纵切-T2-三国大富翁闭环.md.
/// </remarks>
public sealed record SanguoCityTollPaid(
    string GameId,
    string PayerId,
    string OwnerId,
    string CityId,
    decimal Amount,
    decimal OwnerAmount,
    decimal TreasuryOverflow,
    DateTimeOffset OccurredAt,
    string CorrelationId,
    string? CausationId
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.sanguo.city.toll.paid";
}
