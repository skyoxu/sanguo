using System.Text.Json;

namespace Game.Core.Contracts;

/// <summary>
/// Represents an event payload that is already encoded as a JSON string.
/// </summary>
/// <remarks>
/// Use this for integration boundaries where a JSON string is produced outside of the core domain code.
/// Related ADRs: ADR-0004 (Event Bus and Contracts), ADR-0002 (Security Baseline)
/// </remarks>
public sealed record RawJsonEventData(string Json) : IEventData;

/// <summary>
/// Represents an event payload as a <see cref="JsonElement"/>, avoiding arbitrary runtime object instances.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (Event Bus and Contracts), ADR-0002 (Security Baseline)
/// </remarks>
public sealed record JsonElementEventData(JsonElement Value) : IEventData
{
    public static JsonElementEventData FromObject<T>(T value, JsonSerializerOptions? options = null)
        => new(JsonSerializer.SerializeToElement(value, options));
}

