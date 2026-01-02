using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Utilities;

namespace Game.Core.Services;

public sealed class SanguoTurnManager
{
    private readonly IEventBus _bus;
    private readonly SanguoEconomyManager _economy;
    private readonly SanguoBoardState _boardState;
    private readonly SanguoTreasury _treasury;
    private readonly IRandomNumberGenerator _rng;
    private readonly ISanguoAiDecisionPolicy _aiDecisionPolicy;
    private readonly int _totalPositionsHint;
    private readonly double _quarterEnvironmentEventTriggerChance;
    private readonly decimal _quarterEnvironmentEventYieldMultiplier;

    private string? _gameId;
    private string[]? _playerOrder;
    private int _activePlayerIndex;
    private int _turnNumber;
    private SanguoCalendarDate _currentDate;
    private bool _started;

    public SanguoTurnManager(
        IEventBus bus,
        SanguoEconomyManager economy,
        SanguoBoardState boardState,
        SanguoTreasury treasury,
        ISanguoAiDecisionPolicy? aiDecisionPolicy = null,
        IRandomNumberGenerator? rng = null,
        int totalPositionsHint = 0,
        double quarterEnvironmentEventTriggerChance = 0.5,
        decimal quarterEnvironmentEventYieldMultiplier = 0.9m)
    {
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
        _economy = economy ?? throw new ArgumentNullException(nameof(economy));
        _boardState = boardState ?? throw new ArgumentNullException(nameof(boardState));
        _treasury = treasury ?? throw new ArgumentNullException(nameof(treasury));
        _aiDecisionPolicy = aiDecisionPolicy ?? new DefaultSanguoAiDecisionPolicy();
        _rng = rng ?? ThreadLocalRandomNumberGenerator.Instance;
        _totalPositionsHint = totalPositionsHint;
        _quarterEnvironmentEventTriggerChance = quarterEnvironmentEventTriggerChance;
        _quarterEnvironmentEventYieldMultiplier = quarterEnvironmentEventYieldMultiplier;
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

        var date = new SanguoCalendarDate(year, month, day);

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

        var previousSeason = GetSeasonFromMonth(previousDate.Month);
        var currentSeason = GetSeasonFromMonth(_currentDate.Month);
        if (previousSeason != currentSeason)
        {
            _economy.SetActiveSeasonYieldAdjustment(
                year: _currentDate.Year,
                season: currentSeason,
                affectedRegionIds: Array.Empty<string>(),
                yieldMultiplier: 1.0m);

            var roll = _rng.NextDouble();
            if (roll < _quarterEnvironmentEventTriggerChance)
            {
                var regionIds = _boardState.GetCitiesSnapshot().Values
                    .Select(c => c.RegionId)
                    .Distinct(StringComparer.Ordinal)
                    .OrderBy(x => x, StringComparer.Ordinal)
                    .ToArray();

                if (regionIds.Length > 0)
                {
                    var affectedIndex = _rng.NextInt(minInclusive: 0, maxExclusive: regionIds.Length);
                    var affectedRegionIds = new[] { regionIds[affectedIndex] };

                    _economy.SetActiveSeasonYieldAdjustment(
                        year: _currentDate.Year,
                        season: currentSeason,
                        affectedRegionIds: affectedRegionIds,
                        yieldMultiplier: _quarterEnvironmentEventYieldMultiplier);

                    await _economy.PublishSeasonEventIfBoundaryAsync(
                        gameId: _gameId,
                        previousDate: previousDate,
                        currentDate: _currentDate,
                        season: currentSeason,
                        affectedRegionIds: affectedRegionIds,
                        yieldMultiplier: _quarterEnvironmentEventYieldMultiplier,
                        correlationId: correlationId,
                        causationId: causationId,
                        occurredAt: occurredAt);
                }
            }
        }

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

    private int ResolveTotalPositions()
    {
        if (_totalPositionsHint > 0)
            return _totalPositionsHint;

        // Best-effort fallback: derive from known city/player position indices to avoid 0/negative values.
        var maxIndex = 0;
        foreach (var city in _boardState.GetCitiesSnapshot().Values)
            maxIndex = Math.Max(maxIndex, city.PositionIndex);

        if (_playerOrder is not null)
        {
            foreach (var playerId in _playerOrder)
            {
                if (!_boardState.TryGetPlayer(playerId, out var p) || p is null)
                    continue;
                maxIndex = Math.Max(maxIndex, p.PositionIndex);
            }
        }

        return maxIndex + 1;
    }

    private static City? TryGetCityAtPositionIndex(IReadOnlyDictionary<string, City> citiesById, int positionIndex)
    {
        foreach (var city in citiesById.Values)
        {
            if (city.PositionIndex == positionIndex)
                return city;
        }
        return null;
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

        if (!_boardState.TryGetPlayer(activePlayerId, out var aiPlayer) || aiPlayer is null)
            return;

        var view = aiPlayer.ToView();
        var aiDecision = _aiDecisionPolicy.Decide(view);

        var decision = new SanguoAiDecisionMade(
            GameId: _gameId,
            AiPlayerId: activePlayerId,
            DecisionType: aiDecision.DecisionType.ToString(),
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

        if (aiDecision.DecisionType == SanguoAiDecisionType.Skip)
            return;

        await ExecuteAiRollDiceAndResolveAsync(
            aiPlayerId: activePlayerId,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
    }

    private async Task ExecuteAiRollDiceAndResolveAsync(
        string aiPlayerId,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        if (_gameId is null || _playerOrder is null)
            return;

        if (!_boardState.TryGetPlayer(aiPlayerId, out var aiPlayer) || aiPlayer is null)
            return;

        if (aiPlayer.IsEliminated)
            return;

        var totalPositions = ResolveTotalPositions();
        if (totalPositions <= 0)
            return;

        var value = _rng.NextInt(1, 7);
        var dice = new DomainEvent(
            Type: SanguoDiceRolled.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoDiceRolled(
                GameId: _gameId,
                PlayerId: aiPlayerId,
                Value: value,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId)),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N"));
        await _bus.PublishAsync(dice);

        var fromIndex = aiPlayer.PositionIndex;
        if (fromIndex < 0)
            fromIndex = 0;
        if (fromIndex >= totalPositions)
            fromIndex %= totalPositions;

        var start = new CircularMapPosition(fromIndex, totalPositions);
        var end = start.Advance(value);
        var toIndex = end.Current;
        var passedStart = fromIndex + value >= totalPositions;

        aiPlayer.MoveToPosition(toIndex);

        var moved = new DomainEvent(
            Type: SanguoTokenMoved.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoTokenMoved(
                GameId: _gameId,
                PlayerId: aiPlayerId,
                FromIndex: fromIndex,
                ToIndex: toIndex,
                Steps: value,
                PassedStart: passedStart,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId)),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N"));
        await _bus.PublishAsync(moved);

        // Greedy execution: after moving, resolve city rules using the same entrypoints as the human loop would.
        var citiesById = _boardState.GetCitiesSnapshot();
        var city = TryGetCityAtPositionIndex(citiesById, toIndex);
        if (city is null)
            return;

        var players = new List<SanguoPlayer>(_playerOrder.Length);
        foreach (var pid in _playerOrder)
        {
            if (!_boardState.TryGetPlayer(pid, out var p) || p is null)
                throw new InvalidOperationException($"Player not found in board state: {pid}");
            players.Add(p);
        }

        if (_boardState.TryGetOwnerOfCity(city.Id, out var owner) && owner is not null)
        {
            if (!StringComparer.Ordinal.Equals(owner.PlayerId, aiPlayerId))
            {
                _ = await _economy.TryPayTollAndPublishEventAsync(
                    gameId: _gameId,
                    players: players,
                    citiesById: citiesById,
                    treasury: _treasury,
                    payerId: aiPlayerId,
                    cityId: city.Id,
                    tollMultiplier: 1.0m,
                    correlationId: correlationId,
                    causationId: causationId,
                    occurredAt: occurredAt);
            }
            return;
        }

        _ = await _economy.TryBuyCityAndPublishEventAsync(
            gameId: _gameId,
            players: players,
            citiesById: citiesById,
            buyerId: aiPlayerId,
            cityId: city.Id,
            priceMultiplier: 1.0m,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
    }
}
