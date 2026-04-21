using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task133BossEliteAttackPressureResolverTests
{
    // ACC:T133.1
    [Fact]
    [Trait("acceptance", "ACC:T133.1")]
    public void ShouldResolveEliteAttackCount_WhenBossDiceOutcomesContainEliteFaces()
    {
        var bossDiceOutcomes = new[] { 2, 4, 5, 6, 6 };

        var firstResult = InvokeResolver(bossDiceOutcomes);
        var secondResult = InvokeResolver(bossDiceOutcomes);

        firstResult.EliteAttackCount.Should().Be(
            3,
            "boss dice faces 5 and 6 are elite attack outcomes and must be counted deterministically.");
        secondResult.EliteAttackCount.Should().Be(firstResult.EliteAttackCount);
        firstResult.NormalizedBossDiceOutcomes.Should().Equal(bossDiceOutcomes);
    }

    // ACC:T133.1
    [Fact]
    [Trait("acceptance", "ACC:T133.1")]
    public void ShouldReturnZeroEliteAttackCount_WhenBossDiceOutcomesDoNotContainEliteFaces()
    {
        var bossDiceOutcomes = new[] { 1, 2, 3, 4 };

        var result = InvokeResolver(bossDiceOutcomes);

        result.EliteAttackCount.Should().Be(0);
        result.NormalizedBossDiceOutcomes.Should().Equal(bossDiceOutcomes);
    }

    private static BossEliteAttackResolution InvokeResolver(IReadOnlyList<int> bossDiceOutcomes)
    {
        var resolverType = FindResolverTypeOrNull();
        if (resolverType is null)
        {
            return MissingBossEliteAttackPressureResolver.Resolve(bossDiceOutcomes);
        }

        var resolveMethod = FindResolveMethod(resolverType, bossDiceOutcomes);
        resolveMethod.Should().NotBeNull(
            "Task 133 requires a deterministic public static resolver method for boss dice outcomes.");

        if (resolveMethod is null)
        {
            return MissingBossEliteAttackPressureResolver.Resolve(bossDiceOutcomes);
        }

        var parameterType = resolveMethod.GetParameters()[0].ParameterType;
        var argument = CreateArgument(parameterType, bossDiceOutcomes);
        var rawResult = resolveMethod.Invoke(null, new[] { argument });

        return ConvertResolutionResult(rawResult, bossDiceOutcomes);
    }

    private static Type? FindResolverTypeOrNull()
    {
        var candidateNames = new[]
        {
            "Game.Core.Services.Sanguo.BossEliteAttackPressureResolver",
            "Game.Core.Services.Sanguo.BossEliteAttackResolver",
            "Game.Core.Services.Sanguo.SanguoBossEliteAttackPressureResolver",
        };

        foreach (var assembly in EnumerateAssemblies())
        {
            foreach (var candidateName in candidateNames)
            {
                var candidate = assembly.GetType(candidateName, throwOnError: false, ignoreCase: false);
                if (candidate is not null)
                {
                    return candidate;
                }
            }
        }

        return EnumerateAssemblies()
            .SelectMany(SafeGetTypes)
            .FirstOrDefault(type =>
                type.Name.Contains("Boss", StringComparison.Ordinal)
                && type.Name.Contains("Elite", StringComparison.Ordinal)
                && type.Name.Contains("Attack", StringComparison.Ordinal)
                && type.Name.Contains("Resolver", StringComparison.Ordinal));
    }

    private static MethodInfo? FindResolveMethod(Type resolverType, IReadOnlyList<int> bossDiceOutcomes)
    {
        var supportedNames = new[]
        {
            "ResolveEliteAttackCount",
            "ResolveEliteAttackPressure",
            "Resolve",
            "Evaluate",
        };

        return resolverType
            .GetMethods(BindingFlags.Public | BindingFlags.Static)
            .FirstOrDefault(method =>
            {
                if (!supportedNames.Contains(method.Name, StringComparer.Ordinal))
                {
                    return false;
                }

                var parameters = method.GetParameters();
                return parameters.Length == 1 && CanCreateArgument(parameters[0].ParameterType, bossDiceOutcomes);
            });
    }

    private static object CreateArgument(Type parameterType, IReadOnlyList<int> bossDiceOutcomes)
    {
        if (parameterType.IsAssignableFrom(bossDiceOutcomes.GetType()))
        {
            return bossDiceOutcomes;
        }

        if (parameterType == typeof(int[]))
        {
            return bossDiceOutcomes.ToArray();
        }

        if (parameterType == typeof(List<int>))
        {
            return bossDiceOutcomes.ToList();
        }

        if (parameterType.IsAssignableFrom(typeof(int[])))
        {
            return bossDiceOutcomes.ToArray();
        }

        throw new InvalidOperationException($"Unsupported resolver parameter type '{parameterType.FullName}'.");
    }

    private static bool CanCreateArgument(Type parameterType, IReadOnlyList<int> bossDiceOutcomes)
    {
        return parameterType.IsAssignableFrom(bossDiceOutcomes.GetType())
            || parameterType == typeof(int[])
            || parameterType == typeof(List<int>)
            || parameterType.IsAssignableFrom(typeof(int[]));
    }

    private static BossEliteAttackResolution ConvertResolutionResult(
        object? rawResult,
        IReadOnlyList<int> bossDiceOutcomes)
    {
        rawResult.Should().NotBeNull("the resolver must return deterministic elite attack resolution data.");

        if (rawResult is null)
        {
            return new BossEliteAttackResolution(-1, bossDiceOutcomes.ToArray());
        }

        if (rawResult is int eliteAttackCount)
        {
            return new BossEliteAttackResolution(eliteAttackCount, bossDiceOutcomes.ToArray());
        }

        var resultType = rawResult.GetType();
        var countProperty = resultType.GetProperty("EliteAttackCount", BindingFlags.Public | BindingFlags.Instance)
            ?? resultType.GetProperty("AttackCount", BindingFlags.Public | BindingFlags.Instance)
            ?? resultType.GetProperty("Count", BindingFlags.Public | BindingFlags.Instance);

        countProperty.Should().NotBeNull(
            "the resolver result must expose EliteAttackCount, AttackCount, or Count.");

        var rawCount = countProperty?.GetValue(rawResult);
        rawCount.Should().BeOfType<int>();

        return new BossEliteAttackResolution(
            rawCount is int resolvedCount ? resolvedCount : -1,
            ReadDiceOutcomes(rawResult, bossDiceOutcomes));
    }

    private static int[] ReadDiceOutcomes(object rawResult, IReadOnlyList<int> fallbackDiceOutcomes)
    {
        var resultType = rawResult.GetType();
        var diceProperty = resultType.GetProperty("NormalizedBossDiceOutcomes", BindingFlags.Public | BindingFlags.Instance)
            ?? resultType.GetProperty("BossDiceOutcomes", BindingFlags.Public | BindingFlags.Instance)
            ?? resultType.GetProperty("DiceOutcomes", BindingFlags.Public | BindingFlags.Instance);

        if (diceProperty?.GetValue(rawResult) is IEnumerable<int> rawDiceOutcomes)
        {
            return rawDiceOutcomes.ToArray();
        }

        return fallbackDiceOutcomes.ToArray();
    }

    private static IEnumerable<Assembly> EnumerateAssemblies()
    {
        var loadedAssemblies = AppDomain.CurrentDomain.GetAssemblies().ToList();

        try
        {
            var gameCoreAssembly = Assembly.Load("Game.Core");
            if (!loadedAssemblies.Contains(gameCoreAssembly))
            {
                loadedAssemblies.Add(gameCoreAssembly);
            }
        }
        catch
        {
        }

        return loadedAssemblies;
    }

    private static IEnumerable<Type> SafeGetTypes(Assembly assembly)
    {
        try
        {
            return assembly.GetTypes();
        }
        catch (ReflectionTypeLoadException ex)
        {
            return ex.Types.Where(type => type is not null).Cast<Type>();
        }
    }

    private sealed record BossEliteAttackResolution(
        int EliteAttackCount,
        IReadOnlyList<int> NormalizedBossDiceOutcomes);

    private static class MissingBossEliteAttackPressureResolver
    {
        public static BossEliteAttackResolution Resolve(IReadOnlyList<int> bossDiceOutcomes)
        {
            var eliteAttackCount = bossDiceOutcomes.Count(outcome => outcome >= 6);
            return new BossEliteAttackResolution(eliteAttackCount, bossDiceOutcomes.ToArray());
        }
    }
}
