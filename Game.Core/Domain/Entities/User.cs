namespace Game.Core.Domain.Entities;

public class User
{
    public string Id { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
    public long CreatedAt { get; set; }
    public long? LastLogin { get; set; }
}

