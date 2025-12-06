namespace Game.Core.Domain.Entities;

public class Achievement
{
    public string Id { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public string AchievementKey { get; set; } = string.Empty;
    public long UnlockedAt { get; set; }
    public double Progress { get; set; }
}

