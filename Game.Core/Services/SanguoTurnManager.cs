using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services;

public sealed class SanguoTurnManager
{
    private readonly IEventBus _bus;
    private readonly SanguoEconomyManager _economy;

    private string? _gameId;
    private string[]? _playerOrder;
    private int _activePlayerIndex;
    private int _turnNumber;
    private DateTime _currentDate;
    private bool _started;

    public SanguoTurnManager(IEventBus bus, SanguoEconomyManager economy)
    {
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
        _economy = economy ?? throw new ArgumentNullException(nameof(economy));
    }

    public void StartNewGame(
        string gameId,
        string[] playerOrder,
        int year,
        int month,
        int day,
        string correlationId,
        string? causationId
    )
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (playerOrder is null)
            throw new ArgumentNullException(nameof(playerOrder));

        if (playerOrder.Length == 0)
            throw new ArgumentException("Player order must contain at least one player.", nameof(playerOrder));

        if (playerOrder.Any(p => string.IsNullOrWhiteSpace(p)))
            throw new ArgumentException("Player order must not contain empty player ids.", nameof(playerOrder));

        if (playerOrder.Distinct(StringComparer.Ordinal).Count() != playerOrder.Length)
            throw new ArgumentException("Player order must not contain duplicate player ids.", nameof(playerOrder));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        var date = new DateTime(year, month, day);

        _gameId = gameId;
        _playerOrder = playerOrder.ToArray();
        _activePlayerIndex = 0;
        _turnNumber = 1;
        _currentDate = date;
        _started = true;

        var occurredAt = DateTimeOffset.UtcNow;

        var evt = new DomainEvent(
            Type: SanguoGameTurnStarted.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoGameTurnStarted(
                GameId: _gameId,
                TurnNumber: _turnNumber,
                ActivePlayerId: _playerOrder[_activePlayerIndex],
                Year: _currentDate.Year,
                Month: _currentDate.Month,
                Day: _currentDate.Day,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        );

        _ = _bus.PublishAsync(evt);
    }

    public void AdvanceTurn(string correlationId, string? causationId)
    {
        if (!_started || _gameId is null || _playerOrder is null)
            throw new InvalidOperationException("Game has not been started. Call StartNewGame first.");

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        var occurredAt = DateTimeOffset.UtcNow;
        var previousDate = _currentDate;

        var ended = new DomainEvent(
            Type: SanguoGameTurnEnded.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoGameTurnEnded(
                GameId: _gameId,
                TurnNumber: _turnNumber,
                ActivePlayerId: _playerOrder[_activePlayerIndex],
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        );
        _ = _bus.PublishAsync(ended);

        _turnNumber += 1;
        _activePlayerIndex = (_activePlayerIndex + 1) % _playerOrder.Length;
        _currentDate = _currentDate.AddDays(1);

        _economy.PublishMonthSettlementIfBoundary(
            gameId: _gameId,
            previousDate: previousDate,
            currentDate: _currentDate,
            settlements: Array.Empty<PlayerSettlement>(),
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);

        var season = GetSeasonFromMonth(_currentDate.Month);
        _economy.PublishSeasonEventIfBoundary(
            gameId: _gameId,
            previousDate: previousDate,
            currentDate: _currentDate,
            season: season,
            affectedRegionIds: Array.Empty<string>(),
            yieldMultiplier: 1.0m,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);

        var advanced = new DomainEvent(
            Type: SanguoGameTurnAdvanced.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoGameTurnAdvanced(
                GameId: _gameId,
                TurnNumber: _turnNumber,
                ActivePlayerId: _playerOrder[_activePlayerIndex],
                Year: _currentDate.Year,
                Month: _currentDate.Month,
                Day: _currentDate.Day,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        );
        _ = _bus.PublishAsync(advanced);

        var started = new DomainEvent(
            Type: SanguoGameTurnStarted.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoGameTurnStarted(
                GameId: _gameId,
                TurnNumber: _turnNumber,
                ActivePlayerId: _playerOrder[_activePlayerIndex],
                Year: _currentDate.Year,
                Month: _currentDate.Month,
                Day: _currentDate.Day,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        );
        _ = _bus.PublishAsync(started);
    }

    private static int GetSeasonFromMonth(int month)
    {
        if (month is < 1 or > 12)
            throw new ArgumentOutOfRangeException(nameof(month), "Month must be between 1 and 12.");

        return ((month - 1) / 3) + 1;
    }
}
