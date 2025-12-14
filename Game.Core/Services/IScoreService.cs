using Game.Core.Domain;

namespace Game.Core.Services;

/// <summary>
/// Score calculation policy for the domain layer.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0021 (C# Domain Layer Architecture)
/// </remarks>
public interface IScoreService
{
    int ComputeAddedScore(int basePoints, GameConfig config);
}
