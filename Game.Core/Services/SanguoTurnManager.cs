using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Utilities;
using System.Diagnostics.CodeAnalysis;
using System.Security.Cryptography;
using System.Text;

namespace Game.Core.Services;

public sealed class SanguoTurnManager
{
    private readonly IEventBus _bus;
    private readonly SanguoEconomyManager _economy;
    private readonly SanguoBoardState _boardState;
    private readonly SanguoTreasury _treasury;
    private readonly IRandomNumberGenerator _rng;
    private readonly int _randomSeed;
    private readonly ISanguoAiDecisionPolicy _aiDecisionPolicy;
    private readonly int _totalPositionsHint;
    private readonly double _quarterEnvironmentEventTriggerChance;
    private readonly decimal _quarterEnvironmentEventYieldMultiplier;
    private readonly SanguoRandomEventsCatalog? _randomEventsCatalog;
    private readonly int _globalEventIntervalTurns;
    private readonly string _tileRandomEventPoolId;
    private readonly string _globalRandomEventPoolId;
    private readonly IReadOnlyDictionary<int, string>? _tileTypesByPositionIndex;
    private readonly Dictionary<string, int> _turnEventStepDeltasByPlayerId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, int> _turnActionCardStepDeltasByPlayerId = new(StringComparer.Ordinal);
    private readonly SanguoActionCardsCatalog? _actionCardsCatalog;
    private readonly Dictionary<string, Dictionary<string, int>> _randomEventLastAppliedRoundByPlayerId = new(StringComparer.Ordinal);
    private SanguoGlobalEventRoundGate _globalRoundGate = new();

    private string? _gameId;
    private string[]? _playerOrder;
    private int _startingPlayersCount;
    private int _activePlayerIndex;
    private int _turnNumber;
    private SanguoCalendarDate _currentDate;
    private bool _started;
    private string? _gameOverEndReason;
    private int? _actionCardPlayedTurnNumber;
    private int? _diceRolledTurnNumber;

    public SanguoTurnManager(
        IEventBus bus,
        SanguoEconomyManager economy,
        SanguoBoardState boardState,
        SanguoTreasury treasury,
        ISanguoAiDecisionPolicy? aiDecisionPolicy = null,
        IRandomNumberGenerator? rng = null,
        int randomSeed = 0,
        int totalPositionsHint = 0,
        double quarterEnvironmentEventTriggerChance = 0.5,
        decimal quarterEnvironmentEventYieldMultiplier = 0.5m,
        SanguoRandomEventsCatalog? randomEventsCatalog = null,
        int globalEventIntervalTurns = 5,
        string tileRandomEventPoolId = "default",
        string globalRandomEventPoolId = "global",
        SanguoActionCardsCatalog? actionCardsCatalog = null,
        IReadOnlyDictionary<int, string>? tileTypesByPositionIndex = null)
    {
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
        _economy = economy ?? throw new ArgumentNullException(nameof(economy));
        _boardState = boardState ?? throw new ArgumentNullException(nameof(boardState));
        _treasury = treasury ?? throw new ArgumentNullException(nameof(treasury));
        _aiDecisionPolicy = aiDecisionPolicy ?? new DefaultSanguoAiDecisionPolicy();
        _rng = rng ?? ThreadLocalRandomNumberGenerator.Instance;
        _randomSeed = randomSeed;
        _totalPositionsHint = totalPositionsHint;
        _quarterEnvironmentEventTriggerChance = quarterEnvironmentEventTriggerChance;
        _quarterEnvironmentEventYieldMultiplier = quarterEnvironmentEventYieldMultiplier;
        _randomEventsCatalog = randomEventsCatalog;
        _globalEventIntervalTurns = globalEventIntervalTurns;
        _tileRandomEventPoolId = tileRandomEventPoolId ?? throw new ArgumentNullException(nameof(tileRandomEventPoolId));
        _globalRandomEventPoolId = globalRandomEventPoolId ?? throw new ArgumentNullException(nameof(globalRandomEventPoolId));
        _actionCardsCatalog = actionCardsCatalog;
        _tileTypesByPositionIndex = tileTypesByPositionIndex;

        if (_globalEventIntervalTurns != 5 && _globalEventIntervalTurns != 10 && _globalEventIntervalTurns != 20)
            throw new ArgumentOutOfRangeException(nameof(globalEventIntervalTurns), "GlobalEventIntervalTurns must be one of: 5, 10, 20.");
    }

