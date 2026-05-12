using System.Collections.Generic;

namespace Game.Godot.Scripts.UI;

public sealed record HudGameStartedDto(
    IReadOnlyDictionary<string, string> CharacterAssignments,
    IReadOnlyList<string> PlayerIds,
    int PlayersCount,
    int StartingMoneyPreset,
    string CommanderId,
    string ActiveStrategemId,
    string PassiveStrategemId,
    string DifficultyCode,
    string RunMode);

public readonly record struct HudScoreDto(int Value);
public readonly record struct HudHealthDto(int Value);
public readonly record struct HudTurnDto(string ActivePlayerId, int Year, int Month, int Day);
public readonly record struct HudPlayerStateDto(string PlayerId, decimal Money, int PositionIndex);
public readonly record struct HudDiceRolledDto(string PlayerId, int Value);
public readonly record struct HudCityTollPaidDto(decimal TreasuryOverflow, string? PayerId, string? OwnerId, string? CityId);
public readonly record struct HudCityBoughtDto(string BuyerId, string CityId);
public readonly record struct HudTokenMovedDto(string PlayerId, int ToIndex, string CorrelationId);
public readonly record struct HudBossChallengePromptedDto(string BossId, int RoundNumber, int MapCycleNumber, int NextRoundPressureForecast);
public readonly record struct HudObjectiveSkippedDto(string ObjectiveId, string Reason, string BossId, int RoundNumber, int MapCycleNumber);
