namespace Game.Core.Domain.Entities;

public class SaveGame
{
    public string Id { get; set; } = string.Empty;
    public string UserId { get; set; } = string.Empty;
    public int SlotNumber { get; set; }
    public string Data { get; set; } = string.Empty; // JSON
    public long CreatedAt { get; set; }
    public long UpdatedAt { get; set; }
}