    [MemberNotNull(nameof(_gameId), nameof(_playerOrder))]
    private void EnsureStarted()
    {
        if (!_started || _gameId is null || _playerOrder is null)
        {
            if (_gameOverEndReason is not null)
                throw new InvalidOperationException($"GameOver: EndReason={_gameOverEndReason}. Call StartNewGame first.");

            throw new InvalidOperationException("Game has not been started. Call StartNewGame first.");
        }
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
        _startingPlayersCount = _playerOrder.Length;
        _activePlayerIndex = 0;
        _turnNumber = 1;
        _currentDate = date;
        _started = true;
        _gameOverEndReason = null;
        _actionCardPlayedTurnNumber = null;
        _diceRolledTurnNumber = null;
        _randomEventLastAppliedRoundByPlayerId.Clear();
        ResetTurnScopedEventStepDeltas();
        _globalRoundGate = new SanguoGlobalEventRoundGate();

        var occurredAt = DateTimeOffset.UtcNow;
        var activePlayerId = _playerOrder[_activePlayerIndex];

        await TryTriggerGlobalRoundRandomEventBeforeTurnStartedAsync(
            gameId: _gameId,
            activePlayerId: activePlayerId,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);

        var evt = new DomainEvent(
            Type: SanguoGameTurnStarted.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoGameTurnStarted(
                GameId: _gameId,
                TurnNumber: _turnNumber,
                ActivePlayerId: activePlayerId,
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
        await PublishPlayerStateChangedAsync(
            playerId: _playerOrder[_activePlayerIndex],
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
        await PublishAiDecisionIfNeededAsync(
            activePlayerId: _playerOrder[_activePlayerIndex],
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
    }


    public async Task ExecuteHumanRollDiceAndResolveAsync(string correlationId, string? causationId)
    {
        EnsureStarted();

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        if (await TryEndGameIfHumanEliminatedAsync(correlationId: correlationId, causationId: causationId))
        {
            return;
        }

        var activePlayerId = _playerOrder[_activePlayerIndex];
        if (IsAiPlayerId(activePlayerId))
        {
            return;
        }

        if (!_boardState.TryGetPlayer(activePlayerId, out var activePlayer) || activePlayer is null)
            throw new InvalidOperationException($"Player not found in board state: {activePlayerId}");

        var totalPositions = ResolveTotalPositions();
        var occurredAt = DateTimeOffset.UtcNow;
        _diceRolledTurnNumber = _turnNumber;
        var diceValue = _rng.NextInt(1, 7);

        await ExecuteRollDiceMoveAndResolveCityAsync(
            gameId: _gameId,
            playerOrder: _playerOrder,
            activePlayer: activePlayer,
            totalPositions: totalPositions,
            diceValue: diceValue,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);

        await TryEndGameIfHumanEliminatedAsync(correlationId: correlationId, causationId: causationId);
    }

    public async Task<bool> TryPlayHumanActionCardAsync(
        string cardId,
        string correlationId,
        string? causationId)
    {
        EnsureStarted();

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        if (string.IsNullOrWhiteSpace(cardId))
            throw new ArgumentException("CardId must be non-empty.", nameof(cardId));

        var activePlayerId = _playerOrder[_activePlayerIndex];
        if (IsAiPlayerId(activePlayerId))
        {
            return false;
        }

        var occurredAt = DateTimeOffset.UtcNow;

        if (_diceRolledTurnNumber == _turnNumber)
        {
            var rejected = new DomainEvent(
                Type: SanguoActionCardPlayRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoActionCardPlayRejected(
                    GameId: _gameId,
                    TurnNumber: _turnNumber,
                    RoundNumber: ComputeRoundNumber(_turnNumber),
                    PlayerId: activePlayerId,
                    Phase: SanguoTurnPhase.BeforeRoll.ToString(),
                    CardId: cardId,
                    ReasonCode: SanguoActionCardPlayRejected.ReasonNotBeforeRoll,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejected);
            return false;
        }

        if (_actionCardPlayedTurnNumber == _turnNumber)
        {
            var rejected = new DomainEvent(
                Type: SanguoActionCardPlayRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoActionCardPlayRejected(
                    GameId: _gameId,
                    TurnNumber: _turnNumber,
                    RoundNumber: ComputeRoundNumber(_turnNumber),
                    PlayerId: activePlayerId,
                    Phase: SanguoTurnPhase.BeforeRoll.ToString(),
                    CardId: cardId,
                    ReasonCode: SanguoActionCardPlayRejected.ReasonAlreadyPlayedThisTurn,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejected);
            return false;
        }

        if (_actionCardsCatalog is null)
        {
            var rejected = new DomainEvent(
                Type: SanguoActionCardPlayRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoActionCardPlayRejected(
                    GameId: _gameId,
                    TurnNumber: _turnNumber,
                    RoundNumber: ComputeRoundNumber(_turnNumber),
                    PlayerId: activePlayerId,
                    Phase: SanguoTurnPhase.BeforeRoll.ToString(),
                    CardId: cardId,
                    ReasonCode: SanguoActionCardPlayRejected.ReasonCatalogMissing,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejected);
            return false;
        }

        var card = _actionCardsCatalog.Cards.FirstOrDefault(c => string.Equals(c.CardId, cardId, StringComparison.Ordinal));
        if (card is null)
        {
            var rejected = new DomainEvent(
                Type: SanguoActionCardPlayRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoActionCardPlayRejected(
                    GameId: _gameId,
                    TurnNumber: _turnNumber,
                    RoundNumber: ComputeRoundNumber(_turnNumber),
                    PlayerId: activePlayerId,
                    Phase: SanguoTurnPhase.BeforeRoll.ToString(),
                    CardId: cardId,
                    ReasonCode: SanguoActionCardPlayRejected.ReasonUnknownCardId,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejected);
            return false;
        }

        if (!string.Equals(card.EffectKind, "economyStepDelta", StringComparison.Ordinal))
        {
            var rejected = new DomainEvent(
                Type: SanguoActionCardPlayRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoActionCardPlayRejected(
                    GameId: _gameId,
                    TurnNumber: _turnNumber,
                    RoundNumber: ComputeRoundNumber(_turnNumber),
                    PlayerId: activePlayerId,
                    Phase: SanguoTurnPhase.BeforeRoll.ToString(),
                    CardId: cardId,
                    ReasonCode: SanguoActionCardPlayRejected.ReasonInvalidCardEffectKind,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejected);
            return false;
        }

        var appliedAfter = CommitTurnActionCardEconomyStepDeltaAndGetSnapshot(activePlayerId, card.StepDelta);

        var played = new DomainEvent(
            Type: SanguoActionCardPlayed.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoActionCardPlayed(
                GameId: _gameId,
                PlayerId: activePlayerId,
                CardId: cardId,
                EffectKind: "economyStepDelta",
                StepDelta: card.StepDelta,
                DurationRounds: card.DurationRounds,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId,
                AppliedMultipliersAfter: appliedAfter
            )),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N"));
        await _bus.PublishAsync(played);

        _actionCardPlayedTurnNumber = _turnNumber;
        return true;
    }

    public async Task AdvanceTurnAsync(string correlationId, string? causationId)
    {
        EnsureStarted();

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        if (await TryEndGameIfHumanEliminatedAsync(correlationId: correlationId, causationId: causationId))
        {
            return;
        }

        var occurredAt = DateTimeOffset.UtcNow;
        var previousDate = _currentDate;
        var activePlayerId = _playerOrder[_activePlayerIndex];

        await TryTriggerGlobalTurnRandomEventIfBoundaryAsync(
            gameId: _gameId,
            activePlayerId: activePlayerId,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);

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

        ResetTurnScopedEventStepDeltas();

        PruneEliminatedAiPlayers(activePlayerId);
        if (_playerOrder.Length == 0)
        {
            _started = false;
            _gameOverEndReason = SanguoGameEnded.ReasonNoPlayers;
            var evt = new DomainEvent(
                Type: SanguoGameEnded.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoGameEnded(
                    GameId: _gameId,
                    EndReason: SanguoGameEnded.ReasonNoPlayers,
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

        if (_startingPlayersCount >= 2 && _playerOrder.Length == 1)
        {
            _started = false;
            _gameOverEndReason = SanguoGameEnded.ReasonLastActorStanding;

            var winnerPlayerId = _playerOrder[0];
            var evt = new DomainEvent(
                Type: SanguoGameEnded.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoGameEnded(
                    GameId: _gameId,
                    EndReason: SanguoGameEnded.ReasonLastActorStanding,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    WinnerPlayerId: winnerPlayerId
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
                    turnNumber: _turnNumber,
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
                turnNumber: _turnNumber,
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
                    var rngContextId = BuildRngContextId(
                        stream: "rng.events",
                        turnNumber: _turnNumber,
                        roundNumber: ComputeRoundNumber(_turnNumber),
                        sourceId: "quarter_env_region");
                    var candidatesSortedIdsHash = ComputeSha256Hex(string.Join("\n", regionIds));

                    _economy.SetActiveSeasonYieldAdjustment(
                        year: _currentDate.Year,
                        season: currentSeason,
                        affectedRegionIds: affectedRegionIds,
                        yieldMultiplier: _quarterEnvironmentEventYieldMultiplier);

                    await _economy.PublishSeasonEventIfBoundaryAsync(
                        gameId: _gameId,
                        turnNumber: _turnNumber,
                        previousDate: previousDate,
                        currentDate: _currentDate,
                        season: currentSeason,
                        affectedRegionIds: affectedRegionIds,
                        yieldMultiplier: _quarterEnvironmentEventYieldMultiplier,
                        correlationId: correlationId,
                        causationId: causationId,
                        occurredAt: occurredAt,
                        rngContextId: rngContextId,
                        candidatesSortedIdsHash: candidatesSortedIdsHash,
                        pickedIndex: affectedIndex,
                        pickedId: affectedRegionIds[0]);
                }
            }
        }

        var citiesBeforeYearly = CreateCityList(_boardState.GetCitiesSnapshot());
        IReadOnlyList<City> citiesAfterYearly = citiesBeforeYearly;
        if (previousDate.Year != _currentDate.Year)
        {
            citiesAfterYearly = _economy.ApplyYearlyPriceAdjustment(citiesBeforeYearly, _rng);
            _boardState.ApplyCityEconomyUpdates(citiesAfterYearly);
        }

        await _economy.PublishYearlyPriceAdjustmentIfBoundaryAsync(
            gameId: _gameId,
            turnNumber: _turnNumber,
            previousDate: previousDate,
            currentDate: _currentDate,
            previousCities: citiesBeforeYearly,
            currentCities: citiesAfterYearly,
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
        await PublishPlayerStateChangedAsync(
            playerId: _playerOrder[_activePlayerIndex],
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
        await PublishAiDecisionIfNeededAsync(
            activePlayerId: _playerOrder[_activePlayerIndex],
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
    }


    private async Task ExecuteRollDiceMoveAndResolveCityAsync(
        string gameId,
        string[] playerOrder,
        SanguoPlayer activePlayer,
        int totalPositions,
        int diceValue,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        if (totalPositions <= 0)
            return;

        var playerId = activePlayer.PlayerId;
        var value = Math.Clamp(diceValue, 1, 6);

        var fromIndex = activePlayer.PositionIndex;
        if (fromIndex < 0)
            fromIndex = 0;
        if (fromIndex >= totalPositions)
            fromIndex %= totalPositions;

        var start = new CircularMapPosition(fromIndex, totalPositions);
        var end = start.Advance(value);
        var toIndex = end.Current;
        var passedStart = fromIndex + value >= totalPositions;

        var dice = new DomainEvent(
            Type: SanguoDiceRolled.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoDiceRolled(
                GameId: gameId,
                PlayerId: playerId,
                Value: value,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId)),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N"));
        await _bus.PublishAsync(dice);

        activePlayer.MoveToPosition(toIndex);

        var moved = new DomainEvent(
            Type: SanguoTokenMoved.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoTokenMoved(
                GameId: gameId,
                PlayerId: playerId,
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

        var affectedPlayerIds = new HashSet<string>(StringComparer.Ordinal) { playerId };

        var citiesById = _boardState.GetCitiesSnapshot();
        var city = TryGetCityAtPositionIndex(citiesById, toIndex);
        if (city is not null)
        {
            var players = new List<SanguoPlayer>(playerOrder.Length);
            foreach (var pid in playerOrder)
            {
                if (!_boardState.TryGetPlayer(pid, out var p) || p is null)
                    throw new InvalidOperationException($"Player not found in board state: {pid}");
                players.Add(p);
            }

            if (_boardState.TryGetOwnerOfCity(city.Id, out var owner) && owner is not null)
            {
                if (!StringComparer.Ordinal.Equals(owner.PlayerId, playerId))
                {
                    var paid = await _economy.TryPayTollAndPublishEventAsync(
                        gameId: gameId,
                        turnNumber: _turnNumber,
                        players: players,
                        citiesById: citiesById,
                        treasury: _treasury,
                        payerId: playerId,
                        cityId: city.Id,
                        tollMultiplier: 1.0m,
                        correlationId: correlationId,
                        causationId: causationId,
                        occurredAt: occurredAt);

                    if (paid)
                        affectedPlayerIds.Add(owner.PlayerId);
                }
            }
            else
            {
                if (IsAiPlayerId(playerId))
                {
                    _ = await _economy.TryBuyCityAndPublishEventAsync(
                        gameId: gameId,
                        turnNumber: _turnNumber,
                        players: players,
                        citiesById: citiesById,
                        buyerId: playerId,
                        cityId: city.Id,
                        priceMultiplier: 1.0m,
                        correlationId: correlationId,
                        causationId: causationId,
                        occurredAt: occurredAt);
                }
            }
        }
        else
        {
            await TryTriggerTileRandomEventAsync(
                gameId: gameId,
                activePlayerId: playerId,
                positionIndex: toIndex,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt);
        }

        foreach (var pid in affectedPlayerIds)
        {
            await PublishPlayerStateChangedAsync(
                playerId: pid,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt);
        }
    }

    public async Task ExecuteHumanTileActionAsync(string action, string correlationId, string? causationId)
    {
        EnsureStarted();

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        var activePlayerId = _playerOrder[_activePlayerIndex];
        if (IsAiPlayerId(activePlayerId))
        {
            return;
        }

        if (!_boardState.TryGetPlayer(activePlayerId, out var activePlayer) || activePlayer is null)
            throw new InvalidOperationException($"Player not found in board state: {activePlayerId}");

        var normalized = (action ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(normalized) || string.Equals(normalized, "skip", StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        // Currently supported: house_build => buy city.
        var shouldBuy = string.Equals(normalized, "house_build", StringComparison.OrdinalIgnoreCase)
            || string.Equals(normalized, "buy", StringComparison.OrdinalIgnoreCase)
            || string.Equals(normalized, "purchase", StringComparison.OrdinalIgnoreCase);

        if (!shouldBuy)
        {
            return;
        }

        var occurredAt = DateTimeOffset.UtcNow;
        var citiesById = _boardState.GetCitiesSnapshot();
        var city = TryGetCityAtPositionIndex(citiesById, activePlayer.PositionIndex);
        if (city is null)
        {
            return;
        }

        if (_boardState.TryGetOwnerOfCity(city.Id, out _))
        {
            // Owned: no purchase action.
            return;
        }

        var players = new List<SanguoPlayer>(_playerOrder.Length);
        foreach (var pid in _playerOrder)
        {
            if (!_boardState.TryGetPlayer(pid, out var p) || p is null)
                throw new InvalidOperationException($"Player not found in board state: {pid}");
            players.Add(p);
        }

        var bought = await _economy.TryBuyCityAndPublishEventAsync(
            gameId: _gameId,
            turnNumber: _turnNumber,
            players: players,
            citiesById: citiesById,
            buyerId: activePlayerId,
            cityId: city.Id,
            priceMultiplier: 1.0m,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);

        if (!bought)
        {
            return;
        }

        await PublishPlayerStateChangedAsync(
            playerId: activePlayerId,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
    }

    private async Task PublishPlayerStateChangedAsync(
        string playerId,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        if (_gameId is null)
            return;

        if (!_boardState.TryGetPlayer(playerId, out var player) || player is null)
            throw new InvalidOperationException($"Player not found in board state: {playerId}");

        var evt = new DomainEvent(
            Type: SanguoPlayerStateChanged.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoPlayerStateChanged(
                GameId: _gameId,
                PlayerId: playerId,
                Money: player.Money.ToDecimal(),
                PositionIndex: player.PositionIndex,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId)),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N"));

        await _bus.PublishAsync(evt);
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
            _gameOverEndReason = SanguoGameEnded.ReasonPlayerBankrupt;

            var occurredAt = DateTimeOffset.UtcNow;
            var evt = new DomainEvent(
                Type: SanguoGameEnded.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoGameEnded(
                    GameId: _gameId,
                    EndReason: SanguoGameEnded.ReasonPlayerBankrupt,
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

        var previousOrder = _playerOrder;
        var previousActiveIndex = Array.FindIndex(previousOrder, x => string.Equals(x, activePlayerId, StringComparison.Ordinal));

        var kept = new List<string>(previousOrder.Length);
        foreach (var playerId in previousOrder)
        {
            if (!_boardState.TryGetPlayer(playerId, out var player) || player is null)
            {
                kept.Add(playerId);
                continue;
            }

            if (player.IsEliminated && IsAiPlayerId(playerId))
            {
                if (player.OwnedCityIds.Count > 0)
                {
                    var snapshot = player.CaptureRollbackSnapshot();
                    player.RestoreRollbackSnapshot(snapshot with { OwnedCityIds = Array.Empty<string>() });
                }
                continue;
            }

            kept.Add(playerId);
        }

        if (kept.Count == previousOrder.Length)
        {
            return;
        }

        _playerOrder = kept.ToArray();
        _activePlayerIndex = Array.FindIndex(_playerOrder, x => string.Equals(x, activePlayerId, StringComparison.Ordinal));

        // If the active player was removed (e.g., eliminated AI), keep rotation stable by selecting the nearest
        // surviving player before the active one. This ensures the subsequent "+1" in AdvanceTurnAsync advances
        // to the correct next player in the original order.
        if (_activePlayerIndex < 0 && _playerOrder.Length > 0 && previousActiveIndex >= 0)
        {
            for (var offset = 1; offset <= previousOrder.Length; offset++)
            {
                var candidateIndex = (previousActiveIndex - offset) % previousOrder.Length;
                if (candidateIndex < 0)
                    candidateIndex += previousOrder.Length;

                var candidateId = previousOrder[candidateIndex];
                var keptIndex = Array.FindIndex(_playerOrder, x => string.Equals(x, candidateId, StringComparison.Ordinal));
                if (keptIndex >= 0)
                {
                    _activePlayerIndex = keptIndex;
                    break;
                }
            }
        }
    }

    private static IReadOnlyList<City> CreateCityList(IReadOnlyDictionary<string, City> citiesById)
    {
        var list = new System.Collections.Generic.List<City>(citiesById.Count);
        foreach (var city in citiesById.Values)
            list.Add(city);
        return list;
    }

    private int ComputeRoundNumber(int turnNumber)
    {
        if (_startingPlayersCount <= 0)
            return 1;

        if (turnNumber < 1)
            return 1;

        return ((turnNumber - 1) / _startingPlayersCount) + 1;
    }

    private static string BuildRngContextId(string stream, int turnNumber, int roundNumber, string sourceId)
        => $"{stream}:{turnNumber}:{roundNumber}:{sourceId}";

    private static string ComputeSha256Hex(string value)
    {
        var bytes = Encoding.UTF8.GetBytes(value);
        var hash = SHA256.HashData(bytes);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private static int ComputeDeterministicSeed(int baseSeed, string rngContextId, string candidatesSortedIdsHash)
    {
        var material = $"{baseSeed}|{rngContextId}|{candidatesSortedIdsHash}";
        var bytes = Encoding.UTF8.GetBytes(material);
        var hash = SHA256.HashData(bytes);
        var seed = BitConverter.ToInt32(hash, 0) & 0x7fffffff;
        if (seed == 0)
        {
            seed = 1;
        }
        return seed;
    }

    private void ResetTurnScopedEventStepDeltas()
    {
        _turnEventStepDeltasByPlayerId.Clear();
        _turnActionCardStepDeltasByPlayerId.Clear();
    }

    internal AppliedMultipliers GetTurnAppliedMultipliersSnapshot(string playerId)
    {
        if (string.IsNullOrWhiteSpace(playerId))
            throw new ArgumentException("PlayerId must be non-empty.", nameof(playerId));

        var baseSteps = AppliedMultipliers.BaseDefaultSteps;
        var eventDelta = _turnEventStepDeltasByPlayerId.TryGetValue(playerId, out var e) ? e : 0;
        var actionCardDelta = _turnActionCardStepDeltasByPlayerId.TryGetValue(playerId, out var a) ? a : 0;
        var effectiveSteps = AppliedMultipliers.ClampSteps(baseSteps + eventDelta + actionCardDelta);

        var sources = AppliedMultiplierSources.None;
        if (eventDelta != 0)
            sources |= AppliedMultiplierSources.Event;
        if (actionCardDelta != 0)
            sources |= AppliedMultiplierSources.ActionCard;

        return new AppliedMultipliers(
            BaseSteps: baseSteps,
            CharacterStepDelta: 0,
            BuildingStepDelta: 0,
            EventStepDelta: eventDelta,
            ActionCardStepDelta: actionCardDelta,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: effectiveSteps,
            Sources: sources);
    }

    private AppliedMultipliers CommitTurnEventEconomyStepDeltaAndGetSnapshot(string playerId, int stepDelta)
    {
        if (string.IsNullOrWhiteSpace(playerId))
            throw new ArgumentException("PlayerId must be non-empty.", nameof(playerId));

        var current = _turnEventStepDeltasByPlayerId.TryGetValue(playerId, out var v) ? v : 0;
        var next = checked(current + stepDelta);
        _turnEventStepDeltasByPlayerId[playerId] = next;

        var baseSteps = AppliedMultipliers.BaseDefaultSteps;
        var actionCardDelta = _turnActionCardStepDeltasByPlayerId.TryGetValue(playerId, out var a) ? a : 0;
        var effectiveSteps = AppliedMultipliers.ClampSteps(baseSteps + next + actionCardDelta);

        return new AppliedMultipliers(
            BaseSteps: baseSteps,
            CharacterStepDelta: 0,
            BuildingStepDelta: 0,
            EventStepDelta: next,
            ActionCardStepDelta: actionCardDelta,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: effectiveSteps,
            Sources: AppliedMultiplierSources.Event);
    }

    private AppliedMultipliers CommitTurnActionCardEconomyStepDeltaAndGetSnapshot(string playerId, int stepDelta)
    {
        if (string.IsNullOrWhiteSpace(playerId))
            throw new ArgumentException("PlayerId must be non-empty.", nameof(playerId));

        var current = _turnActionCardStepDeltasByPlayerId.TryGetValue(playerId, out var v) ? v : 0;
        var next = checked(current + stepDelta);
        _turnActionCardStepDeltasByPlayerId[playerId] = next;

        var baseSteps = AppliedMultipliers.BaseDefaultSteps;
        var eventDelta = _turnEventStepDeltasByPlayerId.TryGetValue(playerId, out var e) ? e : 0;
        var effectiveSteps = AppliedMultipliers.ClampSteps(baseSteps + next + eventDelta);

        return new AppliedMultipliers(
            BaseSteps: baseSteps,
            CharacterStepDelta: 0,
            BuildingStepDelta: 0,
            EventStepDelta: eventDelta,
            ActionCardStepDelta: next,
            RelicStepDelta: 0,
            RegionStepDelta: 0,
            EffectiveSteps: effectiveSteps,
            Sources: AppliedMultiplierSources.ActionCard);
    }

    private async Task TryTriggerTileRandomEventAsync(
        string gameId,
        string activePlayerId,
        int positionIndex,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        if (_randomEventsCatalog is null)
            return;

        if (!IsEventTilePosition(positionIndex))
            return;

        var roundNumber = ComputeRoundNumber(_turnNumber);
        var rngContextId = BuildRngContextId(
            stream: "rng.random_events",
            turnNumber: _turnNumber,
            roundNumber: roundNumber,
            sourceId: "tile");

        if (!TryPickRandomEvent(
                poolId: _tileRandomEventPoolId,
                playerId: activePlayerId,
                roundNumber: roundNumber,
                rngContextId: rngContextId,
                out var picked,
                out var candidatesSortedIdsHash,
                out var pickedIndex,
                out var pickedId,
                out var pickRejectReason))
            return;

        if (!string.IsNullOrWhiteSpace(pickRejectReason))
        {
            var rejectedEvt = new DomainEvent(
                Type: SanguoRandomEventRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventRejected(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: picked.EventId,
                    EffectKind: picked.EffectKind,
                    RejectReason: pickRejectReason,
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejectedEvt);
            return;
        }

        var effectResult = ApplyRandomEventEffect(
            playerId: activePlayerId,
            effectKind: picked.EffectKind,
            moneyDelta: picked.MoneyDelta,
            stepDelta: picked.StepDelta);

        if (effectResult.Applied)
        {
            RecordRandomEventApplied(activePlayerId, picked.EventId, roundNumber);
            var evt = new DomainEvent(
                Type: SanguoRandomEventApplied.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventApplied(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: picked.EventId,
                    EffectKind: picked.EffectKind,
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId,
                    AppliedMultipliersAfter: effectResult.AppliedMultipliersAfter
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(evt);
        }
        else
        {
            var evt = new DomainEvent(
                Type: SanguoRandomEventRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventRejected(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: picked.EventId,
                    EffectKind: picked.EffectKind,
                    RejectReason: effectResult.RejectReason,
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(evt);
        }

        if (effectResult.MoneyChanged)
        {
            await PublishPlayerStateChangedAsync(
                playerId: activePlayerId,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt);
        }
    }

    private async Task TryTriggerGlobalRoundRandomEventBeforeTurnStartedAsync(
        string gameId,
        string activePlayerId,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        if (_randomEventsCatalog is null)
            return;

        if (_startingPlayersCount is < 4 or > 8)
            return;

        var roundNumber = ComputeRoundNumber(_turnNumber);
        if (!_globalRoundGate.TryMarkChecked(roundNumber))
            return;

        var rngContextId = BuildRngContextId(
            stream: "rng.global_round_events",
            turnNumber: _turnNumber,
            roundNumber: roundNumber,
            sourceId: "global_round");

        if (!TryPickRandomEvent(
                poolId: _globalRandomEventPoolId,
                playerId: activePlayerId,
                roundNumber: roundNumber,
                rngContextId: rngContextId,
                out var picked,
                out var candidatesSortedIdsHash,
                out var pickedIndex,
                out var pickedId,
                out var pickRejectReason))
            return;

        var publishedEventId = SanguoGlobalEventId.WithGlobalPrefix(picked.EventId);

        if (!string.IsNullOrWhiteSpace(pickRejectReason))
        {
            var rejectedEvt = new DomainEvent(
                Type: SanguoRandomEventRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventRejected(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: publishedEventId,
                    EffectKind: picked.EffectKind,
                    RejectReason: pickRejectReason,
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejectedEvt);
            return;
        }

        var effectResult = ApplyRandomEventEffect(
            playerId: activePlayerId,
            effectKind: picked.EffectKind,
            moneyDelta: picked.MoneyDelta,
            stepDelta: picked.StepDelta);

        if (effectResult.Applied)
        {
            RecordRandomEventApplied(activePlayerId, picked.EventId, roundNumber);
            var evt = new DomainEvent(
                Type: SanguoRandomEventApplied.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventApplied(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: publishedEventId,
                    EffectKind: picked.EffectKind,
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId,
                    AppliedMultipliersAfter: effectResult.AppliedMultipliersAfter
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(evt);
        }
        else
        {
            var evt = new DomainEvent(
                Type: SanguoRandomEventRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventRejected(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: publishedEventId,
                    EffectKind: picked.EffectKind,
                    RejectReason: effectResult.RejectReason,
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(evt);
        }
    }

    private async Task TryTriggerGlobalTurnRandomEventIfBoundaryAsync(
        string gameId,
        string activePlayerId,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        if (_randomEventsCatalog is null)
            return;

        if (_globalEventIntervalTurns <= 0)
            return;

        if (_turnNumber % _globalEventIntervalTurns != 0)
            return;

        var roundNumber = ComputeRoundNumber(_turnNumber);
        var rngContextId = BuildRngContextId(
            stream: "rng.random_events",
            turnNumber: _turnNumber,
            roundNumber: roundNumber,
            sourceId: "global");

        if (!TryPickRandomEvent(
                poolId: _globalRandomEventPoolId,
                playerId: activePlayerId,
                roundNumber: roundNumber,
                rngContextId: rngContextId,
                out var picked,
                out var candidatesSortedIdsHash,
                out var pickedIndex,
                out var pickedId,
                out var pickRejectReason))
            return;

        var publishedEventId = SanguoGlobalEventId.WithGlobalPrefix(picked.EventId);

        if (!string.IsNullOrWhiteSpace(pickRejectReason))
        {
            var rejectedEvt = new DomainEvent(
                Type: SanguoRandomEventRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventRejected(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: publishedEventId,
                    EffectKind: picked.EffectKind,
                    RejectReason: pickRejectReason,
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejectedEvt);
            return;
        }

        var effectResult = ApplyRandomEventEffect(
            playerId: activePlayerId,
            effectKind: picked.EffectKind,
            moneyDelta: picked.MoneyDelta,
            stepDelta: picked.StepDelta);

        if (effectResult.Applied)
        {
            RecordRandomEventApplied(activePlayerId, picked.EventId, roundNumber);
            var evt = new DomainEvent(
                Type: SanguoRandomEventApplied.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventApplied(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: publishedEventId,
                    EffectKind: picked.EffectKind,
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId,
                    AppliedMultipliersAfter: effectResult.AppliedMultipliersAfter
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(evt);
        }
        else
        {
            var evt = new DomainEvent(
                Type: SanguoRandomEventRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventRejected(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: publishedEventId,
                    EffectKind: picked.EffectKind,
                    RejectReason: effectResult.RejectReason,
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(evt);
        }

        if (effectResult.MoneyChanged)
        {
            await PublishPlayerStateChangedAsync(
                playerId: activePlayerId,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt);
        }
    }

    private bool IsEventTilePosition(int positionIndex)
    {
        if (_tileTypesByPositionIndex is null)
            return true;

        if (!_tileTypesByPositionIndex.TryGetValue(positionIndex, out var tileType))
            return false;

        return string.Equals(tileType, SanguoTileDefinition.TileTypeEvent, StringComparison.OrdinalIgnoreCase);
    }

    private readonly record struct RandomEventEffectResult(
        bool Applied,
        bool MoneyChanged,
        AppliedMultipliers? AppliedMultipliersAfter,
        string RejectReason
    );

    private RandomEventEffectResult ApplyRandomEventEffect(
        string playerId,
        string effectKind,
        int? moneyDelta,
        int? stepDelta)
    {
        if (string.Equals(effectKind, "economyStepDelta", StringComparison.Ordinal))
        {
            if (!stepDelta.HasValue)
            {
                return new RandomEventEffectResult(
                    Applied: false,
                    MoneyChanged: false,
                    AppliedMultipliersAfter: null,
                    RejectReason: "missing_step_delta");
            }

            var applied = CommitTurnEventEconomyStepDeltaAndGetSnapshot(playerId, stepDelta.Value);
            return new RandomEventEffectResult(
                Applied: true,
                MoneyChanged: false,
                AppliedMultipliersAfter: applied,
                RejectReason: string.Empty);
        }

        if (string.Equals(effectKind, "moneyDelta", StringComparison.Ordinal))
        {
            if (!moneyDelta.HasValue)
            {
                return new RandomEventEffectResult(
                    Applied: false,
                    MoneyChanged: false,
                    AppliedMultipliersAfter: null,
                    RejectReason: "missing_money_delta");
            }

            if (!_boardState.TryGetPlayer(playerId, out var player) || player is null)
            {
                return new RandomEventEffectResult(
                    Applied: false,
                    MoneyChanged: false,
                    AppliedMultipliersAfter: null,
                    RejectReason: "player_not_found");
            }

            var snapshot = player.CaptureRollbackSnapshot();
            var currentMoney = snapshot.Money;
            var delta = moneyDelta.Value;

            if (delta == 0)
            {
                return new RandomEventEffectResult(
                    Applied: true,
                    MoneyChanged: false,
                    AppliedMultipliersAfter: null,
                    RejectReason: string.Empty);
            }

            if (delta > 0)
            {
                var add = Money.FromMajorUnits((long)delta);
                var newMoney = currentMoney.AddCapped(add, out var overflow);
                if (overflow > Money.Zero)
                {
                    _treasury.Deposit(overflow);
                }

                player.RestoreRollbackSnapshot(snapshot with { Money = newMoney });
                return new RandomEventEffectResult(
                    Applied: true,
                    MoneyChanged: true,
                    AppliedMultipliersAfter: null,
                    RejectReason: string.Empty);
            }

            var debit = Money.FromMajorUnits((long)-delta);
            if (currentMoney >= debit)
            {
                var newMoney = currentMoney - debit;
                player.RestoreRollbackSnapshot(snapshot with { Money = newMoney });
                return new RandomEventEffectResult(
                    Applied: true,
                    MoneyChanged: true,
                    AppliedMultipliersAfter: null,
                    RejectReason: string.Empty);
            }

            player.RestoreRollbackSnapshot(snapshot with
            {
                Money = Money.Zero,
                IsEliminated = true,
                OwnedCityIds = Array.Empty<string>()
            });

            return new RandomEventEffectResult(
                Applied: true,
                MoneyChanged: true,
                AppliedMultipliersAfter: null,
                RejectReason: string.Empty);
        }

        // Reject: non-allowlist effect kind must not produce any numerical changes.
        return new RandomEventEffectResult(
            Applied: false,
            MoneyChanged: false,
            AppliedMultipliersAfter: null,
            RejectReason: "invalid_effect_kind");
    }

    private void RecordRandomEventApplied(string playerId, string eventId, int roundNumber)
    {
        if (string.IsNullOrWhiteSpace(playerId) || string.IsNullOrWhiteSpace(eventId))
            return;

        if (!_randomEventLastAppliedRoundByPlayerId.TryGetValue(playerId, out var byEventId))
        {
            byEventId = new Dictionary<string, int>(StringComparer.Ordinal);
            _randomEventLastAppliedRoundByPlayerId[playerId] = byEventId;
        }

        byEventId[eventId] = roundNumber;
    }

    private bool IsRandomEventEligibleForPlayer(string playerId, SanguoRandomEventCatalogEntry entry, int currentRoundNumber)
    {
        if (string.IsNullOrWhiteSpace(playerId))
            return true;

        if (!_randomEventLastAppliedRoundByPlayerId.TryGetValue(playerId, out var byEventId))
            return true;

        if (!byEventId.TryGetValue(entry.EventId, out var lastAppliedRound))
            return true;

        if (entry.UniqueOnce)
            return false;

        if (entry.CooldownRounds <= 0)
            return true;

        return (currentRoundNumber - lastAppliedRound) > entry.CooldownRounds;
    }

    private bool TryPickRandomEvent(
        string poolId,
        string playerId,
        int roundNumber,
        string rngContextId,
        out SanguoRandomEventCatalogEntry picked,
        out string candidatesSortedIdsHash,
        out int pickedIndex,
        out string pickedId,
        out string? rejectReason)
    {
        picked = default!;
        candidatesSortedIdsHash = string.Empty;
        pickedIndex = -1;
        pickedId = string.Empty;
        rejectReason = null;

        if (_randomEventsCatalog is null)
            return false;

        if (string.IsNullOrWhiteSpace(poolId))
            return false;

        var pool = _randomEventsCatalog.EventPools
            .FirstOrDefault(p => string.Equals(p.PoolId, poolId, StringComparison.Ordinal));

        if (pool is null)
            return false;

        var eventsById = new Dictionary<string, SanguoRandomEventCatalogEntry>(StringComparer.Ordinal);
        foreach (var e in _randomEventsCatalog.Events)
        {
            if (!string.IsNullOrWhiteSpace(e.EventId))
                eventsById[e.EventId] = e;
        }

        var allCandidates = new List<SanguoRandomEventCatalogEntry>();
        var eligibleCandidates = new List<SanguoRandomEventCatalogEntry>();
        foreach (var eventId in pool.EventIds
                     .Where(x => !string.IsNullOrWhiteSpace(x))
                     .Distinct(StringComparer.Ordinal)
                     .OrderBy(x => x, StringComparer.Ordinal))
        {
            if (!eventsById.TryGetValue(eventId, out var e))
                continue;

            allCandidates.Add(e);
            if (IsRandomEventEligibleForPlayer(playerId, e, roundNumber))
            {
                eligibleCandidates.Add(e);
            }
        }

        if (allCandidates.Count == 0)
            return false;

        var list = eligibleCandidates.Count > 0 ? eligibleCandidates : allCandidates;
        var candidateIds = list.Select(x => x.EventId).ToArray();
        candidatesSortedIdsHash = ComputeSha256Hex(string.Join("\n", candidateIds));

        if (eligibleCandidates.Count == 0)
        {
            rejectReason = "no_eligible_candidates";
        }

        var seed = ComputeDeterministicSeed(_randomSeed, rngContextId, candidatesSortedIdsHash);
        var picker = new DeterministicRandomNumberGenerator(seed);
        pickedIndex = picker.NextInt(minInclusive: 0, maxExclusive: list.Count);
        picked = list[pickedIndex];
        pickedId = picked.EventId;
        return true;
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

        // Best-effort fallback: derive from known city position indices only.
        // Player positions alone are not sufficient to infer a stable board size.
        var maxIndex = -1;
        foreach (var city in _boardState.GetCitiesSnapshot().Values)
            maxIndex = Math.Max(maxIndex, city.PositionIndex);

        if (maxIndex < 0)
            return 0;

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
            DecisionNode: aiDecision.DecisionNode,
            FromState: aiDecision.FromState,
            ToState: aiDecision.ToState,
            Reason: aiDecision.Reason,
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

        _diceRolledTurnNumber = _turnNumber;
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
                    turnNumber: _turnNumber,
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
            turnNumber: _turnNumber,
            players: players,
            citiesById: citiesById,
            buyerId: aiPlayerId,
            cityId: city.Id,
            priceMultiplier: 1.0m,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
    }

    public SanguoSaveSnapshot ExportSaveSnapshot()
    {
        EnsureStarted();

        var playersById = _boardState.Players;
        var players = new List<SanguoSavePlayer>(_playerOrder.Length);
        foreach (var pid in _playerOrder)
        {
            if (!playersById.TryGetValue(pid, out var p))
                throw new InvalidOperationException($"Player not found in board state: {pid}");

            var owned = p.OwnedCityIds is null ? Array.Empty<string>() : p.OwnedCityIds.ToArray();
            players.Add(new SanguoSavePlayer(
                PlayerId: p.PlayerId,
                Money: p.Money.ToDecimal(),
                PositionIndex: p.PositionIndex,
                IsEliminated: p.IsEliminated,
                OwnedCityIds: owned
            ));
        }

        var cities = _boardState.CitiesById;
        var cityEconomy = new List<SanguoSaveCityEconomy>(cities.Count);
        foreach (var city in cities.Values.OrderBy(c => c.Id, StringComparer.Ordinal))
        {
            cityEconomy.Add(new SanguoSaveCityEconomy(
                CityId: city.Id,
                BasePrice: city.BasePrice.ToDecimal(),
                BaseToll: city.BaseToll.ToDecimal()
            ));
        }

        return new SanguoSaveSnapshot(
            GameId: _gameId,
            TurnNumber: _turnNumber,
            ActivePlayerIndex: _activePlayerIndex,
            Year: _currentDate.Year,
            Month: _currentDate.Month,
            Day: _currentDate.Day,
            PlayerOrder: _playerOrder.ToArray(),
            Players: players,
            CityEconomy: cityEconomy,
            TreasuryMinorUnits: _treasury.MinorUnits
        );
    }

    public void RestoreFromSaveSnapshot(SanguoSaveSnapshot snapshot)
    {
        ArgumentNullException.ThrowIfNull(snapshot, nameof(snapshot));

        if (string.IsNullOrWhiteSpace(snapshot.GameId))
            throw new ArgumentException("Snapshot GameId must be non-empty.", nameof(snapshot));

        if (snapshot.TurnNumber < 1)
            throw new ArgumentOutOfRangeException(nameof(snapshot), "Snapshot TurnNumber must be >= 1.");

        if (snapshot.PlayerOrder is null || snapshot.PlayerOrder.Count == 0)
            throw new ArgumentException("Snapshot PlayerOrder must be non-empty.", nameof(snapshot));

        if (snapshot.ActivePlayerIndex < 0 || snapshot.ActivePlayerIndex >= snapshot.PlayerOrder.Count)
            throw new ArgumentOutOfRangeException(nameof(snapshot), "Snapshot ActivePlayerIndex is out of range.");

        if (snapshot.Players is null || snapshot.Players.Count == 0)
            throw new ArgumentException("Snapshot Players must be non-empty.", nameof(snapshot));

        if (snapshot.TreasuryMinorUnits < 0)
            throw new ArgumentOutOfRangeException(nameof(snapshot), "Snapshot TreasuryMinorUnits must be non-negative.");

        var order = snapshot.PlayerOrder.Select(p => (p ?? string.Empty).Trim()).Where(p => p.Length != 0).ToArray();
        if (order.Length != snapshot.PlayerOrder.Count)
            throw new ArgumentException("Snapshot PlayerOrder must not contain empty player ids.", nameof(snapshot));

        if (order.Distinct(StringComparer.Ordinal).Count() != order.Length)
            throw new ArgumentException("Snapshot PlayerOrder must not contain duplicate player ids.", nameof(snapshot));

        var playersById = new Dictionary<string, SanguoSavePlayer>(StringComparer.Ordinal);
        foreach (var p in snapshot.Players)
        {
            ArgumentNullException.ThrowIfNull(p, nameof(snapshot));
            var pid = (p.PlayerId ?? string.Empty).Trim();
            if (pid.Length == 0)
                throw new ArgumentException("Snapshot Players must not contain empty PlayerId.", nameof(snapshot));
            if (!playersById.TryAdd(pid, p))
                throw new ArgumentException($"Duplicate Snapshot PlayerId: {pid}", nameof(snapshot));
        }

        foreach (var pid in order)
        {
            if (!playersById.ContainsKey(pid))
                throw new ArgumentException($"Snapshot is missing player entry for PlayerOrder id: {pid}", nameof(snapshot));
        }

        var citiesById = _boardState.GetCitiesSnapshot();
        var claimedCityIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var p in playersById.Values)
        {
            var owned = p.OwnedCityIds ?? Array.Empty<string>();
            foreach (var cidRaw in owned)
            {
                var cid = (cidRaw ?? string.Empty).Trim();
                if (cid.Length == 0)
                    continue;
                if (!citiesById.ContainsKey(cid))
                    throw new ArgumentException($"Snapshot references unknown CityId: {cid}", nameof(snapshot));
                if (!claimedCityIds.Add(cid))
                    throw new ArgumentException($"Snapshot has duplicate city ownership claim: {cid}", nameof(snapshot));
            }
        }

        if (snapshot.CityEconomy is not null && snapshot.CityEconomy.Count > 0)
        {
            var econById = new Dictionary<string, SanguoSaveCityEconomy>(StringComparer.Ordinal);
            foreach (var e in snapshot.CityEconomy)
            {
                ArgumentNullException.ThrowIfNull(e, nameof(snapshot));
                var cid = (e.CityId ?? string.Empty).Trim();
                if (cid.Length == 0)
                    continue;
                if (!citiesById.ContainsKey(cid))
                    throw new ArgumentException($"Snapshot CityEconomy references unknown CityId: {cid}", nameof(snapshot));
                econById[cid] = e;
            }

            var updated = new List<City>(citiesById.Count);
            foreach (var city in citiesById.Values.OrderBy(c => c.Id, StringComparer.Ordinal))
            {
                if (!econById.TryGetValue(city.Id, out var econ))
                {
                    updated.Add(city);
                    continue;
                }

                updated.Add(new City(
                    id: city.Id,
                    name: city.Name,
                    regionId: city.RegionId,
                    basePrice: Money.FromDecimal(econ.BasePrice),
                    baseToll: Money.FromDecimal(econ.BaseToll),
                    positionIndex: city.PositionIndex));
            }

            _boardState.ApplyCityEconomyUpdates(updated);
        }

        foreach (var pid in order)
        {
            if (!_boardState.TryGetPlayer(pid, out var player) || player is null)
                throw new InvalidOperationException($"Player not found in board state: {pid}");

            var p = playersById[pid];
            var owned = (p.OwnedCityIds ?? Array.Empty<string>()).Where(x => !string.IsNullOrWhiteSpace(x)).Select(x => x.Trim()).ToArray();

            player.RestoreRollbackSnapshot(new SanguoPlayer.RollbackSnapshot(
                Money: Money.FromDecimal(p.Money),
                PositionIndex: p.PositionIndex < 0 ? 0 : p.PositionIndex,
                IsEliminated: p.IsEliminated,
                OwnedCityIds: owned
            ));
        }

        _treasury.RestoreRollbackSnapshot(snapshot.TreasuryMinorUnits);

        _gameId = snapshot.GameId;
        _playerOrder = order;
        _startingPlayersCount = order.Length;
        _activePlayerIndex = snapshot.ActivePlayerIndex;
        _turnNumber = snapshot.TurnNumber;
        _currentDate = new SanguoCalendarDate(snapshot.Year, snapshot.Month, snapshot.Day);
        _started = true;
        _actionCardPlayedTurnNumber = null;
        _diceRolledTurnNumber = null;
        ResetTurnScopedEventStepDeltas();
        _globalRoundGate = new SanguoGlobalEventRoundGate();
    }

    public async Task PublishStateSnapshotAsync(string correlationId, string? causationId)
    {
        EnsureStarted();

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        var occurredAt = DateTimeOffset.UtcNow;
        var activePlayerId = _playerOrder[_activePlayerIndex];

        await TryTriggerGlobalRoundRandomEventBeforeTurnStartedAsync(
            gameId: _gameId,
            activePlayerId: activePlayerId,
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);

        await _bus.PublishAsync(new DomainEvent(
            Type: SanguoGameTurnStarted.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoGameTurnStarted(
                GameId: _gameId,
                TurnNumber: _turnNumber,
                ActivePlayerId: activePlayerId,
                Year: _currentDate.Year,
                Month: _currentDate.Month,
                Day: _currentDate.Day,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N")
        ));

        var playersById = _boardState.Players;
        if (playersById.TryGetValue(activePlayerId, out var active))
        {
            await PublishPlayerStateChangedAsync(
                playerId: active.PlayerId,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt);
        }

        foreach (var pid in _playerOrder)
        {
            if (StringComparer.Ordinal.Equals(pid, activePlayerId))
                continue;

            await PublishPlayerStateChangedAsync(
                playerId: pid,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt);
        }

        foreach (var pid in _playerOrder)
        {
            if (!_boardState.TryGetPlayer(pid, out var player) || player is null)
                continue;

            var idx = player.PositionIndex;
            if (idx < 0)
                idx = 0;

            await _bus.PublishAsync(new DomainEvent(
                Type: SanguoTokenMoved.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoTokenMoved(
                    GameId: _gameId,
                    PlayerId: pid,
                    FromIndex: idx,
                    ToIndex: idx,
                    Steps: 1,
                    PassedStart: false,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N")
            ));

            foreach (var cityId in player.OwnedCityIds)
            {
                if (string.IsNullOrWhiteSpace(cityId))
                    continue;

                if (!_boardState.CitiesById.TryGetValue(cityId, out var city))
                    continue;

                await _bus.PublishAsync(new DomainEvent(
                    Type: SanguoCityBought.EventType,
                    Source: nameof(SanguoTurnManager),
                    Data: JsonElementEventData.FromObject(new SanguoCityBought(
                        GameId: _gameId,
                        TurnNumber: _turnNumber,
                        BuyerId: pid,
                        CityId: cityId,
                        Price: city.BasePrice.ToDecimal(),
                        OccurredAt: occurredAt,
                        CorrelationId: correlationId,
                        CausationId: causationId,
                        AppliedMultipliers: new AppliedMultipliers(
                            BaseSteps: AppliedMultipliers.BaseDefaultSteps,
                            CharacterStepDelta: 0,
                            BuildingStepDelta: 0,
                            EventStepDelta: 0,
                            ActionCardStepDelta: 0,
                            RelicStepDelta: 0,
                            RegionStepDelta: 0,
                            EffectiveSteps: AppliedMultipliers.BaseDefaultSteps)
                    )),
                    Timestamp: occurredAt.UtcDateTime,
                    Id: Guid.NewGuid().ToString("N")
                ));
            }
        }
    }
}
