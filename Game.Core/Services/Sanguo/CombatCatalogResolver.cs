using System;
using System.Collections.Generic;
using System.Linq;
using Game.Core.Contracts.Sanguo;

namespace Game.Core.Services.Sanguo;

public sealed class CombatCatalogResolver
{
    private readonly CombatCatalog _catalog;

    public CombatCatalogResolver()
        : this(CreateDefaultCatalog())
    {
    }

    public CombatCatalogResolver(CombatCatalog catalog)
    {
        _catalog = catalog;
    }

    public CombatCatalogResolution Resolve(string referenceId, string targetKind)
    {
        if (string.IsNullOrWhiteSpace(referenceId))
        {
            return CombatCatalogResolution.Fail(referenceId, targetKind, "missing_reference_id");
        }

        if (string.Equals(targetKind, "Boss", StringComparison.OrdinalIgnoreCase))
        {
            var boss = _catalog.Bosses.FirstOrDefault(item => string.Equals(item.Id, referenceId, StringComparison.Ordinal));
            return boss is null
                ? CombatCatalogResolution.Fail(referenceId, targetKind, "boss_not_found")
                : CombatCatalogResolution.ForBoss(boss);
        }

        var enemy = _catalog.Enemies.FirstOrDefault(item => string.Equals(item.Id, referenceId, StringComparison.Ordinal));
        return enemy is null
            ? CombatCatalogResolution.Fail(referenceId, targetKind, "enemy_not_found")
            : CombatCatalogResolution.ForEnemy(enemy);
    }

    public CombatCatalogResolution ResolveEnemy(string referenceId) => Resolve(referenceId, "Enemy");

    public CombatCatalogResolution ResolveBoss(string referenceId) => Resolve(referenceId, "Boss");

    private static CombatCatalog CreateDefaultCatalog()
    {
        return new CombatCatalog(
            EnemyDefinitions: new[]
            {
                new EnemyDefinition(
                    Id: "enemy_bandit_scout",
                    NameKey: "combat.enemy.bandit_scout.name",
                    CombatRating: 10),
                new EnemyDefinition(
                    Id: "enc_event_combat_small",
                    NameKey: "combat.enemy.event_small.name",
                    CombatRating: 10),
                new EnemyDefinition(
                    Id: "enc_event_combat_medium",
                    NameKey: "combat.enemy.event_medium.name",
                    CombatRating: 15),
                new EnemyDefinition(
                    Id: "enc_event_combat_large",
                    NameKey: "combat.enemy.event_large.name",
                    CombatRating: 20),
            },
            Bosses: new[]
            {
                new BossDefinition(
                    Id: "boss_yellow_turban_leader",
                    NameKey: "combat.boss.yellow_turban_leader.name",
                    CombatRating: 30),
                new BossDefinition(
                    Id: "boss_yellow_turban",
                    NameKey: "combat.boss.yellow_turban.name",
                    CombatRating: 30),
            });
    }
}

public sealed record CombatCatalogResolution(
    bool Success,
    string? Id,
    string TargetKind,
    EnemyDefinition? Enemy,
    BossDefinition? Boss,
    string? Error)
{
    public static CombatCatalogResolution ForEnemy(EnemyDefinition enemy)
        => new(true, enemy.Id, "Enemy", enemy, null, null);

    public static CombatCatalogResolution ForBoss(BossDefinition boss)
        => new(true, boss.Id, "Boss", null, boss, null);

    public static CombatCatalogResolution Fail(string? id, string? targetKind, string error)
        => new(false, id, string.IsNullOrWhiteSpace(targetKind) ? "Enemy" : targetKind, null, null, error);
}
