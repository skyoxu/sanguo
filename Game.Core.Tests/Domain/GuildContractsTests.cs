using System;
using FluentAssertions;
using Game.Core.Contracts.Guild;
using Xunit;

namespace Game.Core.Tests.Domain;

public sealed class GuildContractsTests
{
    [Fact]
    public void GuildMemberJoinedEventHasExpectedEventType()
    {
        GuildMemberJoined.EventType.Should().Be("core.guild.member.joined");
    }

    [Fact]
    public void CanCreateGuildMemberJoinedWithBasicValues()
    {
        var now = DateTimeOffset.UtcNow;

        var evt = new GuildMemberJoined(
            UserId: "user-1",
            GuildId: "guild-1",
            JoinedAt: now,
            Role: "member"
        );

        evt.UserId.Should().Be("user-1");
        evt.GuildId.Should().Be("guild-1");
        evt.Role.Should().Be("member");
        evt.JoinedAt.Should().Be(now);
    }
}

