using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Contracts.Sanguo;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task225CombatCatalogTests
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 64,
    };

    // ACC:T225.1
    [Fact]
    public void ShouldExposeTraceableCombatCatalogTypes_WhenTask225CoreContractsAreInspected()
    {
        var characterType = RequireType("CharacterDefinition");
        var enemyType = RequireAnyType("CombatEnemyDefinition", "EnemyCombatDefinition", "EnemyDefinition");
        var bossType = RequireAnyType("CombatBossDefinition", "BossCombatDefinition", "BossDefinition");

        characterType.Should().NotBeNull();
        enemyType.Should().NotBeNull();
        bossType.Should().NotBeNull();
    }

    // ACC:T225.2
    [Fact]
    public void ShouldPreserveCombatRating_WhenCharacterDefinitionAddsExtendedCombatAttributes()
    {
        var characterType = RequireType("CharacterDefinition");
        var propertyNames = GetPublicPropertyNames(characterType);

        propertyNames.Should().Contain("CombatRating");
        propertyNames.Should().Contain(new[]
        {
            "Attack",
            "Defense",
            "Health",
            "Morale"
        });
    }

    // ACC:T225.3
    [Fact]
    public void ShouldLoadExistingCharacterData_WhenOnlyCombatRatingIsPresent()
    {
        const string legacyJson = """
            {
              "characterId": "char_legacy_guard",
              "nameKey": "character.legacy_guard.name",
              "descriptionKey": "character.legacy_guard.desc",
              "combatRating": 42,
              "portraitPath": "res://Assets/characters/legacy_guard.png",
              "startingMoneyStepDelta": 1,
              "economyStepDeltas": {
                "buyPrice": 0,
                "toll": 0,
                "incomeSettlement": 0,
                "buildCost": 0,
                "upgradeCost": 0
              }
            }
            """;

        var character = JsonSerializer.Deserialize<SanguoCharacterDefinition>(legacyJson, JsonOptions);

        character.Should().NotBeNull();
        character!.CombatRating.Should().Be(42);
        character.Attack.Should().Be(0);
        character.Defense.Should().Be(0);
        character.Health.Should().Be(0);
        character.Morale.Should().Be(0);
    }

    // ACC:T225.4
    [Fact]
    public void ShouldExposeFormalEnemyCatalogEntries_WhenCombatCatalogIsInspected()
    {
        var catalogType = RequireAnyType("CombatCatalog", "CombatDefinitionCatalog", "CombatEncounterCatalog");
        var memberNames = GetPublicMemberNames(catalogType);

        memberNames.Should().Contain(name => name.Contains("Enemy", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T225.5
    [Fact]
    public void ShouldExposeFormalBossCatalogEntries_WhenCombatCatalogIsInspected()
    {
        var catalogType = RequireAnyType("CombatCatalog", "CombatDefinitionCatalog", "CombatEncounterCatalog");
        var memberNames = GetPublicMemberNames(catalogType);

        memberNames.Should().Contain(name => name.Contains("Boss", StringComparison.OrdinalIgnoreCase));
    }

    // ACC:T225.6
    [Fact]
    public void ShouldResolveEnemyReference_WhenRandomEventTargetsEnemyCatalogEntry()
    {
        var combatEvents = LoadRandomEventsCatalogFromData().Events
            .Where(e => e.EffectKind == SanguoEffectKinds.StartCombat)
            .ToArray();
        var resolver = new CombatCatalogResolver();

        combatEvents.Should().HaveCount(3);
        foreach (var combatEvent in combatEvents)
        {
            var result = resolver.Resolve(combatEvent.EncounterId!, "Enemy");

            result.Success.Should().BeTrue("every random event combat reference must resolve to an explicit enemy definition");
            result.Id.Should().Be(combatEvent.EncounterId);
            result.TargetKind.Should().Be("Enemy");
            result.Enemy.Should().NotBeNull();
            result.Enemy!.Id.Should().Be(combatEvent.EncounterId);
            result.Error.Should().BeNull();
        }
    }

    // ACC:T225.7
    [Fact]
    public void ShouldResolveBossReference_WhenRandomEventTargetsBossCatalogEntry()
    {
        var resolver = new CombatCatalogResolver();
        var result = resolver.Resolve("boss_yellow_turban_leader", "Boss");

        result.Success.Should().BeTrue("Boss combat references must resolve to explicit Boss definitions");
        result.Id.Should().Be("boss_yellow_turban_leader");
        result.TargetKind.Should().Be("Boss");
        result.Boss.Should().NotBeNull();
        result.Boss!.Id.Should().Be("boss_yellow_turban_leader");
        result.Error.Should().BeNull();
    }

    // ACC:T225.8
    [Fact]
    public void ShouldRejectUnresolvedCombatReference_WhenRandomEventTargetIsMissing()
    {
        var resolver = new CombatCatalogResolver();
        var result = resolver.Resolve("missing_task_225_reference", "Enemy");

        result.Success.Should().BeFalse("unresolved combat encounter references must fail validation instead of being silently accepted");
        result.Error.Should().Be("enemy_not_found");
    }

    // ACC:T225.9
    [Fact]
    public void ShouldKeepCombatCatalogPureCore_WhenPublicContractsAreInspected()
    {
        var catalogType = RequireAnyType("CombatCatalog", "CombatDefinitionCatalog", "CombatEncounterCatalog");
        var publicSurface = catalogType.GetMembers(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static);

        publicSurface
            .Select(member => member.DeclaringType?.Assembly.GetReferencedAssemblies().Select(reference => reference.Name) ?? Array.Empty<string>())
            .SelectMany(referenceNames => referenceNames)
            .Should()
            .NotContain("GodotSharp");
    }

    // ACC:T225.10
    [Fact]
    public void ShouldProvideDeterministicEnemyLookup_WhenCatalogContainsMultipleDefinitions()
    {
        var resolver = new CombatCatalogResolver();

        var first = resolver.Resolve("enemy_bandit_scout", "Enemy");
        var second = resolver.Resolve("enemy_bandit_scout", "Enemy");

        first.Success.Should().BeTrue();
        second.Success.Should().BeTrue();
        second.Id.Should().Be(first.Id);
    }

    // ACC:T225.10
    [Fact]
    public void ShouldExposeValidUniqueDefaultCatalogEntries_WhenCombatCatalogIsCreated()
    {
        var catalog = new CombatCatalog(
            EnemyDefinitions: new[]
            {
                new EnemyDefinition("enemy_a", "enemy.a.name", 1),
                new EnemyDefinition("enemy_b", "enemy.b.name", 2),
            },
            Bosses: new[]
            {
                new BossDefinition("boss_a", "boss.a.name", 10),
            });

        catalog.EnemyDefinitions.Select(enemy => enemy.Id).Should().OnlyHaveUniqueItems();
        catalog.Bosses.Select(boss => boss.Id).Should().OnlyHaveUniqueItems();
        catalog.EnemyDefinitions.Should().OnlyContain(enemy => enemy.CombatRating >= 0);
        catalog.Bosses.Should().OnlyContain(boss => boss.CombatRating >= 0);
        catalog.Resolve("missing", "Enemy").Should().BeNull();
    }

    // ACC:T225.11
    [Fact]
    public void ShouldKeepExistingCombatRatingValue_WhenExtendedAttributesAreDefaulted()
    {
        var characterType = RequireType("CharacterDefinition");
        var instance = CreateInstance(characterType);

        SetIfPresent(instance, "CombatRating", 7);
        SetDefaultNumericIfPresent(instance, "Attack");
        SetDefaultNumericIfPresent(instance, "Defense");
        SetDefaultNumericIfPresent(instance, "Health");

        ReadNumericProperty(instance, "CombatRating").Should().Be(7);
    }

    // ACC:T225.12
    [Fact]
    public void ShouldExposeCombatAttributesAsNumericValues_WhenCharacterDefinitionIsInspected()
    {
        var characterType = RequireType("CharacterDefinition");

        foreach (var propertyName in new[] { "Attack", "Defense", "Health", "Morale" })
        {
            var property = characterType.GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
            property.Should().NotBeNull();
            IsNumericType(property!.PropertyType).Should().BeTrue($"{propertyName} must be numeric for deterministic core validation");
        }
    }

    // ACC:T225.13
    [Fact]
    public void ShouldExposeResolvableCatalogIdentity_WhenEnemyAndBossDefinitionsAreInspected()
    {
        var enemyType = RequireAnyType("CombatEnemyDefinition", "EnemyCombatDefinition", "EnemyDefinition");
        var bossType = RequireAnyType("CombatBossDefinition", "BossCombatDefinition", "BossDefinition");

        GetPublicPropertyNames(enemyType).Should().Contain(name => IsCatalogIdentityName(name));
        GetPublicPropertyNames(bossType).Should().Contain(name => IsCatalogIdentityName(name));
    }

    // ACC:T225.14
    [Fact]
    public void ShouldPreserveRelevantExistingContracts_WhenCombatCatalogChangesAreRefactored()
    {
        var characterType = RequireType("CharacterDefinition");
        var catalogType = RequireAnyType("CombatCatalog", "CombatDefinitionCatalog", "CombatEncounterCatalog");

        characterType.GetProperty("CombatRating", BindingFlags.Public | BindingFlags.Instance).Should().NotBeNull();
        catalogType.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
            .Should()
            .Contain(method => method.Name.Contains("Resolve", StringComparison.OrdinalIgnoreCase));
    }

    private static Type RequireType(string typeName)
    {
        var type = FindType(typeName);
        type.Should().NotBeNull($"{typeName} must exist in Game.Core for Task 225 combat behavior");
        return type!;
    }

    private static Type RequireAnyType(params string[] typeNames)
    {
        var type = typeNames.Select(FindType).FirstOrDefault(candidate => candidate is not null);
        type.Should().NotBeNull($"one of {string.Join(", ", typeNames)} must exist in Game.Core for Task 225 combat behavior");
        return type!;
    }

    private static Type? FindType(string typeName)
    {
        TryLoadAssembly("Game.Core");

        return AppDomain.CurrentDomain.GetAssemblies()
            .Where(assembly => !assembly.IsDynamic)
            .SelectMany(GetTypesSafely)
            .FirstOrDefault(type => type.Name.Equals(typeName, StringComparison.Ordinal));
    }

    private static void TryLoadAssembly(string assemblyName)
    {
        try
        {
            Assembly.Load(assemblyName);
        }
        catch
        {
            // The test host may already have loaded the assembly through project references.
        }
    }

    private static IEnumerable<Type> GetTypesSafely(Assembly assembly)
    {
        try
        {
            return assembly.GetTypes();
        }
        catch (ReflectionTypeLoadException exception)
        {
            return exception.Types.Where(type => type is not null)!;
        }
    }

    private static object CreateInstance(Type type)
    {
        var instance = Activator.CreateInstance(type, nonPublic: true);
        instance.Should().NotBeNull($"{type.Name} must be constructible for deterministic core tests");
        return instance!;
    }

    private static IReadOnlyCollection<string> GetPublicPropertyNames(Type type)
    {
        return type.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
            .Select(property => property.Name)
            .ToArray();
    }

    private static IReadOnlyCollection<string> GetPublicMemberNames(Type type)
    {
        return type.GetMembers(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
            .Select(member => member.Name)
            .ToArray();
    }

    private static void SetIfPresent(object instance, string propertyName, object value)
    {
        var property = instance.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        if (property is null || !property.CanWrite)
        {
            return;
        }

        property.SetValue(instance, Convert.ChangeType(value, Nullable.GetUnderlyingType(property.PropertyType) ?? property.PropertyType));
    }

    private static void SetDefaultNumericIfPresent(object instance, string propertyName)
    {
        var property = instance.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        if (property is null || !property.CanWrite || !IsNumericType(property.PropertyType))
        {
            return;
        }

        property.SetValue(instance, Convert.ChangeType(0, Nullable.GetUnderlyingType(property.PropertyType) ?? property.PropertyType));
    }

    private static int ReadNumericProperty(object instance, string propertyName)
    {
        var property = instance.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        property.Should().NotBeNull($"{propertyName} must remain available");
        var value = property!.GetValue(instance);
        value.Should().NotBeNull($"{propertyName} must have a readable value");
        return Convert.ToInt32(value);
    }

    private static object? InvokeBestResolveMethod(object resolver, string referenceId, string targetKind)
    {
        var methods = resolver.GetType()
            .GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
            .Where(method => method.Name.Contains("Resolve", StringComparison.OrdinalIgnoreCase))
            .OrderByDescending(method => method.GetParameters().Length)
            .ToArray();

        methods.Should().NotBeEmpty("combat reference resolution must be exposed through a public core API");

        foreach (var method in methods)
        {
            var parameters = method.GetParameters();
            var args = new object?[parameters.Length];
            var canInvoke = true;

            for (var index = 0; index < parameters.Length; index++)
            {
                var parameter = parameters[index];
                if (parameter.ParameterType == typeof(string))
                {
                    args[index] = parameter.Name?.Contains("kind", StringComparison.OrdinalIgnoreCase) == true ||
                        parameter.Name?.Contains("target", StringComparison.OrdinalIgnoreCase) == true
                        ? targetKind
                        : referenceId;
                }
                else if (parameter.HasDefaultValue)
                {
                    args[index] = parameter.DefaultValue;
                }
                else
                {
                    canInvoke = false;
                    break;
                }
            }

            if (!canInvoke)
            {
                continue;
            }

            try
            {
                return method.Invoke(resolver, args);
            }
            catch (TargetInvocationException exception)
            {
                return exception.InnerException;
            }
        }

        return null;
    }

    private static bool IsFailedResolution(object? result)
    {
        if (result is null)
        {
            return true;
        }

        if (result is Exception)
        {
            return true;
        }

        var resultType = result.GetType();
        var successProperty = resultType.GetProperty("Success") ?? resultType.GetProperty("IsSuccess") ?? resultType.GetProperty("Resolved");
        if (successProperty?.PropertyType == typeof(bool))
        {
            return (bool)successProperty.GetValue(result)! == false;
        }

        var errorProperty = resultType.GetProperty("Error") ?? resultType.GetProperty("ErrorMessage") ?? resultType.GetProperty("FailureReason");
        if (errorProperty?.GetValue(result) is string error)
        {
            return !string.IsNullOrWhiteSpace(error);
        }

        return false;
    }

    private static string? NormalizeResolutionId(object? result)
    {
        if (result is null)
        {
            return null;
        }

        var resultType = result.GetType();
        var idProperty = resultType.GetProperty("Id") ?? resultType.GetProperty("DefinitionId") ?? resultType.GetProperty("CatalogId");
        return idProperty?.GetValue(result)?.ToString() ?? result.ToString();
    }

    private static bool IsNumericType(Type type)
    {
        var targetType = Nullable.GetUnderlyingType(type) ?? type;
        return targetType == typeof(byte) ||
            targetType == typeof(short) ||
            targetType == typeof(int) ||
            targetType == typeof(long) ||
            targetType == typeof(float) ||
            targetType == typeof(double) ||
            targetType == typeof(decimal);
    }

    private static bool IsCatalogIdentityName(string name)
    {
        return string.Equals(name, "Id", StringComparison.Ordinal) ||
            string.Equals(name, "DefinitionId", StringComparison.Ordinal) ||
            string.Equals(name, "CatalogId", StringComparison.Ordinal);
    }

    private static SanguoRandomEventsCatalog LoadRandomEventsCatalogFromData()
    {
        var json = File.ReadAllText(Path.Combine(FindRepoRoot(), "Data", "random_events.json"));
        var catalog = JsonSerializer.Deserialize<SanguoRandomEventsCatalog>(json, JsonOptions);
        catalog.Should().NotBeNull();
        return catalog!;
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json")))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found.");
    }
}
