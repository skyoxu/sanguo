using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using Game.Core.Domain.ValueObjects;
using Game.Core.Utilities;
using System.Diagnostics.CodeAnalysis;
using System.Linq;
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
    private readonly ISanguoRegionSynergyTollBypassPolicy _regionSynergyTollBypassPolicy;
    private readonly int _totalPositionsHint;
    private readonly double _quarterEnvironmentEventTriggerChance;
    private readonly decimal _quarterEnvironmentEventYieldMultiplier;
    private readonly SanguoRandomEventsCatalog? _randomEventsCatalog;
    private readonly int _globalEventIntervalTurns;
    private readonly string _tileRandomEventPoolId;
    private readonly string _globalRandomEventPoolId;
    private readonly IReadOnlyDictionary<int, string>? _tileTypesByPositionIndex;
    private readonly IReadOnlyDictionary<string, int> _combatRatingByPlayerId;
    private readonly Dictionary<string, int> _turnEventStepDeltasByPlayerId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, int> _turnActionCardStepDeltasByPlayerId = new(StringComparer.Ordinal);
    private readonly SanguoActionCardsCatalog? _actionCardsCatalog;
    private readonly Dictionary<string, Dictionary<string, int>> _actionCardsByPlayerId = new(StringComparer.Ordinal);
    private readonly SanguoBuildingsCatalog? _buildingsCatalog;
    private readonly SanguoRelicsCatalog? _relicsCatalog;
    private readonly IReadOnlyDictionary<string, SanguoBuildingDefinition> _buildingsById;
    private readonly Dictionary<string, Dictionary<string, int>> _buildingLevelsByCityId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, Dictionary<string, int>> _randomEventLastAppliedRoundByPlayerId = new(StringComparer.Ordinal);
    private SanguoGlobalEventRoundGate _globalRoundGate = new();
    private readonly Dictionary<string, int> _relicStepDeltaByPlayerId = new(StringComparer.Ordinal);
    private readonly Dictionary<string, HashSet<string>> _relicIdsByPlayerId = new(StringComparer.Ordinal);
    private readonly HashSet<string> _grantedRelicIds = new(StringComparer.Ordinal);
    private readonly Dictionary<string, string> _capturedRegionOwnerByRegionId = new(StringComparer.Ordinal);

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
    private readonly string _contentPackId;
    private readonly int _contentPackVersion;
    private const int InitialActionCardCopiesPerType = 2;
    private const int MaxActionCardsPerPlayer = 15;

    public SanguoTurnManager(
        IEventBus bus,
        SanguoEconomyManager economy,
        SanguoBoardState boardState,
        SanguoTreasury treasury,
        ISanguoAiDecisionPolicy? aiDecisionPolicy = null,
        ISanguoRegionSynergyTollBypassPolicy? regionSynergyTollBypassPolicy = null,
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
        SanguoBuildingsCatalog? buildingsCatalog = null,
        SanguoRelicsCatalog? relicsCatalog = null,
        IReadOnlyDictionary<int, string>? tileTypesByPositionIndex = null,
        IReadOnlyDictionary<string, int>? combatRatingByPlayerId = null,
        string? contentPackId = null,
        int contentPackVersion = 0)
    {
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
        _economy = economy ?? throw new ArgumentNullException(nameof(economy));
        _boardState = boardState ?? throw new ArgumentNullException(nameof(boardState));
        _treasury = treasury ?? throw new ArgumentNullException(nameof(treasury));
        _aiDecisionPolicy = aiDecisionPolicy ?? new DefaultSanguoAiDecisionPolicy();
        _regionSynergyTollBypassPolicy = regionSynergyTollBypassPolicy ?? new DefaultSanguoRegionSynergyTollBypassPolicy();
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
        _buildingsCatalog = buildingsCatalog;
        _relicsCatalog = relicsCatalog;
        _buildingsById = CreateBuildingsById(buildingsCatalog);
        _tileTypesByPositionIndex = tileTypesByPositionIndex;
        _combatRatingByPlayerId = combatRatingByPlayerId ?? new Dictionary<string, int>(StringComparer.Ordinal);
        _contentPackId = string.IsNullOrWhiteSpace(contentPackId) ? string.Empty : contentPackId.Trim();
        _contentPackVersion = contentPackVersion < 0 ? 0 : contentPackVersion;

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
        _buildingLevelsByCityId.Clear();
        _started = true;
        _gameOverEndReason = null;
        _actionCardPlayedTurnNumber = null;
        _diceRolledTurnNumber = null;
        _randomEventLastAppliedRoundByPlayerId.Clear();
        ResetTurnScopedEventStepDeltas();
        _relicStepDeltaByPlayerId.Clear();
        _relicIdsByPlayerId.Clear();
        _grantedRelicIds.Clear();
        _globalRoundGate = new SanguoGlobalEventRoundGate();
        ResetRegionCaptureState();
        ResetActionCardInventory(_playerOrder);

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

        if (!HasActionCard(activePlayerId, cardId))
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
                    ReasonCode: SanguoActionCardPlayRejected.ReasonNotOwned,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejected);
            return false;
        }

        if (string.Equals(card.EffectKind, SanguoEffectKinds.EconomyStepDelta, StringComparison.Ordinal))
        {
            var appliedAfter = CommitTurnActionCardEconomyStepDeltaAndGetSnapshot(activePlayerId, card.StepDelta);

            var played = new DomainEvent(
                Type: SanguoActionCardPlayed.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoActionCardPlayed(
                    GameId: _gameId,
                    PlayerId: activePlayerId,
                    CardId: cardId,
                    EffectKind: SanguoEffectKinds.EconomyStepDelta,
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

            var cardLost = new DomainEvent(
                Type: SanguoCardLost.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoCardLost(
                    GameId: _gameId,
                    PlayerId: activePlayerId,
                    CardId: cardId,
                    ReasonCode: SanguoCardLost.ReasonConsumed,
                    SourceKind: "action_card",
                    SourceId: cardId,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(cardLost);

            ConsumeActionCard(activePlayerId, cardId);
            _actionCardPlayedTurnNumber = _turnNumber;
            return true;
        }

        if (string.Equals(card.EffectKind, SanguoEffectKinds.TransferOwnership, StringComparison.Ordinal))
        {
            if (!_boardState.TryGetPlayer(activePlayerId, out var activePlayer) || activePlayer is null)
                throw new InvalidOperationException($"Player not found in board state: {activePlayerId}");

            var citiesById = _boardState.GetCitiesSnapshot();
            var city = TryGetCityAtPositionIndex(citiesById, activePlayer.PositionIndex);

            if (city is null
                || !_boardState.TryGetOwnerOfCity(city.Id, out var owner)
                || owner is null
                || string.Equals(owner.PlayerId, activePlayerId, StringComparison.Ordinal))
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
                        ReasonCode: SanguoActionCardPlayRejected.ReasonInvalidTarget,
                        OccurredAt: occurredAt,
                        CorrelationId: correlationId,
                        CausationId: causationId
                    )),
                    Timestamp: occurredAt.UtcDateTime,
                    Id: Guid.NewGuid().ToString("N"));
                await _bus.PublishAsync(rejected);
                return false;
            }

            var transferred = await TransferCityOwnershipAsync(
                cityId: city.Id,
                newOwnerId: activePlayerId,
                reasonCode: SanguoCityOwnerChanged.ReasonStolen,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt);

            if (!transferred)
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
                        ReasonCode: SanguoActionCardPlayRejected.ReasonInvalidTarget,
                        OccurredAt: occurredAt,
                        CorrelationId: correlationId,
                        CausationId: causationId
                    )),
                    Timestamp: occurredAt.UtcDateTime,
                    Id: Guid.NewGuid().ToString("N"));
                await _bus.PublishAsync(rejected);
                return false;
            }

            var played = new DomainEvent(
                Type: SanguoActionCardPlayed.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoActionCardPlayed(
                    GameId: _gameId,
                    PlayerId: activePlayerId,
                    CardId: cardId,
                    EffectKind: SanguoEffectKinds.TransferOwnership,
                    StepDelta: card.StepDelta,
                    DurationRounds: card.DurationRounds,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    AppliedMultipliersAfter: null
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(played);

            var cardLost = new DomainEvent(
                Type: SanguoCardLost.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoCardLost(
                    GameId: _gameId,
                    PlayerId: activePlayerId,
                    CardId: cardId,
                    ReasonCode: SanguoCardLost.ReasonConsumed,
                    SourceKind: "action_card",
                    SourceId: cardId,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(cardLost);

            ConsumeActionCard(activePlayerId, cardId);
            _actionCardPlayedTurnNumber = _turnNumber;
            return true;
        }

        var rejectedUnknown = new DomainEvent(
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
        await _bus.PublishAsync(rejectedUnknown);
        return false;
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

        await PruneEliminatedAiPlayersAsync(
            activePlayerId: activePlayerId,
            occurredAt: occurredAt,
            correlationId: correlationId,
            causationId: causationId);
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
                    settlements = _economy.SettleMonth(
                        boardState: _boardState,
                        playerOrder: _playerOrder,
                        treasury: _treasury,
                        buildingIncomeSettlementStepDeltaProvider: ComputeCityBuildingIncomeSettlementStepDelta);
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
                    var ownerRelicStepDelta = GetPersistentRelicStepDelta(owner.PlayerId);
                    var appliedByCityId = new Dictionary<string, AppliedMultipliers>(StringComparer.Ordinal);

                    decimal ComputeCityFinalToll(string cityId)
                    {
                        if (!citiesById.TryGetValue(cityId, out var ownedCity))
                            throw new InvalidOperationException($"City not found while computing region synergy toll (cityId={cityId}).");

                        var buildingTollStepDelta = ComputeCityBuildingTollStepDelta(cityId);
                        var tollSources = AppliedMultiplierSources.None;
                        if (buildingTollStepDelta != 0)
                            tollSources |= AppliedMultiplierSources.Building;
                        if (ownerRelicStepDelta != 0)
                            tollSources |= AppliedMultiplierSources.Relic;

                        var applied = CreateAppliedMultipliers(
                            characterStepDelta: 0,
                            buildingStepDelta: buildingTollStepDelta,
                            eventStepDelta: 0,
                            actionCardStepDelta: 0,
                            relicStepDelta: ownerRelicStepDelta,
                            regionStepDelta: 0,
                            sources: tollSources);

                        appliedByCityId[cityId] = applied;
                        return Money.FromDecimal(ownedCity.BaseToll.ToDecimal() * applied.EffectiveMultiplier).ToDecimal();
                    }

                    var synergy = SanguoRegionSynergyTollCalculator.Compute(
                        payerId: playerId,
                        ownerId: owner.PlayerId,
                        landingCityId: city.Id,
                        citiesById: citiesById,
                        ownerOwnedCityIds: owner.OwnedCityIds,
                        computeCityFinalToll: ComputeCityFinalToll,
                        bypassPolicy: _regionSynergyTollBypassPolicy);

                    var anyPaid = false;
                    var paidBreakdown = new List<SanguoCityTollSynergyPaidBreakdownItem>(capacity: synergy.Breakdown.Count);
                    decimal paidTotal = 0m;
                    foreach (var item in synergy.Breakdown)
                    {
                        if (!appliedByCityId.TryGetValue(item.CityId, out var applied))
                            throw new InvalidOperationException($"Missing applied multipliers for synergy toll city (cityId={item.CityId}).");

                        var paid = await _economy.TryPayTollAndPublishEventAsync(
                            gameId: gameId,
                            turnNumber: _turnNumber,
                            players: players,
                            citiesById: citiesById,
                            payerId: playerId,
                            cityId: item.CityId,
                            tollMultiplier: applied.EffectiveMultiplier,
                            treasury: _treasury,
                            correlationId: correlationId,
                            causationId: causationId,
                            occurredAt: occurredAt,
                            appliedMultipliersOverride: applied,
                            ignorePayerPositionCheck: true);

                        if (!paid)
                            break;
                        anyPaid = true;
                        paidTotal += item.Amount;
                        paidBreakdown.Add(new SanguoCityTollSynergyPaidBreakdownItem(
                            CityId: item.CityId,
                            Amount: item.Amount,
                            AppliedMultipliers: applied));
                    }

                    if (anyPaid && synergy.Breakdown.Count > 1)
                    {
                        var synergyPaid = new DomainEvent(
                            Type: SanguoCityTollSynergyPaid.EventType,
                            Source: nameof(SanguoTurnManager),
                            Data: JsonElementEventData.FromObject(new SanguoCityTollSynergyPaid(
                                GameId: gameId,
                                TurnNumber: _turnNumber,
                                PayerId: playerId,
                                OwnerId: owner.PlayerId,
                                LandingCityId: city.Id,
                                RegionId: city.RegionId,
                                ExpectedTotalAmount: synergy.Total,
                                PaidTotalAmount: paidTotal,
                                ExpectedCitiesCount: synergy.Breakdown.Count,
                                PaidCitiesCount: paidBreakdown.Count,
                                Breakdown: paidBreakdown,
                                OccurredAt: occurredAt,
                                CorrelationId: correlationId,
                                CausationId: causationId
                            )),
                            Timestamp: occurredAt.UtcDateTime,
                            Id: Guid.NewGuid().ToString("N"));
                        await _bus.PublishAsync(synergyPaid);
                    }

                    if (anyPaid)
                        affectedPlayerIds.Add(owner.PlayerId);
                }
            }
            else
            {
                if (IsAiPlayerId(playerId))
                {
                    var bought = await _economy.TryBuyCityAndPublishEventAsync(
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

                    if (bought)
                    {
                        await PublishRegionCaptureChangesAsync(
                            triggerCityId: city.Id,
                            occurredAt: occurredAt,
                            correlationId: correlationId,
                            causationId: causationId);
                    }
                }
            }
        }
        else
        {
            if (IsFacilityTilePosition(toIndex))
            {
                await TryResolveFacilityTileAsync(
                    gameId: gameId,
                    playerId: playerId,
                    positionIndex: toIndex,
                    correlationId: correlationId,
                    causationId: causationId,
                    occurredAt: occurredAt);
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

        if (string.Equals(normalized, "start_combat", StringComparison.OrdinalIgnoreCase)
            || string.Equals(normalized, "startCombat", StringComparison.OrdinalIgnoreCase))
        {
            await StartCombatAndReturnToMainLoopAsync(
                activePlayerId: activePlayerId,
                activePlayer: activePlayer,
                correlationId: correlationId,
                causationId: causationId);
            return;
        }

        var shouldBuy = string.Equals(normalized, "house_build", StringComparison.OrdinalIgnoreCase)
            || string.Equals(normalized, "buy", StringComparison.OrdinalIgnoreCase)
            || string.Equals(normalized, "purchase", StringComparison.OrdinalIgnoreCase)
            || string.Equals(normalized, "buy_land", StringComparison.OrdinalIgnoreCase);

        var shouldBuild = string.Equals(normalized, "build", StringComparison.OrdinalIgnoreCase);

        if (!shouldBuy && !shouldBuild)
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

        if (shouldBuild)
        {
            await TryBuildOrUpgradeCityAsync(
                playerId: activePlayerId,
                city: city,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt);
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

        var bought = await ApplyOwnershipChangeAsync(
            () => _economy.TryBuyCityAndPublishEventAsync(
                gameId: _gameId,
                turnNumber: _turnNumber,
                players: players,
                citiesById: citiesById,
                buyerId: activePlayerId,
                cityId: city.Id,
                priceMultiplier: 1.0m,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt),
            triggerCityId: city.Id,
            occurredAt: occurredAt,
            correlationId: correlationId,
            causationId: causationId);

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

    private async Task StartCombatAndReturnToMainLoopAsync(
        string activePlayerId,
        SanguoPlayer activePlayer,
        string correlationId,
        string? causationId)
    {
        var positionIndex = activePlayer.PositionIndex;
        if (_tileTypesByPositionIndex is null)
            return;

        if (!_tileTypesByPositionIndex.TryGetValue(positionIndex, out var type))
            return;

        if (!string.Equals(type, SanguoTileDefinition.TileTypePass, StringComparison.OrdinalIgnoreCase))
            return;

        var occurredAt = DateTimeOffset.UtcNow;
        var roundNumber = ComputeRoundNumber(_turnNumber);
        var rngContextId = BuildRngContextId(
            stream: "rng.combat",
            turnNumber: _turnNumber,
            roundNumber: roundNumber,
            sourceId: $"tile:{positionIndex}");

        var candidatesSortedIdsHash = ComputeSha256Hex("combat:encounter:default");
        var seed = ComputeDeterministicSeed(_randomSeed, rngContextId, candidatesSortedIdsHash);
        var encounterId = $"enc_battlefield_{_turnNumber}_{positionIndex}";
        var encounterTarget = 10 + (seed % 11); // 10..20 deterministic

        await StartPveCombatAsync(
            gameId: _gameId!,
            playerId: activePlayerId,
            player: activePlayer,
            encounterId: encounterId,
            encounterTarget: encounterTarget,
            seed: seed,
            occurredAt: occurredAt,
            correlationId: correlationId,
            causationId: causationId);
    }

    private async Task StartPveCombatAsync(
        string gameId,
        string playerId,
        SanguoPlayer player,
        string encounterId,
        int encounterTarget,
        int seed,
        DateTimeOffset occurredAt,
        string correlationId,
        string? causationId)
    {
        var started = new DomainEvent(
            Type: SanguoCombatStarted.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoCombatStarted(
                GameId: gameId,
                PlayerId: playerId,
                EncounterId: encounterId,
                RandomSeed: seed,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId)),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N"));
        await _bus.PublishAsync(started);

        var combatRating = _combatRatingByPlayerId.TryGetValue(playerId, out var cr) ? cr : 0;
        var result = Game.Core.Services.Sanguo.SanguoCombatResolver.ResolvePveCombat(
            combatRating: combatRating,
            encounterTarget: encounterTarget,
            seed: seed);

        var moneyChanged = ApplyMoneyDeltaToPlayer(player, result.MoneyDelta);
        if (moneyChanged)
        {
            await PublishPlayerStateChangedAsync(
                playerId: playerId,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt);
        }

        var endedEvtId = Guid.NewGuid().ToString("N");
        var ended = new DomainEvent(
            Type: SanguoCombatEnded.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoCombatEnded(
                GameId: gameId,
                PlayerId: playerId,
                EncounterId: encounterId,
                Result: result,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId)),
            Timestamp: occurredAt.UtcDateTime,
            Id: endedEvtId);
        await _bus.PublishAsync(ended);

        var relicMoneyChanged = await TryGrantRelicLootAsync(
            gameId: gameId,
            playerId: playerId,
            sourceKind: "combat",
            sourceId: encounterId,
            correlationId: correlationId,
            causationId: endedEvtId,
            occurredAt: occurredAt);

        if (relicMoneyChanged)
        {
            await PublishPlayerStateChangedAsync(
                playerId: playerId,
                correlationId: correlationId,
                causationId: endedEvtId,
                occurredAt: occurredAt);
        }
    }

    private bool ApplyMoneyDeltaToPlayer(SanguoPlayer player, decimal moneyDelta)
    {
        if (player is null)
            return false;

        // Stop-loss: core only applies positive money deltas in this phase.
        if (moneyDelta <= 0m)
            return false;

        var snapshot = player.CaptureRollbackSnapshot();
        var currentMoney = snapshot.Money;

        var add = Money.FromMajorUnits((long)moneyDelta);
        var newMoney = currentMoney.AddCapped(add, out var overflow);
        if (overflow > Money.Zero)
        {
            _treasury.Deposit(overflow);
        }
        player.RestoreRollbackSnapshot(snapshot with { Money = newMoney });
        return true;
    }

    private async Task TryBuildOrUpgradeCityAsync(
        string playerId,
        City city,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        if (_gameId is null)
        {
            return;
        }

        if (_buildingsCatalog is null || _buildingsCatalog.Buildings is null || _buildingsCatalog.Buildings.Count == 0)
        {
            return;
        }

        if (!_boardState.TryGetOwnerOfCity(city.Id, out var owner) || owner is null)
        {
            return;
        }

        if (!string.Equals(owner.PlayerId, playerId, StringComparison.Ordinal))
        {
            return;
        }

        if (!_boardState.TryGetPlayer(playerId, out var player) || player is null)
        {
            return;
        }

        if (!_buildingLevelsByCityId.TryGetValue(city.Id, out var buildingLevels))
        {
            buildingLevels = new Dictionary<string, int>(StringComparer.Ordinal);
            _buildingLevelsByCityId[city.Id] = buildingLevels;
        }

        var candidates = _buildingsCatalog.Buildings
            .OrderBy(x => x.BuildingId, StringComparer.Ordinal)
            .ToArray();

        SanguoBuildingDefinition? picked = null;
        var currentLevel = 0;
        foreach (var def in candidates)
        {
            var level = buildingLevels.TryGetValue(def.BuildingId, out var v) ? v : 0;
            if (level < def.MaxLevel)
            {
                picked = def;
                currentLevel = level;
                break;
            }
        }

        if (picked is null)
        {
            return;
        }

        var newLevel = currentLevel + 1;
        if (newLevel < 1 || newLevel > picked.MaxLevel)
        {
            return;
        }

        var costBase = currentLevel == 0 ? picked.BuildCostBase : picked.UpgradeCostBase;
        var costDelta = currentLevel == 0 ? picked.EconomyStepDeltas.BuildCost : picked.EconomyStepDeltas.UpgradeCost;
        var relicStepDelta = GetPersistentRelicStepDelta(playerId);
        var costSources = AppliedMultiplierSources.Building;
        if (relicStepDelta != 0)
            costSources |= AppliedMultiplierSources.Relic;
        var costApplied = CreateAppliedMultipliers(
            characterStepDelta: 0,
            buildingStepDelta: costDelta,
            eventStepDelta: 0,
            actionCardStepDelta: 0,
            relicStepDelta: relicStepDelta,
            regionStepDelta: 0,
            sources: costSources);
        var costMultiplier = costApplied.EffectiveMultiplier;
        var cost = Money.FromDecimal(costBase * costMultiplier);

        if (!player.TrySpend(cost))
        {
            return;
        }

        buildingLevels[picked.BuildingId] = newLevel;

        var evt = new DomainEvent(
            Type: SanguoBuildingBuilt.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoBuildingBuilt(
                GameId: _gameId,
                PlayerId: playerId,
                CityId: city.Id,
                BuildingId: picked.BuildingId,
                NewLevel: newLevel,
                EconomyStepDeltas: picked.EconomyStepDeltas,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId)),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N"));

        await _bus.PublishAsync(evt);

        await PublishPlayerStateChangedAsync(
            playerId: playerId,
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

    private async Task PruneEliminatedAiPlayersAsync(
        string activePlayerId,
        DateTimeOffset occurredAt,
        string correlationId,
        string? causationId)
    {
        if (_playerOrder is null || _playerOrder.Length == 0)
        {
            return;
        }

        var previousOrder = _playerOrder;
        var previousActiveIndex = Array.FindIndex(previousOrder, x => string.Equals(x, activePlayerId, StringComparison.Ordinal));

        var kept = new List<string>(previousOrder.Length);
        await ApplyOwnershipChangeAsync(
            () =>
            {
                var changed = false;
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
                            changed = true;
                        }
                        _relicIdsByPlayerId.Remove(playerId);
                        _relicStepDeltaByPlayerId.Remove(playerId);
                        continue;
                    }

                    kept.Add(playerId);
                }
                return changed;
            },
            triggerCityId: null,
            occurredAt: occurredAt,
            correlationId: correlationId,
            causationId: causationId);

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

    private void ResetRegionCaptureState()
    {
        _capturedRegionOwnerByRegionId.Clear();
        var captured = ComputeCapturedRegionOwners(out _);
        foreach (var (regionId, ownerId) in captured)
        {
            _capturedRegionOwnerByRegionId[regionId] = ownerId;
        }
    }

    private Dictionary<string, string> ComputeCapturedRegionOwners(out Dictionary<string, List<string>> cityIdsByRegion)
    {
        cityIdsByRegion = new Dictionary<string, List<string>>(StringComparer.Ordinal);

        var citiesById = _boardState.GetCitiesSnapshot();
        foreach (var city in citiesById.Values)
        {
            var regionId = (city.RegionId ?? string.Empty).Trim();
            if (regionId.Length == 0)
            {
                continue;
            }

            if (!cityIdsByRegion.TryGetValue(regionId, out var list))
            {
                list = new List<string>();
                cityIdsByRegion[regionId] = list;
            }
            list.Add(city.Id);
        }

        foreach (var list in cityIdsByRegion.Values)
        {
            list.Sort(StringComparer.Ordinal);
        }

        var cityOwnerByCityId = new Dictionary<string, string>(StringComparer.Ordinal);
        if (_playerOrder is null)
        {
            return new Dictionary<string, string>(StringComparer.Ordinal);
        }

        foreach (var playerId in _playerOrder)
        {
            if (!_boardState.TryGetPlayer(playerId, out var player) || player is null)
            {
                continue;
            }

            foreach (var cityId in player.OwnedCityIds)
            {
                if (string.IsNullOrWhiteSpace(cityId))
                {
                    continue;
                }

                cityOwnerByCityId[cityId] = player.PlayerId;
            }
        }

        var captured = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var (regionId, cityIds) in cityIdsByRegion)
        {
            string? ownerId = null;
            var allOwnedBySame = true;
            foreach (var cityId in cityIds)
            {
                if (!cityOwnerByCityId.TryGetValue(cityId, out var owner))
                {
                    allOwnedBySame = false;
                    break;
                }

                if (ownerId is null)
                {
                    ownerId = owner;
                }
                else if (!string.Equals(ownerId, owner, StringComparison.Ordinal))
                {
                    allOwnedBySame = false;
                    break;
                }
            }

            if (allOwnedBySame && !string.IsNullOrWhiteSpace(ownerId))
            {
                captured[regionId] = ownerId!;
            }
        }

        return captured;
    }

    internal Task<bool> ApplyOwnershipChangeAsync(
        Func<bool> mutateOwnership,
        string? triggerCityId,
        DateTimeOffset occurredAt,
        string correlationId,
        string? causationId)
    {
        ArgumentNullException.ThrowIfNull(mutateOwnership, nameof(mutateOwnership));
        return ApplyOwnershipChangeAsync(
            () => Task.FromResult(mutateOwnership()),
            triggerCityId,
            occurredAt,
            correlationId,
            causationId);
    }

    internal async Task<bool> ApplyOwnershipChangeAsync(
        Func<Task<bool>> mutateOwnershipAsync,
        string? triggerCityId,
        DateTimeOffset occurredAt,
        string correlationId,
        string? causationId)
    {
        ArgumentNullException.ThrowIfNull(mutateOwnershipAsync, nameof(mutateOwnershipAsync));

        var changed = await mutateOwnershipAsync();
        if (!changed)
        {
            return false;
        }

        await PublishRegionCaptureChangesAsync(
            triggerCityId: triggerCityId,
            occurredAt: occurredAt,
            correlationId: correlationId,
            causationId: causationId);

        return true;
    }

    internal Task<bool> TransferCityOwnershipAsync(
        string cityId,
        string? newOwnerId,
        string reasonCode,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        EnsureStarted();

        if (string.IsNullOrWhiteSpace(cityId))
            throw new ArgumentException("CityId must be non-empty.", nameof(cityId));

        if (string.IsNullOrWhiteSpace(reasonCode))
            throw new ArgumentException("ReasonCode must be non-empty.", nameof(reasonCode));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        var normalizedNewOwnerId = string.IsNullOrWhiteSpace(newOwnerId) ? null : newOwnerId;

        var cities = _boardState.CitiesById;
        if (!cities.ContainsKey(cityId))
            throw new InvalidOperationException($"City not found in board state: {cityId}");

        SanguoPlayer? newOwner = null;
        if (normalizedNewOwnerId is not null)
        {
            if (!_boardState.TryGetPlayer(normalizedNewOwnerId, out newOwner) || newOwner is null)
                throw new InvalidOperationException($"NewOwnerId not found in board state: {normalizedNewOwnerId}");
        }

        SanguoPlayer? oldOwner = null;
        if (_boardState.TryGetOwnerOfCity(cityId, out var resolved) && resolved is not null)
        {
            oldOwner = resolved;
        }

        var oldOwnerId = oldOwner?.PlayerId;
        if (string.Equals(oldOwnerId, normalizedNewOwnerId, StringComparison.Ordinal))
            return Task.FromResult(false);

        if (oldOwnerId is null && normalizedNewOwnerId is null)
            return Task.FromResult(false);

        return ApplyOwnershipChangeAsync(
            async () =>
            {
                SanguoPlayer.RollbackSnapshot? oldSnapshot = null;
                SanguoPlayer.RollbackSnapshot? newSnapshot = null;

                if (oldOwner is not null)
                    oldSnapshot = oldOwner.CaptureRollbackSnapshot();
                if (newOwner is not null)
                    newSnapshot = newOwner.CaptureRollbackSnapshot();

                var changed = false;

                if (oldOwner is not null && oldSnapshot.HasValue)
                {
                    var remaining = oldSnapshot.Value.OwnedCityIds
                        .Where(x => !string.Equals(x, cityId, StringComparison.Ordinal))
                        .ToArray();
                    if (remaining.Length != oldSnapshot.Value.OwnedCityIds.Count)
                    {
                        oldOwner.RestoreRollbackSnapshot(oldSnapshot.Value with { OwnedCityIds = remaining });
                        changed = true;
                    }
                }

                if (newOwner is not null && newSnapshot.HasValue)
                {
                    var nextOwned = newSnapshot.Value.OwnedCityIds.ToList();
                    if (!nextOwned.Contains(cityId, StringComparer.Ordinal))
                    {
                        nextOwned.Add(cityId);
                        changed = true;
                    }

                    if (changed)
                        newOwner.RestoreRollbackSnapshot(newSnapshot.Value with { OwnedCityIds = nextOwned });
                }

                if (!changed)
                    return false;

                var evt = new DomainEvent(
                    Type: SanguoCityOwnerChanged.EventType,
                    Source: nameof(SanguoTurnManager),
                    Data: JsonElementEventData.FromObject(new SanguoCityOwnerChanged(
                        GameId: _gameId!,
                        TurnNumber: _turnNumber,
                        CityId: cityId,
                        OldOwnerId: oldOwnerId,
                        NewOwnerId: normalizedNewOwnerId,
                        ReasonCode: reasonCode,
                        OccurredAt: occurredAt,
                        CorrelationId: correlationId,
                        CausationId: causationId
                    )),
                    Timestamp: occurredAt.UtcDateTime,
                    Id: Guid.NewGuid().ToString("N"));

                try
                {
                    await _bus.PublishAsync(evt);
                    return true;
                }
                catch (Exception ex)
                {
                    if (oldOwner is not null && oldSnapshot.HasValue)
                        oldOwner.RestoreRollbackSnapshot(oldSnapshot.Value);
                    if (newOwner is not null && newSnapshot.HasValue)
                        newOwner.RestoreRollbackSnapshot(newSnapshot.Value);

                    throw new InvalidOperationException(
                        $"Event publish failed after city ownership change. State has been rolled back (gameId={_gameId}, cityId={cityId}).",
                        ex);
                }
            },
            triggerCityId: cityId,
            occurredAt: occurredAt,
            correlationId: correlationId,
            causationId: causationId);
    }

    private async Task PublishRegionCaptureChangesAsync(
        string? triggerCityId,
        DateTimeOffset occurredAt,
        string correlationId,
        string? causationId)
    {
        if (_gameId is null || _playerOrder is null)
        {
            return;
        }

        var captured = ComputeCapturedRegionOwners(out var cityIdsByRegion);

        foreach (var (regionId, ownerId) in captured)
        {
            if (_capturedRegionOwnerByRegionId.TryGetValue(regionId, out var previousOwner)
                && string.Equals(previousOwner, ownerId, StringComparison.Ordinal))
            {
                continue;
            }

            var cityIds = cityIdsByRegion.TryGetValue(regionId, out var list)
                ? list
                : new List<string>();

            var evt = new DomainEvent(
                Type: SanguoRegionCaptured.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRegionCaptured(
                    GameId: _gameId,
                    RegionId: regionId,
                    OwnerId: ownerId,
                    CityIds: cityIds,
                    ReasonCode: SanguoRegionCaptured.ReasonCaptured,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(evt);
        }

        foreach (var (regionId, previousOwner) in _capturedRegionOwnerByRegionId.ToArray())
        {
            if (captured.TryGetValue(regionId, out var currentOwner)
                && string.Equals(currentOwner, previousOwner, StringComparison.Ordinal))
            {
                continue;
            }

            var reason = captured.ContainsKey(regionId)
                ? SanguoRegionLost.ReasonOwnerChanged
                : SanguoRegionLost.ReasonLostLastCity;

            var evt = new DomainEvent(
                Type: SanguoRegionLost.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRegionLost(
                    GameId: _gameId,
                    RegionId: regionId,
                    OwnerId: previousOwner,
                    ReasonCode: reason,
                    TriggerCityId: triggerCityId,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(evt);
        }

        _capturedRegionOwnerByRegionId.Clear();
        foreach (var (regionId, ownerId) in captured)
        {
            _capturedRegionOwnerByRegionId[regionId] = ownerId;
        }
    }

    internal AppliedMultipliers GetTurnAppliedMultipliersSnapshot(string playerId)
    {
        if (string.IsNullOrWhiteSpace(playerId))
            throw new ArgumentException("PlayerId must be non-empty.", nameof(playerId));

        var baseSteps = AppliedMultipliers.BaseDefaultSteps;
        var eventDelta = _turnEventStepDeltasByPlayerId.TryGetValue(playerId, out var e) ? e : 0;
        var actionCardDelta = _turnActionCardStepDeltasByPlayerId.TryGetValue(playerId, out var a) ? a : 0;
        var relicDelta = GetPersistentRelicStepDelta(playerId);
        var effectiveSteps = AppliedMultipliers.ClampSteps(baseSteps + eventDelta + actionCardDelta + relicDelta);

        var sources = AppliedMultiplierSources.None;
        if (eventDelta != 0)
            sources |= AppliedMultiplierSources.Event;
        if (actionCardDelta != 0)
            sources |= AppliedMultiplierSources.ActionCard;
        if (relicDelta != 0)
            sources |= AppliedMultiplierSources.Relic;

        return new AppliedMultipliers(
            BaseSteps: baseSteps,
            CharacterStepDelta: 0,
            BuildingStepDelta: 0,
            EventStepDelta: eventDelta,
            ActionCardStepDelta: actionCardDelta,
            RelicStepDelta: relicDelta,
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
        var relicDelta = GetPersistentRelicStepDelta(playerId);
        var effectiveSteps = AppliedMultipliers.ClampSteps(baseSteps + next + actionCardDelta + relicDelta);

        return new AppliedMultipliers(
            BaseSteps: baseSteps,
            CharacterStepDelta: 0,
            BuildingStepDelta: 0,
            EventStepDelta: next,
            ActionCardStepDelta: actionCardDelta,
            RelicStepDelta: relicDelta,
            RegionStepDelta: 0,
            EffectiveSteps: effectiveSteps,
            Sources: relicDelta == 0 ? AppliedMultiplierSources.Event : (AppliedMultiplierSources.Event | AppliedMultiplierSources.Relic));
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
        var relicDelta = GetPersistentRelicStepDelta(playerId);
        var effectiveSteps = AppliedMultipliers.ClampSteps(baseSteps + next + eventDelta + relicDelta);

        return new AppliedMultipliers(
            BaseSteps: baseSteps,
            CharacterStepDelta: 0,
            BuildingStepDelta: 0,
            EventStepDelta: eventDelta,
            ActionCardStepDelta: next,
            RelicStepDelta: relicDelta,
            RegionStepDelta: 0,
            EffectiveSteps: effectiveSteps,
            Sources: relicDelta == 0 ? AppliedMultiplierSources.ActionCard : (AppliedMultiplierSources.ActionCard | AppliedMultiplierSources.Relic));
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
                    PickedId: pickedId,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "tile"
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejectedEvt);
            return;
        }

        if (string.Equals(picked.EffectKind, SanguoEffectKinds.StartCombat, StringComparison.Ordinal))
        {
            if (!_boardState.TryGetPlayer(activePlayerId, out var activePlayer) || activePlayer is null)
            {
                var rejectedEvt = new DomainEvent(
                    Type: SanguoRandomEventRejected.EventType,
                    Source: nameof(SanguoTurnManager),
                    Data: JsonElementEventData.FromObject(new SanguoRandomEventRejected(
                        GameId: gameId,
                        PlayerId: activePlayerId,
                        EventId: picked.EventId,
                        EffectKind: picked.EffectKind,
                        RejectReason: "player_not_found",
                        MoneyDelta: picked.MoneyDelta,
                        StepDelta: picked.StepDelta,
                        OccurredAt: occurredAt,
                        CorrelationId: correlationId,
                        CausationId: causationId,
                        RngContextId: rngContextId,
                        CandidatesSortedIdsHash: candidatesSortedIdsHash,
                        PickedIndex: pickedIndex,
                        PickedId: pickedId,
                        EncounterId: picked.EncounterId,
                        EncounterTarget: picked.EncounterTarget,
                        TriggerSource: "tile"
                    )),
                    Timestamp: occurredAt.UtcDateTime,
                    Id: Guid.NewGuid().ToString("N"));
                await _bus.PublishAsync(rejectedEvt);
                return;
            }

            if (string.IsNullOrWhiteSpace(picked.EncounterId) || !picked.EncounterTarget.HasValue)
            {
                var rejectedEvt = new DomainEvent(
                    Type: SanguoRandomEventRejected.EventType,
                    Source: nameof(SanguoTurnManager),
                    Data: JsonElementEventData.FromObject(new SanguoRandomEventRejected(
                        GameId: gameId,
                        PlayerId: activePlayerId,
                        EventId: picked.EventId,
                        EffectKind: picked.EffectKind,
                        RejectReason: "missing_encounter_fields",
                        MoneyDelta: picked.MoneyDelta,
                        StepDelta: picked.StepDelta,
                        OccurredAt: occurredAt,
                        CorrelationId: correlationId,
                        CausationId: causationId,
                        RngContextId: rngContextId,
                        CandidatesSortedIdsHash: candidatesSortedIdsHash,
                        PickedIndex: pickedIndex,
                        PickedId: pickedId,
                        EncounterId: picked.EncounterId,
                        EncounterTarget: picked.EncounterTarget,
                        TriggerSource: "tile"
                    )),
                    Timestamp: occurredAt.UtcDateTime,
                    Id: Guid.NewGuid().ToString("N"));
                await _bus.PublishAsync(rejectedEvt);
                return;
            }

            RecordRandomEventApplied(activePlayerId, picked.EventId, roundNumber);
            var appliedEvtId = Guid.NewGuid().ToString("N");
            var appliedEvt = new DomainEvent(
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
                    AppliedMultipliersAfter: null,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "tile"
                )),
                 Timestamp: occurredAt.UtcDateTime,
                 Id: appliedEvtId);
            await _bus.PublishAsync(appliedEvt);

            var relicMoneyChanged = await TryGrantRelicLootAsync(
                gameId: gameId,
                playerId: activePlayerId,
                sourceKind: "event_tile",
                sourceId: picked.EventId,
                correlationId: correlationId,
                causationId: appliedEvtId,
                occurredAt: occurredAt);

            if (relicMoneyChanged)
            {
                await PublishPlayerStateChangedAsync(
                    playerId: activePlayerId,
                    correlationId: correlationId,
                    causationId: appliedEvtId,
                    occurredAt: occurredAt);
            }

            var combatRngContextId = BuildRngContextId(
                stream: "rng.combat",
                turnNumber: _turnNumber,
                roundNumber: roundNumber,
                sourceId: $"random_event:{picked.EventId}");
            var combatCandidatesSortedIdsHash = ComputeSha256Hex($"combat:random_event:{picked.EncounterId}:{picked.EncounterTarget.Value}");
            var seed = ComputeDeterministicSeed(_randomSeed, combatRngContextId, combatCandidatesSortedIdsHash);
            var encounterInstanceId = $"{picked.EncounterId}:{_turnNumber}:{positionIndex}:{activePlayerId}";

            await StartPveCombatAsync(
                gameId: gameId,
                playerId: activePlayerId,
                player: activePlayer,
                encounterId: encounterInstanceId,
                encounterTarget: picked.EncounterTarget.Value,
                seed: seed,
                occurredAt: occurredAt,
                correlationId: correlationId,
                causationId: appliedEvtId);
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
            var evtId = Guid.NewGuid().ToString("N");
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
                    AppliedMultipliersAfter: effectResult.AppliedMultipliersAfter,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "tile"
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: evtId);
            await _bus.PublishAsync(evt);

            var relicMoneyChanged = await TryGrantRelicLootAsync(
                gameId: gameId,
                playerId: activePlayerId,
                sourceKind: "event_tile",
                sourceId: picked.EventId,
                correlationId: correlationId,
                causationId: evtId,
                occurredAt: occurredAt);

            if (relicMoneyChanged)
            {
                await PublishPlayerStateChangedAsync(
                    playerId: activePlayerId,
                    correlationId: correlationId,
                    causationId: evtId,
                    occurredAt: occurredAt);
            }
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
                    PickedId: pickedId,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "tile"
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
                    PickedId: pickedId,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "global"
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejectedEvt);
            return;
        }

        if (string.Equals(picked.EffectKind, SanguoEffectKinds.StartCombat, StringComparison.Ordinal))
        {
            var rejectedEvt = new DomainEvent(
                Type: SanguoRandomEventRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventRejected(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: publishedEventId,
                    EffectKind: picked.EffectKind,
                    RejectReason: "effect_kind_not_allowed_for_global_events",
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "global"
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
                    AppliedMultipliersAfter: effectResult.AppliedMultipliersAfter,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "global"
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
                    PickedId: pickedId,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "global"
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
                    PickedId: pickedId,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "global"
                )),
                Timestamp: occurredAt.UtcDateTime,
                Id: Guid.NewGuid().ToString("N"));
            await _bus.PublishAsync(rejectedEvt);
            return;
        }

        if (string.Equals(picked.EffectKind, SanguoEffectKinds.StartCombat, StringComparison.Ordinal))
        {
            var rejectedEvt = new DomainEvent(
                Type: SanguoRandomEventRejected.EventType,
                Source: nameof(SanguoTurnManager),
                Data: JsonElementEventData.FromObject(new SanguoRandomEventRejected(
                    GameId: gameId,
                    PlayerId: activePlayerId,
                    EventId: publishedEventId,
                    EffectKind: picked.EffectKind,
                    RejectReason: "effect_kind_not_allowed_for_global_events",
                    MoneyDelta: picked.MoneyDelta,
                    StepDelta: picked.StepDelta,
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId,
                    RngContextId: rngContextId,
                    CandidatesSortedIdsHash: candidatesSortedIdsHash,
                    PickedIndex: pickedIndex,
                    PickedId: pickedId,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "global"
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
                    AppliedMultipliersAfter: effectResult.AppliedMultipliersAfter,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "global"
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
                    PickedId: pickedId,
                    EncounterId: picked.EncounterId,
                    EncounterTarget: picked.EncounterTarget,
                    TriggerSource: "global"
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

    private bool IsFacilityTilePosition(int positionIndex)
    {
        if (_tileTypesByPositionIndex is null)
            return false;

        if (!_tileTypesByPositionIndex.TryGetValue(positionIndex, out var tileType))
            return false;

        return string.Equals(tileType, SanguoMapTileDefinitionV2.TileKindFacility, StringComparison.OrdinalIgnoreCase);
    }

    private async Task TryResolveFacilityTileAsync(
        string gameId,
        string playerId,
        int positionIndex,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        // Stop-loss: facility interaction UI is handled by later tasks. Here we only support auditable loot drops.
        _ = await TryGrantRelicLootAsync(
            gameId: gameId,
            playerId: playerId,
            sourceKind: "facility_tile",
            sourceId: $"tile:{positionIndex}",
            correlationId: correlationId,
            causationId: causationId,
            occurredAt: occurredAt);
    }

    private int GetPersistentRelicStepDelta(string playerId)
    {
        if (string.IsNullOrWhiteSpace(playerId))
            return 0;

        return _relicStepDeltaByPlayerId.TryGetValue(playerId, out var v) ? v : 0;
    }

    private async Task<bool> TryGrantRelicLootAsync(
        string gameId,
        string playerId,
        string sourceKind,
        string sourceId,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt)
    {
        if (_relicsCatalog is null || _relicsCatalog.Relics is null || _relicsCatalog.Relics.Count == 0)
            return false;

        if (!_boardState.TryGetPlayer(playerId, out var player) || player is null)
            return false;

        if (player.IsEliminated)
            return false;

        var roundNumber = ComputeRoundNumber(_turnNumber);
        var rngContextId = BuildRngContextId(
            stream: "rng.loot.relic",
            turnNumber: _turnNumber,
            roundNumber: roundNumber,
            sourceId: $"{sourceKind}:{sourceId}");

        var candidateIds = _relicsCatalog.Relics
            .Select(r => r.RelicId)
            .Where(id => !string.IsNullOrWhiteSpace(id))
            .OrderBy(id => id, StringComparer.Ordinal)
            .ToArray();

        if (candidateIds.Length == 0)
            return false;

        var candidatesSortedIdsHash = ComputeSha256Hex("relics:" + string.Join(",", candidateIds));
        var seed = ComputeDeterministicSeed(_randomSeed, rngContextId, candidatesSortedIdsHash);

        string? pickedId = null;
        int? pickedIndex = null;

        for (var attempt = 0; attempt < candidateIds.Length; attempt++)
        {
            var idx = (seed + attempt) % candidateIds.Length;
            var id = candidateIds[idx];
            if (_grantedRelicIds.Contains(id))
                continue;

            pickedId = id;
            pickedIndex = idx;
            break;
        }

        SanguoRelicDefinition? picked = null;
        if (!string.IsNullOrWhiteSpace(pickedId))
        {
            picked = _relicsCatalog.Relics.FirstOrDefault(r => StringComparer.Ordinal.Equals(r.RelicId, pickedId));
        }

        int? validatedMoneyDelta = null;
        int? validatedStepDelta = null;
        var validPicked = false;

        if (picked is not null)
        {
            if (string.Equals(picked.EffectKind, SanguoEffectKinds.EconomyStepDelta, StringComparison.Ordinal)
                && picked.EconomyStepDelta.HasValue)
            {
                validatedStepDelta = picked.EconomyStepDelta.Value;
                validPicked = true;
            }
            else if (string.Equals(picked.EffectKind, SanguoEffectKinds.MoneyDelta, StringComparison.Ordinal)
                && picked.MoneyDelta.HasValue)
            {
                validatedMoneyDelta = picked.MoneyDelta.Value;
                validPicked = true;
            }
        }

        var lootEvtId = Guid.NewGuid().ToString("N");
        var loot = new DomainEvent(
            Type: SanguoLootGranted.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoLootGranted(
                GameId: gameId,
                PlayerId: playerId,
                LootKind: "relic",
                MoneyDelta: validPicked ? validatedMoneyDelta : null,
                CardId: null,
                RelicId: validPicked ? picked!.RelicId : null,
                SourceKind: sourceKind,
                SourceId: sourceId,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId,
                RngContextId: rngContextId,
                CandidatesSortedIdsHash: candidatesSortedIdsHash,
                PickedIndex: pickedIndex,
                PickedId: pickedId
            )),
            Timestamp: occurredAt.UtcDateTime,
            Id: lootEvtId);
        await _bus.PublishAsync(loot);

        if (!validPicked || picked is null)
            return false;

        _grantedRelicIds.Add(picked.RelicId);
        if (!_relicIdsByPlayerId.TryGetValue(playerId, out var owned))
        {
            owned = new HashSet<string>(StringComparer.Ordinal);
            _relicIdsByPlayerId[playerId] = owned;
        }
        owned.Add(picked.RelicId);

        var moneyChanged = false;
        if (validatedStepDelta.HasValue)
        {
            var current = _relicStepDeltaByPlayerId.TryGetValue(playerId, out var v) ? v : 0;
            var next = checked(current + validatedStepDelta.Value);
            _relicStepDeltaByPlayerId[playerId] = next;
        }
        else if (validatedMoneyDelta.HasValue)
        {
            moneyChanged = ApplyMoneyDeltaToPlayer(player, validatedMoneyDelta.Value);
        }

        var applied = new DomainEvent(
            Type: SanguoRelicApplied.EventType,
            Source: nameof(SanguoTurnManager),
            Data: JsonElementEventData.FromObject(new SanguoRelicApplied(
                GameId: gameId,
                PlayerId: playerId,
                RelicId: picked.RelicId,
                EffectKind: picked.EffectKind,
                MoneyDelta: validatedMoneyDelta,
                StepDelta: validatedStepDelta,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: lootEvtId
            )),
            Timestamp: occurredAt.UtcDateTime,
            Id: Guid.NewGuid().ToString("N"));
        await _bus.PublishAsync(applied);

        return moneyChanged;
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

    private static IReadOnlyDictionary<string, SanguoBuildingDefinition> CreateBuildingsById(SanguoBuildingsCatalog? catalog)
    {
        if (catalog is null || catalog.Buildings is null || catalog.Buildings.Count == 0)
        {
            return new Dictionary<string, SanguoBuildingDefinition>(StringComparer.Ordinal);
        }

        var dict = new Dictionary<string, SanguoBuildingDefinition>(StringComparer.Ordinal);
        foreach (var def in catalog.Buildings)
        {
            if (!dict.TryAdd(def.BuildingId, def))
            {
                throw new ArgumentException($"Duplicate BuildingId in buildings catalog: {def.BuildingId}", nameof(catalog));
            }
        }

        return dict;
    }

    private int ComputeCityBuildingTollStepDelta(string cityId) =>
        ComputeCityBuildingStepDelta(cityId, d => d.Toll);

    private int ComputeCityBuildingIncomeSettlementStepDelta(string cityId) =>
        ComputeCityBuildingStepDelta(cityId, d => d.IncomeSettlement);

    private int ComputeCityBuildingStepDelta(string cityId, Func<SanguoEconomyStepDeltas, int> selector)
    {
        if (string.IsNullOrWhiteSpace(cityId))
        {
            return 0;
        }

        if (_buildingsCatalog is null || _buildingsCatalog.Buildings is null || _buildingsCatalog.Buildings.Count == 0)
        {
            return 0;
        }

        if (!_buildingLevelsByCityId.TryGetValue(cityId, out var levels) || levels.Count == 0)
        {
            return 0;
        }

        var sum = 0;
        foreach (var (buildingId, level) in levels)
        {
            if (level <= 0)
            {
                continue;
            }

            if (!_buildingsById.TryGetValue(buildingId, out var def))
            {
                continue;
            }

            var delta = selector(def.EconomyStepDeltas);
            sum = checked(sum + (delta * level));
        }

        return sum;
    }

    private static AppliedMultipliers CreateAppliedMultipliers(
        int characterStepDelta,
        int buildingStepDelta,
        int eventStepDelta,
        int actionCardStepDelta,
        int relicStepDelta,
        int regionStepDelta,
        AppliedMultiplierSources sources)
    {
        var baseSteps = AppliedMultipliers.BaseDefaultSteps;
        var effectiveSteps = AppliedMultipliers.ClampSteps(
            baseSteps
            + characterStepDelta
            + buildingStepDelta
            + eventStepDelta
            + actionCardStepDelta
            + relicStepDelta
            + regionStepDelta);

        return new AppliedMultipliers(
            BaseSteps: baseSteps,
            CharacterStepDelta: characterStepDelta,
            BuildingStepDelta: buildingStepDelta,
            EventStepDelta: eventStepDelta,
            ActionCardStepDelta: actionCardStepDelta,
            RelicStepDelta: relicStepDelta,
            RegionStepDelta: regionStepDelta,
            EffectiveSteps: effectiveSteps,
            Sources: sources);
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
                var buildingTollStepDelta = ComputeCityBuildingTollStepDelta(city.Id);
                var ownerRelicStepDelta = GetPersistentRelicStepDelta(owner.PlayerId);
                var tollSources = AppliedMultiplierSources.None;
                if (buildingTollStepDelta != 0)
                    tollSources |= AppliedMultiplierSources.Building;
                if (ownerRelicStepDelta != 0)
                    tollSources |= AppliedMultiplierSources.Relic;
                var applied = CreateAppliedMultipliers(
                    characterStepDelta: 0,
                    buildingStepDelta: buildingTollStepDelta,
                    eventStepDelta: 0,
                    actionCardStepDelta: 0,
                    relicStepDelta: ownerRelicStepDelta,
                    regionStepDelta: 0,
                    sources: tollSources);

                _ = await _economy.TryPayTollAndPublishEventAsync(
                    gameId: _gameId,
                    turnNumber: _turnNumber,
                    players: players,
                    citiesById: citiesById,
                    treasury: _treasury,
                    payerId: aiPlayerId,
                    cityId: city.Id,
                    tollMultiplier: applied.EffectiveMultiplier,
                    correlationId: correlationId,
                    causationId: causationId,
                    occurredAt: occurredAt,
                    appliedMultipliersOverride: applied);
            }
            return;
        }

        await ApplyOwnershipChangeAsync(
            () => _economy.TryBuyCityAndPublishEventAsync(
                gameId: _gameId,
                turnNumber: _turnNumber,
                players: players,
                citiesById: citiesById,
                buyerId: aiPlayerId,
                cityId: city.Id,
                priceMultiplier: 1.0m,
                correlationId: correlationId,
                causationId: causationId,
                occurredAt: occurredAt),
            triggerCityId: city.Id,
            occurredAt: occurredAt,
            correlationId: correlationId,
            causationId: causationId);
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
            TreasuryMinorUnits: _treasury.MinorUnits,
            ContentPackId: _contentPackId,
            ContentPackVersion: _contentPackVersion,
            ActionCardsByPlayerId: BuildActionCardsSnapshot()
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
        ResetRegionCaptureState();
        RestoreActionCardInventory(snapshot.ActionCardsByPlayerId, order);
    }

    private void ResetActionCardInventory(string[] playerOrder)
    {
        _actionCardsByPlayerId.Clear();

        if (_actionCardsCatalog is null || _actionCardsCatalog.Cards.Count == 0)
        {
            return;
        }

        var cardIds = _actionCardsCatalog.Cards
            .Select(c => (c.CardId ?? string.Empty).Trim())
            .Where(id => id.Length != 0)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(id => id, StringComparer.Ordinal)
            .ToArray();

        foreach (var playerId in playerOrder)
        {
            var cards = new Dictionary<string, int>(StringComparer.Ordinal);
            _actionCardsByPlayerId[playerId] = cards;

            var remaining = MaxActionCardsPerPlayer;
            foreach (var cardId in cardIds)
            {
                if (remaining <= 0)
                {
                    break;
                }

                var add = Math.Min(InitialActionCardCopiesPerType, remaining);
                if (add <= 0)
                {
                    break;
                }

                cards[cardId] = add;
                remaining -= add;
            }
        }
    }

    private void RestoreActionCardInventory(
        IReadOnlyDictionary<string, IReadOnlyDictionary<string, int>>? snapshot,
        string[] playerOrder)
    {
        _actionCardsByPlayerId.Clear();

        if (snapshot is null)
        {
            ResetActionCardInventory(playerOrder);
            return;
        }

        foreach (var playerId in playerOrder)
        {
            if (!snapshot.TryGetValue(playerId, out var cards) || cards is null)
            {
                _actionCardsByPlayerId[playerId] = new Dictionary<string, int>(StringComparer.Ordinal);
                continue;
            }

            var restored = new Dictionary<string, int>(StringComparer.Ordinal);
            var remaining = MaxActionCardsPerPlayer;
            foreach (var (cardIdRaw, countRaw) in cards.OrderBy(k => k.Key, StringComparer.Ordinal))
            {
                var cardId = (cardIdRaw ?? string.Empty).Trim();
                if (cardId.Length == 0 || countRaw <= 0 || remaining <= 0)
                {
                    continue;
                }

                var add = Math.Min(countRaw, remaining);
                restored[cardId] = add;
                remaining -= add;
            }

            _actionCardsByPlayerId[playerId] = restored;
        }
    }

    private IReadOnlyDictionary<string, IReadOnlyDictionary<string, int>> BuildActionCardsSnapshot()
    {
        if (_actionCardsByPlayerId.Count == 0)
        {
            return new Dictionary<string, IReadOnlyDictionary<string, int>>(StringComparer.Ordinal);
        }

        var snapshot = new Dictionary<string, IReadOnlyDictionary<string, int>>(StringComparer.Ordinal);
        foreach (var (playerId, cards) in _actionCardsByPlayerId)
        {
            var copy = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (var (cardId, count) in cards)
            {
                if (count > 0)
                {
                    copy[cardId] = count;
                }
            }
            snapshot[playerId] = copy;
        }

        return snapshot;
    }

    private bool HasActionCard(string playerId, string cardId)
    {
        if (string.IsNullOrWhiteSpace(playerId) || string.IsNullOrWhiteSpace(cardId))
        {
            return false;
        }

        return _actionCardsByPlayerId.TryGetValue(playerId, out var cards)
            && cards.TryGetValue(cardId, out var count)
            && count > 0;
    }

    private void ConsumeActionCard(string playerId, string cardId)
    {
        if (!_actionCardsByPlayerId.TryGetValue(playerId, out var cards))
        {
            return;
        }

        if (!cards.TryGetValue(cardId, out var count) || count <= 0)
        {
            return;
        }

        if (count == 1)
        {
            cards.Remove(cardId);
            return;
        }

        cards[cardId] = count - 1;
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
