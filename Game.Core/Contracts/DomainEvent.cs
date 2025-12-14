namespace Game.Core.Contracts;

/// <summary>
/// Domain event envelope (CloudEvents-like) used for cross-layer communication.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (Event Bus and Contracts), ADR-0002 (Security Baseline)
/// </remarks>
public record DomainEvent(
    string Type,
    string Source,
    IEventData? Data,
    DateTime Timestamp,
    string Id,
    string SpecVersion = "1.0",
    string DataContentType = "application/json"
);
