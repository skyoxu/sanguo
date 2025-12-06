namespace Game.Core.Contracts;

public record DomainEvent(
    string Type,
    string Source,
    object? Data,
    DateTime Timestamp,
    string Id,
    string SpecVersion = "1.0",
    string DataContentType = "application/json"
);

