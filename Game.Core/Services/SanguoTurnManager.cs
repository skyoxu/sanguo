using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;

namespace Game.Core.Services;

public sealed class SanguoTurnManager
{
    private readonly IEventBus _bus;
    private readonly SanguoEconomyManager _economy;
    private readonly SanguoBoardState _boardState;
    private readonly SanguoTreasury _treasury;

    private string? _gameId;
    private string[]? _playerOrder;
    private int _activePlayerIndex;
    private int _turnNumber;
    private DateTime _currentDate;
    private bool _started;

    public SanguoTurnManager(
        IEventBus bus,
        SanguoEconomyManager economy,
        SanguoBoardState boardState,
        SanguoTreasury treasury)
    {
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
        _economy = economy ?? throw new ArgumentNullException(nameof(economy));
        _boardState = boardState ?? throw new ArgumentNullException(nameof(boardState));
        _treasury = treasury ?? throw new ArgumentNullException(nameof(treasury));
    }

    public async Task StartNewGameAsync(
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

        foreach (var playerId in playerOrder)
        {
            if (!_boardState.TryGetPlayer(playerId, out _))
                throw new ArgumentException($"PlayerId not found in board state: {playerId}", nameof(playerOrder));
        }

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

        await _bus.PublishAsync(evt);
        await PublishAiDecisionIfNeededAsync(
            activePlayerId: _playerOrder[_activePlayerIndex],
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
    }

    public async Task AdvanceTurnAsync(string correlationId, string? causationId)
    {
        if (!_started || _gameId is null || _playerOrder is null)
            throw new InvalidOperationException("Game has not been started. Call StartNewGame first.");

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        if (await TryEndGameIfHumanEliminatedAsync(correlationId: correlationId, causationId: causationId))
        {
            return;
        }

        var occurredAt = DateTimeOffset.UtcNow;
        var previousDate = _currentDate;
        var activePlayerId = _playerOrder[_activePlayerIndex];

        var ended = new DomainEvent(
            Type: SanguoGameTurnEnded.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoGameTurnEnded(
                GameId: _gameId,
                TurnNumber: _turnNumber,
                ActivePlayerId: activePlayerId,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        );
        await _bus.PublishAsync(ended);

        PruneEliminatedAiPlayers(activePlayerId);
        if (_playerOrder.Length == 0)
        {
            _started = false;
            var evt = new DomainEvent(
                Type: SanguoGameEnded.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoGameEnded(
                    GameId: _gameId,
                    EndReason: "no_players",
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: DateTime.UtcNow,
                Id: Guid.NewGuid().ToString("N")
            );
            await _bus.PublishAsync(evt);
            return;
        }

        _turnNumber += 1;
        _activePlayerIndex = (_activePlayerIndex + 1) % _playerOrder.Length;
        _currentDate = _currentDate.AddDays(1);

        IReadOnlyList<PlayerSettlement> settlements = Array.Empty<PlayerSettlement>();
        if (previousDate.Year != _currentDate.Year || previousDate.Month != _currentDate.Month)
        {
            var snapshots = new List<SanguoPlayer.RollbackSnapshot>(_playerOrder.Length);
            foreach (var playerId in _playerOrder)
            {
                if (!_boardState.TryGetPlayer(playerId, out var player) || player is null)
                    throw new InvalidOperationException($"Player not found in board state: {playerId}");

                snapshots.Add(player.CaptureRollbackSnapshot());
            }

            var treasurySnapshot = _treasury.CaptureRollbackSnapshot();

            try
            {
                settlements = _economy.SettleMonth(_boardState, _playerOrder, _treasury);
                await _economy.PublishMonthSettlementIfBoundaryAsync(
                    gameId: _gameId,
                    previousDate: previousDate,
                    currentDate: _currentDate,
                    settlements: settlements,
                    correlationId: correlationId,
                    causationId: causationId,
                    occurredAt: occurredAt);
            }
            catch
            {
                for (var i = 0; i < _playerOrder.Length; i++)
                {
                    var playerId = _playerOrder[i];
                    _ = _boardState.TryGetPlayer(playerId, out var player);
                    player!.RestoreRollbackSnapshot(snapshots[i]);
                }

                _treasury.RestoreRollbackSnapshot(treasurySnapshot);
                throw;
            }
        }
        else
        {
            await _economy.PublishMonthSettlementIfBoundaryAsync(
                gameId: _gameId,
                previousDate: previousDate,
                currentDate: _currentDate,
                settlements: settlements,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt);
        }

        var season = GetSeasonFromMonth(_currentDate.Month);
        await _economy.PublishSeasonEventIfBoundaryAsync(
            gameId: _gameId,
            previousDate: previousDate,
            currentDate: _currentDate,
            season: season,
            affectedRegionIds: Array.Empty<string>(),
            yieldMultiplier: 1.0m,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);

        await _economy.PublishYearlyPriceAdjustmentIfBoundaryAsync(
            gameId: _gameId,
            previousDate: previousDate,
            currentDate: _currentDate,
            cities: CreateCityList(_boardState.GetCitiesSnapshot()),
            yearlyMultiplier: 1.0m,
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
        await _bus.PublishAsync(advanced);

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
        await _bus.PublishAsync(started);
        await PublishAiDecisionIfNeededAsync(
            activePlayerId: _playerOrder[_activePlayerIndex],
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
    }

    private async Task<bool> TryEndGameIfHumanEliminatedAsync(string correlationId, string? causationId)
    {
        if (_playerOrder is null || _gameId is null)
        {
            return false;
        }

        foreach (var playerId in _playerOrder)
        {
            if (IsAiPlayerId(playerId))
                continue;

            if (!_boardState.TryGetPlayer(playerId, out var player) || player is null)
                continue;

            if (!player.IsEliminated)
                continue;

            _started = false;

            var occurredAt = DateTimeOffset.UtcNow;
            var evt = new DomainEvent(
                Type: SanguoGameEnded.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoGameEnded(
                    GameId: _gameId,
                    EndReason: "human_eliminated",
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: DateTime.UtcNow,
                Id: Guid.NewGuid().ToString("N")
            );

            await _bus.PublishAsync(evt);
            return true;
        }

        return false;
    }

    private void PruneEliminatedAiPlayers(string activePlayerId)
    {
        if (_playerOrder is null || _playerOrder.Length == 0)
        {
            return;
        }

        var kept = new List<string>(_playerOrder.Length);
        foreach (var playerId in _playerOrder)
        {
            if (!_boardState.TryGetPlayer(playerId, out var player) || player is null)
            {
                kept.Add(playerId);
                continue;
            }

            if (player.IsEliminated && IsAiPlayerId(playerId))
                continue;

            kept.Add(playerId);
        }

        if (kept.Count == _playerOrder.Length)
        {
            return;
        }

        _playerOrder = kept.ToArray();
        _activePlayerIndex = Array.FindIndex(_playerOrder, x => string.Equals(x, activePlayerId, StringComparison.Ordinal));
    }

    private static IReadOnlyList<City> CreateCityList(IReadOnlyDictionary<string, City> citiesById)
    {
        var list = new System.Collections.Generic.List<City>(citiesById.Count);
        foreach (var city in citiesById.Values)
            list.Add(city);
        return list;
    }

    private static int GetSeasonFromMonth(int month)
    {
        if (month is < 1 or > 12)
            throw new ArgumentOutOfRangeException(nameof(month), "Month must be between 1 and 12.");

        return ((month - 1) / 3) + 1;
    }


    private static bool IsAiPlayerId(string playerId)
    {
        return playerId.StartsWith("ai-", StringComparison.OrdinalIgnoreCase);
    }

    private async Task PublishAiDecisionIfNeededAsync(
        string activePlayerId,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        if (_gameId is null)
            throw new InvalidOperationException("GameId is not set.");

        if (!IsAiPlayerId(activePlayerId))
            return;

        var decision = new SanguoAiDecisionMade(
            GameId: _gameId,
            AiPlayerId: activePlayerId,
            DecisionType: "skip",
            TargetCityId: null,
            OccurredAt: occurredAt,
            CorrelationId: correlationId,
            CausationId: causationId);

        var evt = new DomainEvent(
            Type: SanguoAiDecisionMade.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(decision),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N"));

        await _bus.PublishAsync(evt);
    }
}
