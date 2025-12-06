namespace Game.Core.Domain;

public record GameStatistics(
    int TotalMoves,
    int ItemsCollected,
    int EnemiesDefeated,
    double DistanceTraveled,
    double AverageReactionTime
);

public record GameResult(
    int FinalScore,
    int LevelReached,
    double PlayTimeSeconds,
    IReadOnlyList<string> Achievements,
    GameStatistics Statistics
);

