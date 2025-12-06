using Game.Core.Domain;

namespace Game.Core.State;

public record SaveMetadata(DateTime CreatedAt, DateTime UpdatedAt, string Version, string Checksum);

public record SaveData(
    string Id,
    GameState State,
    GameConfig Config,
    SaveMetadata Metadata,
    string? Screenshot = null,
    string? Title = null
);

public record GameStateManagerOptions(
    string StorageKey = "guild-manager-game",
    int MaxSaves = 10,
    TimeSpan AutoSaveInterval = default,
    bool EnableCompression = false
)
{
    public static GameStateManagerOptions Default => new(
        StorageKey: "guild-manager-game",
        MaxSaves: 10,
        AutoSaveInterval: TimeSpan.FromSeconds(30),
        EnableCompression: false
    );
}
