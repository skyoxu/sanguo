using Game.Core.Domain.ValueObjects;

namespace Game.Core.Domain;

/// <summary>
/// Immutable snapshot of a Sanguo player for cross-layer reads (UI/AI).
/// </summary>
public sealed record SanguoPlayerView : ISanguoPlayerView
{
    public SanguoPlayerView(
        string playerId,
        Money money,
        int positionIndex,
        IReadOnlyCollection<string> ownedCityIds,
        bool isEliminated)
    {
        if (string.IsNullOrWhiteSpace(playerId))
            throw new ArgumentException("PlayerId must be non-empty.", nameof(playerId));

        if (positionIndex < 0)
            throw new ArgumentOutOfRangeException(nameof(positionIndex), "PositionIndex must be non-negative.");

        ArgumentNullException.ThrowIfNull(ownedCityIds, nameof(ownedCityIds));

        PlayerId = playerId;
        Money = money;
        PositionIndex = positionIndex;
        IsEliminated = isEliminated;
        OwnedCityIds = Array.AsReadOnly(ownedCityIds.ToArray());
    }

    public string PlayerId { get; }

    public Money Money { get; }

    public int PositionIndex { get; }

    public IReadOnlyCollection<string> OwnedCityIds { get; }

    public bool IsEliminated { get; }
}
