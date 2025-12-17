using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Utilities;

namespace Game.Core.Services;

public sealed class SanguoDiceService
{
    private readonly IEventBus _bus;

    public SanguoDiceService(IEventBus bus)
    {
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
    }

    public int RollD6(string gameId, string playerId, string correlationId, string? causationId)
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (string.IsNullOrWhiteSpace(playerId))
            throw new ArgumentException("PlayerId must be non-empty.", nameof(playerId));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        var value = RandomHelper.NextInt(1, 7);
        var occurredAt = DateTimeOffset.UtcNow;

        var evt = new DomainEvent(
            Type: SanguoDiceRolled.EventType,
            Source: nameof(SanguoDiceService),
            Data: JsonElementEventData.FromObject(new
            {
                GameId = gameId,
                PlayerId = playerId,
                Value = value,
                OccurredAt = occurredAt,
                CorrelationId = correlationId,
                CausationId = causationId,
            }),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        );

        _bus.PublishAsync(evt).GetAwaiter().GetResult();
        return value;
    }
}

