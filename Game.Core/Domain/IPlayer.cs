using Game.Core.Domain.ValueObjects;

namespace Game.Core.Domain;

/// <summary>
/// Read-only player projection used by core systems.
/// </summary>
public interface IPlayer
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
    /// Owned city ids.
    /// </summary>
    IReadOnlyCollection<string> OwnedCityIds { get; }
}
