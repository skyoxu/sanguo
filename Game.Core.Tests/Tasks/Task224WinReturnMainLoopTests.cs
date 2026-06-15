using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using System.Linq;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task224WinReturnMainLoopTests
{
    // ACC:T224.1 ACC:T224.4 ACC:T224.5 ACC:T224.8 ACC:T224.9
    [Fact]
    public void ShouldResolveCombatWin_WhenPlayerMainUnitDefeatsEnemyMainUnit()
    {
        var result = ResolveWinAtCombatEndHp();

        result.Outcome.Should().Be("win");
        result.MoneyDelta.Should().BeGreaterThan(0m);
    }

    // ACC:T224.6 ACC:T224.10
    [Fact]
    public void ShouldKeepWinReturnBehaviorInPureCore_WhenEvidenceIsValidated()
    {
        var hasGodotReferences = typeof(SanguoCombatResolver).Assembly.GetReferencedAssemblies()
            .Any(name => !string.IsNullOrEmpty(name.Name) && name.Name.StartsWith("Godot"));

        hasGodotReferences.Should().BeFalse();
    }

    // ACC:T224.7 ACC:T224.11
    [Fact]
    public void ShouldPreservePassingCombatResolverBehavior_WhenWinReturnEvidenceIsAdded()
    {
        var result = SanguoCombatResolver.ResolvePveCombat(combatRating: 12, encounterTarget: 10, seed: 224);

        result.Outcome.Should().Be("win");
    }

    private static SanguoCombatResult ResolveWinAtCombatEndHp()
    {
        var stats = new SanguoCombatStatsDefinition(
            MaxHP: 100,
            CurrentHP: 37,
            Attack: 18,
            CritRate: 0m,
            CritMultiplier: 1.5m,
            LifeStealRate: 0m,
            DodgeRate: 0m,
            AttackSpeed: 2.0m,
            DamageReductionRate: 0m,
            ReflectRate: 0m,
            AoEEnabled: false);

        return SanguoCombatResolver.ResolvePveCombat(stats, combatRating: 0, encounterTarget: 12, seed: 224);
    }
}
