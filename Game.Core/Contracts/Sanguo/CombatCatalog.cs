using System;
using System.Collections.Generic;

namespace Game.Core.Contracts.Sanguo;

/// <summary>
/// DTO: EnemyDefinition
/// Description: Formal enemy combat definition for random-event combat references.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed record EnemyDefinition(
    string Id,
    string NameKey,
    int CombatRating,
    SanguoCombatStatsDefinition? Stats = null
);

/// <summary>
/// DTO: BossDefinition
/// Description: Formal Boss combat definition for random-event and campaign combat references.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed record BossDefinition(
    string Id,
    string NameKey,
    int CombatRating,
    SanguoCombatStatsDefinition? Stats = null
);

/// <summary>
/// DTO: CombatCatalog
/// Description: Formal enemy and Boss combat catalog.
/// </summary>
/// <remarks>
/// Related ADRs: ADR-0004 (event bus and contracts), ADR-0005 (quality gates).
/// Overlay reference: docs/architecture/overlays/PRD-SANGUO-V4/08/08-Contracts-Combat-Baseline.md.
/// </remarks>
public sealed record CombatCatalog(
    IReadOnlyList<EnemyDefinition> EnemyDefinitions,
    IReadOnlyList<BossDefinition> Bosses
)
{
    public IReadOnlyList<EnemyDefinition> Enemies => EnemyDefinitions;

    public object? Resolve(string referenceId, string targetKind)
    {
        if (string.Equals(targetKind, "Boss", StringComparison.OrdinalIgnoreCase))
        {
            return FindBoss(referenceId);
        }

        return FindEnemy(referenceId);
    }

    public EnemyDefinition? FindEnemy(string referenceId)
    {
        foreach (var enemy in EnemyDefinitions)
        {
            if (string.Equals(enemy.Id, referenceId, StringComparison.Ordinal))
            {
                return enemy;
            }
        }

        return null;
    }

    public BossDefinition? FindBoss(string referenceId)
    {
        foreach (var boss in Bosses)
        {
            if (string.Equals(boss.Id, referenceId, StringComparison.Ordinal))
            {
                return boss;
            }
        }

        return null;
    }
}
