namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// Serializable snapshot of the Sanguo game runtime state for save/load.
/// </summary>
/// <remarks>
/// This is a contract/DTO (SSoT) and MUST remain Godot-free for fast unit testing.
///
/// Related ADRs: ADR-0006 (data storage), ADR-0004 (event contracts), ADR-0018 (Godot+C# template lineage).
/// </remarks>
public sealed record SanguoSaveSnapshot(
    string GameId,
    int TurnNumber,
    int ActivePlayerIndex,
    int Year,
    int Month,
    int Day,
    IReadOnlyList<string> PlayerOrder,
    IReadOnlyList<SanguoSavePlayer> Players,
    IReadOnlyList<SanguoSaveCityEconomy> CityEconomy,
    long TreasuryMinorUnits,
    string ContentPackId = "",
    int ContentPackVersion = 0
);

/// <summary>
/// Serializable per-player save data.
/// </summary>
public sealed record SanguoSavePlayer(
    string PlayerId,
    decimal Money,
    int PositionIndex,
    bool IsEliminated,
    IReadOnlyList<string> OwnedCityIds
);

/// <summary>
/// Serializable economy values for a city.
/// </summary>
public sealed record SanguoSaveCityEconomy(
    string CityId,
    decimal BasePrice,
    decimal BaseToll
);

