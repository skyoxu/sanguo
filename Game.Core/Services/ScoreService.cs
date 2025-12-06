using Game.Core.Domain;

namespace Game.Core.Services;

public class ScoreService
{
    public int Score { get; private set; }

    public int ComputeAddedScore(int basePoints, GameConfig config)
    {
        if (basePoints < 0) basePoints = 0;
        var difficultyMultiplier = config.Difficulty switch
        {
            Difficulty.Easy => 0.9,
            Difficulty.Medium => 1.0,
            Difficulty.Hard => 1.2,
            _ => 1.0
        };
        var added = (int)Math.Round(basePoints * config.ScoreMultiplier * difficultyMultiplier);
        return Math.Max(0, added);
    }

    public void Add(int basePoints, GameConfig config)
    {
        Score += ComputeAddedScore(basePoints, config);
    }

    public void Reset() => Score = 0;
}
