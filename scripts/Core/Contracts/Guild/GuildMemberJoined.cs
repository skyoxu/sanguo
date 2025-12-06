namespace Game.Contracts.Guild;

/// <summary>
/// Domain event: app.guild.member.joined
/// Description: Emitted when a user joins a guild.
/// </summary>
public sealed record GuildMemberJoined(
    string UserId,
    string GuildId,
    System.DateTimeOffset JoinedAt,
    string Role // member | admin
)
{
    public const string EventType = "app.guild.member.joined";
}

