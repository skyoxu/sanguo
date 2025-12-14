namespace Game.Core.Contracts;

/// <summary>
/// Core game engine event type constants.
/// These constants define the event types for core game engine functionality.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (Event Bus and Contracts), ADR-0021 (C# Domain Layer Architecture)
/// </remarks>
public static class CoreGameEvents
{
    /// <summary>
    /// Event type: game.started
    /// Emitted when the game engine starts
    /// </summary>
    public const string GameStarted = "game.started";

    /// <summary>
    /// Event type: game.ended
    /// Emitted when the game engine ends
    /// </summary>
    public const string GameEnded = "game.ended";

    /// <summary>
    /// Event type: score.changed
    /// Emitted when player score changes
    /// </summary>
    public const string ScoreChanged = "score.changed";

    /// <summary>
    /// Event type: core.score.updated
    /// Emitted when player score updates (preferred)
    /// </summary>
    public const string ScoreUpdated = "core.score.updated";

    /// <summary>
    /// Event type: player.health.changed
    /// Emitted when player health changes
    /// </summary>
    public const string PlayerHealthChanged = "player.health.changed";

    /// <summary>
    /// Event type: core.health.updated
    /// Emitted when player health updates (preferred)
    /// </summary>
    public const string HealthUpdated = "core.health.updated";

    /// <summary>
    /// Event type: player.damaged
    /// Emitted when player takes damage
    /// </summary>
    public const string PlayerDamaged = "player.damaged";

    /// <summary>
    /// Event type: player.moved
    /// Emitted when player position changes
    /// </summary>
    public const string PlayerMoved = "player.moved";

    /// <summary>
    /// Event type: game.save.created
    /// Emitted when a game save is created
    /// </summary>
    public const string GameSaveCreated = "game.save.created";

    /// <summary>
    /// Event type: game.state.manager.updated
    /// Emitted when the game state manager updates its state
    /// </summary>
    public const string GameStateManagerUpdated = "game.state.manager.updated";

    /// <summary>
    /// Event type: game.save.loaded
    /// Emitted when a game save is loaded
    /// </summary>
    public const string GameSaveLoaded = "game.save.loaded";

    /// <summary>
    /// Event type: game.save.deleted
    /// Emitted when a game save is deleted
    /// </summary>
    public const string GameSaveDeleted = "game.save.deleted";

    /// <summary>
    /// Event type: game.autosave.enabled
    /// Emitted when autosave is enabled
    /// </summary>
    public const string GameAutosaveEnabled = "game.autosave.enabled";

    /// <summary>
    /// Event type: game.autosave.disabled
    /// Emitted when autosave is disabled
    /// </summary>
    public const string GameAutosaveDisabled = "game.autosave.disabled";

    /// <summary>
    /// Event type: game.autosave.completed
    /// Emitted when an autosave operation completes
    /// </summary>
    public const string GameAutosaveCompleted = "game.autosave.completed";
}
