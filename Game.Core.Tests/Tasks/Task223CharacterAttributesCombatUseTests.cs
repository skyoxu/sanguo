using System;
using System.Linq;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task223CharacterAttributesCombatUseTests
{
    // acceptance: ACC:T223.1
    [Fact]
    public void ShouldExposePrdV4CharacterCombatAttributeState_WhenRulesFreezeRequirementIsImplemented()
    {
        var stats = new SanguoCombatStatsDefinition(
            MaxHP: 120,
            CurrentHP: 100,
            Attack: 14,
            CritRate: 0.20m,
            CritMultiplier: 1.75m,
            LifeStealRate: 0.10m,
            DodgeRate: 0.05m,
            AttackSpeed: 1.50m,
            DamageReductionRate: 0.15m,
            ReflectRate: 0.08m,
            AoEEnabled: true);

        stats.MaxHP.Should().Be(120);
        stats.CurrentHP.Should().Be(100);
        stats.Attack.Should().Be(14);
        stats.CritRate.Should().Be(0.20m);
        stats.CritMultiplier.Should().Be(1.75m);
        stats.LifeStealRate.Should().Be(0.10m);
        stats.DodgeRate.Should().Be(0.05m);
        stats.AttackSpeed.Should().Be(1.50m);
        stats.DamageReductionRate.Should().Be(0.15m);
        stats.ReflectRate.Should().Be(0.08m);
        stats.AoEEnabled.Should().BeTrue();
    }

    // acceptance: ACC:T223.2
    [Fact]
    public void ShouldKeepSanguoCombatResolverAsPrimaryCombatResolutionSurface_WhenAttributesAreConsumed()
    {
        typeof(SanguoCombatResolver).Namespace.Should().Be("Game.Core.Services.Sanguo");

        typeof(SanguoCombatResolver).GetMethods()
            .Where(method => method.Name == nameof(SanguoCombatResolver.ResolvePveCombat))
            .Should().Contain(method => method.GetParameters()
                .Any(parameter => parameter.ParameterType == typeof(SanguoCombatStatsDefinition)),
                "Task 223 must extend the existing Sanguo combat resolver instead of adding a parallel resolver family");
    }

    // acceptance: ACC:T223.3
    [Fact]
    public void ShouldNotIntroduceParallelCharacterCombatResolverSurface_WhenMainResolverIsExtended()
    {
        var gameCoreAssembly = typeof(SanguoCombatResolver).Assembly;

        gameCoreAssembly.GetType("Game.Core.Combat.CharacterCombatResolver").Should().BeNull(
            "PRD-SANGUO-V4 keeps SanguoCombatResolver as the governed combat simulation entry point");
    }

    // acceptance: ACC:T223.4
    [Fact]
    public void ShouldKeepCombatResolutionPureCore_WhenRulesFreezeRequirementIsImplemented()
    {
        var godotReferences = typeof(SanguoCombatResolver).Assembly.GetReferencedAssemblies()
            .Where(name => name.Name is not null && name.Name.StartsWith("Godot", StringComparison.OrdinalIgnoreCase))
            .Select(name => name.FullName)
            .ToArray();

        godotReferences.Should().BeEmpty("REQ-190c71c34423 requires combat attribute resolution to stay in pure core logic");
    }

    // acceptance: ACC:T223.5
    [Fact]
    public void ShouldChangeMainResolverCombatResult_WhenAttackAttributeChanges()
    {
        var weakStats = CreateStats(attack: 8);
        var strongStats = CreateStats(attack: 18);

        var weakResult = SanguoCombatResolver.ResolvePveCombat(playerStats: weakStats, combatRating: 0, encounterTarget: 12, seed: 223);
        var strongResult = SanguoCombatResolver.ResolvePveCombat(playerStats: strongStats, combatRating: 0, encounterTarget: 12, seed: 223);

        weakResult.Outcome.Should().Be("lose");
        strongResult.Outcome.Should().Be("win");
        strongResult.EffectiveCombatRating.Should().BeGreaterThan(weakResult.EffectiveCombatRating);
    }

    // acceptance: ACC:T223.6
    [Fact]
    public void ShouldChangeEffectiveCombatRating_WhenEachV4CombatAttributeChanges()
    {
        var baseline = CreateStats(
            maxHp: 100,
            currentHp: 60,
            attack: 8,
            critRate: 0m,
            critMultiplier: 1.5m,
            lifeStealRate: 0m,
            dodgeRate: 0m,
            attackSpeed: 2.0m,
            damageReductionRate: 0m,
            reflectRate: 0m,
            aoeEnabled: false);
        var baselineRating = ResolveRating(baseline);

        var variants = new[]
        {
            CreateStats(maxHp: 200, currentHp: 60, attack: 8),
            CreateStats(maxHp: 100, currentHp: 100, attack: 8),
            CreateStats(maxHp: 100, currentHp: 60, attack: 12),
            CreateStats(maxHp: 100, currentHp: 60, attack: 8, critRate: 0.50m),
            CreateStats(maxHp: 100, currentHp: 60, attack: 8, critRate: 0.50m, critMultiplier: 2.5m),
            CreateStats(maxHp: 100, currentHp: 60, attack: 8, lifeStealRate: 0.75m),
            CreateStats(maxHp: 100, currentHp: 60, attack: 8, dodgeRate: 0.75m),
            CreateStats(maxHp: 100, currentHp: 60, attack: 8, attackSpeed: 1.0m),
            CreateStats(maxHp: 100, currentHp: 60, attack: 8, damageReductionRate: 0.75m),
            CreateStats(maxHp: 100, currentHp: 60, attack: 8, reflectRate: 0.75m),
            CreateStats(maxHp: 100, currentHp: 60, attack: 8, aoeEnabled: true),
        };

        variants.Select(ResolveRating).Should().OnlyContain(rating => rating != baselineRating,
            "every PRD v4 player combat attribute must be consumed by the governed resolver");
    }

    // acceptance: ACC:T223.7
    [Fact]
    public void ShouldUseAttributePayloadInsteadOfLegacyCombatRating_WhenStatsAreSupplied()
    {
        var weakStats = CreateStats(attack: 1);
        var strongStats = CreateStats(attack: 18);

        var weakResult = SanguoCombatResolver.ResolvePveCombat(playerStats: weakStats, combatRating: 99, encounterTarget: 12, seed: 223);
        var strongResult = SanguoCombatResolver.ResolvePveCombat(playerStats: strongStats, combatRating: 0, encounterTarget: 12, seed: 223);

        weakResult.Outcome.Should().Be("lose");
        strongResult.Outcome.Should().Be("win");
    }

    // acceptance: ACC:T223.8
    [Fact]
    public void ShouldResolveSameMainResolverCombatResult_WhenAttributesAndSeedAreIdentical()
    {
        var stats = CreateStats(attack: 12, critRate: 0.25m, damageReductionRate: 0.10m);

        var firstResult = SanguoCombatResolver.ResolvePveCombat(playerStats: stats, combatRating: 0, encounterTarget: 10, seed: 223);
        var secondResult = SanguoCombatResolver.ResolvePveCombat(playerStats: stats, combatRating: 0, encounterTarget: 10, seed: 223);

        secondResult.Should().Be(firstResult);
    }

    // acceptance: ACC:T223.9
    [Fact]
    public void ShouldRejectInvalidCombatAttributes_WhenNumericValuesAreOutOfRange()
    {
        var invalidHp = () => SanguoCombatResolver.ResolvePveCombat(
            playerStats: CreateStats(maxHp: 100, currentHp: 120),
            combatRating: 0,
            encounterTarget: 10,
            seed: 223);
        var invalidRate = () => SanguoCombatResolver.ResolvePveCombat(
            playerStats: CreateStats(critRate: 1.20m),
            combatRating: 0,
            encounterTarget: 10,
            seed: 223);

        invalidHp.Should().Throw<ArgumentOutOfRangeException>().And.ParamName.Should().Be("playerStats");
        invalidRate.Should().Throw<ArgumentOutOfRangeException>().And.ParamName.Should().Be("playerStats");
    }

    // acceptance: ACC:T223.10
    [Fact]
    public void ShouldPreserveLegacyCombatRatingResolver_WhenAttributePayloadIsUnavailable()
    {
        var result = SanguoCombatResolver.ResolvePveCombat(combatRating: 12, encounterTarget: 10, seed: 223);

        result.Outcome.Should().Be("win");
        result.EffectiveCombatRating.Should().Be(12);
    }

    [Fact]
    public void ShouldExposeTraceableCoverageMembersOnGovernedResolver_WhenTaskViewIsValidated()
    {
        typeof(SanguoCombatResolver).GetMethods()
            .Where(method => method.Name == nameof(SanguoCombatResolver.ResolvePveCombat))
            .Should().HaveCountGreaterThan(1);
    }

    private static int ResolveRating(SanguoCombatStatsDefinition stats)
    {
        return SanguoCombatResolver.ResolvePveCombat(playerStats: stats, combatRating: 0, encounterTarget: 100, seed: 223)
            .EffectiveCombatRating;
    }

    private static SanguoCombatStatsDefinition CreateStats(
        int maxHp = 100,
        int currentHp = 100,
        int attack = 12,
        decimal critRate = 0m,
        decimal critMultiplier = 1.5m,
        decimal lifeStealRate = 0m,
        decimal dodgeRate = 0m,
        decimal attackSpeed = 2.0m,
        decimal damageReductionRate = 0m,
        decimal reflectRate = 0m,
        bool aoeEnabled = false)
    {
        return new SanguoCombatStatsDefinition(
            MaxHP: maxHp,
            CurrentHP: currentHp,
            Attack: attack,
            CritRate: critRate,
            CritMultiplier: critMultiplier,
            LifeStealRate: lifeStealRate,
            DodgeRate: dodgeRate,
            AttackSpeed: attackSpeed,
            DamageReductionRate: damageReductionRate,
            ReflectRate: reflectRate,
            AoEEnabled: aoeEnabled);
    }
}
