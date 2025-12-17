using Game.Core.Domain.ValueObjects;

namespace Game.Core.Domain;

/// <summary>
/// Read-only Sanguo player projection intended for UI/AI consumption.
/// </summary>
public interface ISanguoPlayerView
{
    /// <summary>
    /// Unique player identifier.
    /// </summary>
    string PlayerId { get; }

    /// <summary>
    /// Current money balance. Must never be negative and must not exceed the configured maximum.
    /// </summary>
    Money Money { get; }

    /// <summary>
    /// Current position on the board (0-based index).
    /// </summary>
    int PositionIndex { get; }

    /// <summary>
    /// Owned city ids.
    /// </summary>
    IReadOnlyCollection<string> OwnedCityIds { get; }

    /// <summary>
    /// True when this player has been eliminated and is locked from further actions.
    /// </summary>
    bool IsEliminated { get; }
}
