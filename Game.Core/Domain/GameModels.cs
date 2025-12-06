using Game.Core.Domain.ValueObjects;

namespace Game.Core.Domain;

public enum Difficulty
{
    Easy,
    Medium,
    Hard
}

public record GameConfig(
    int MaxLevel,
    int InitialHealth,
    double ScoreMultiplier,
    bool AutoSave,
    Difficulty Difficulty
);

public record GameState(
    string Id,
    int Level,
    int Score,
    int Health,
    IReadOnlyList<string> Inventory,
    Position Position,
    DateTime Timestamp
);

