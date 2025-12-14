namespace Game.Core.Contracts.Guild;

/// <summary>
/// Domain event: core.guild.member.joined
/// Description: Emitted when a user joins a guild.
/// </summary>
/// <remarks>
/// ADR references: ADR-0004 (event bus and contracts), ADR-0018 (Godot C# tech stack), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-Guild-Manager/08/_index.md.
/// </remarks>
public sealed record GuildMemberJoined(
    string UserId,
    string GuildId,
    System.DateTimeOffset JoinedAt,
    string Role // member | admin
)
{
    /// <summary>
    /// CloudEvents type for this domain event.
    /// </summary>
    public const string EventType = "core.guild.member.joined";
}
