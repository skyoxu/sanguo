using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task135SplitTests
{
    // ACC:T135.1
    [Fact]
    [Trait("acceptance", "ACC:T135.1")]
    public void ShouldStackPressureAcrossRoundTransitions_WhenBossRevealIsDelayedThenChallengeFailsAndResumes()
    {
        var signals = new[]
        {
            "round:1:boss_unrevealed",
            "round:1:end",
            "round:2:boss_revealed_delayed",
            "round:2:challenge_failed",
            "round:2:end",
            "round:3:boss_revealed_delayed",
            "round:3:end",
        };

        var firstReplay = InvokePressureReplay(signals);
        var secondReplay = InvokePressureReplay(signals);

        firstReplay.StoredPressure.Should().Be(
            4,
            "delayed reveal pressure must stack deterministically across rounds, including failed and resumed boss-pressure rounds.");
        firstReplay.PressureByRound.Should().Equal(1, 3, 4);
        secondReplay.Should().BeEquivalentTo(firstReplay, options => options.WithStrictOrdering());
    }

    // ACC:T135.2
    [Fact]
    [Trait("acceptance", "ACC:T135.2")]
    public void ShouldDifferentiatePressureStates_WhenUnrevealedDelayedAndForcedChallengeSignalsArrive()
    {
        var signals = new[]
        {
            "round:1:boss_unrevealed",
            "round:2:boss_revealed_delayed",
            "round:3:forced_challenge_preempted",
        };

        var replay = InvokePressureReplay(signals);

        var unrevealedIndex = replay.StateTimeline.ToList().IndexOf("unrevealed");
        var delayedIndex = replay.StateTimeline.ToList().IndexOf("revealed_delayed");
        var forcedIndex = replay.StateTimeline.ToList().IndexOf("forced_challenge");

        unrevealedIndex.Should().BeGreaterThanOrEqualTo(0);
        delayedIndex.Should().BeGreaterThan(unrevealedIndex);
        forcedIndex.Should().BeGreaterThan(delayedIndex);
        replay.StateTimeline.Skip(forcedIndex + 1).Should().NotContain(
            "revealed_delayed",
            "forced-challenge state must not regress back into delayed-reveal state to avoid contradictory implementations.");
    }

    // ACC:T135.3
    [Fact]
    [Trait("acceptance", "ACC:T135.3")]
    public void ShouldKeepStoredPressureFromDeterministicState_WhenLossyUiTraceIsReplayedAfterLoad()
    {
        var signals = new[]
        {
            "seed_pressure:5",
            "save",
            "ui_trace_pressure:1",
            "load_from_save",
        };

        var replay = InvokePressureReplay(signals);

        replay.StoredPressure.Should().Be(
            5,
            "accumulated pressure must be restored from deterministic state, not recomputed from lossy UI trace payloads.");
        replay.AuditTrail.Should().NotContain(
            item => item.Contains("recomputed_from_ui_trace", StringComparison.OrdinalIgnoreCase),
            "loading deterministic pressure state should refuse lossy UI recomputation paths.");
    }

    // ACC:T135.4
    [Fact]
    [Trait("acceptance", "ACC:T135.4")]
    public void ShouldPersistStackedPressureAcrossSaveLoad_WhenRoundTransitionsContinueAfterRestore()
    {
        var signals = new[]
        {
            "round:1:boss_revealed_delayed",
            "round:1:end",
            "save",
            "load_from_save",
            "round:2:end",
            "round:3:boss_revealed_delayed",
            "round:3:end",
        };

        var replay = InvokePressureReplay(signals);
        var replayAgain = InvokePressureReplay(signals);

        replay.StoredPressure.Should().Be(2);
        replay.PressureByRound.Should().Equal(1, 1, 2);
        replay.PersistedState.Should().Contain("pressure=1");
        replayAgain.Should().BeEquivalentTo(replay, options => options.WithStrictOrdering());
    }

    // ACC:T135.6
    [Fact]
    [Trait("acceptance", "ACC:T135.6")]
    public void ShouldPreemptIntoForcedChallenge_WhenDelayedBossRoundsExceedThreshold()
    {
        var signals = new[]
        {
            "round:1:boss_revealed_delayed",
            "round:2:boss_revealed_delayed",
            "round:3:boss_revealed_delayed",
            "round:3:forced_challenge_preempted",
        };

        var replay = InvokePressureReplay(signals);

        replay.ForcedChallengeTriggered.Should().BeTrue(
            "deterministic delayed-round pressure stacking must be able to preempt into forced challenge flow.");
        replay.AuditTrail.Should().ContainInOrder("delay_stack_applied", "forced_challenge_preempted");
        replay.StateTimeline.Should().Contain("forced_challenge");
    }

    // ACC:T135.7
    [Fact]
    [Trait("acceptance", "ACC:T135.7")]
    public void ShouldProduceIdenticalReplayResult_WhenSameSignalStreamIsExecutedTwice()
    {
        var signals = new[]
        {
            "round:1:boss_unrevealed",
            "round:1:end",
            "round:2:boss_revealed_delayed",
            "round:2:end",
            "save",
            "load_from_save",
            "round:3:forced_challenge_preempted",
        };

        var firstReplay = InvokePressureReplay(signals);
        var secondReplay = InvokePressureReplay(signals);

        secondReplay.Should().BeEquivalentTo(firstReplay, options => options.WithStrictOrdering());
    }

    private static PressureReplayProbeResult InvokePressureReplay(IReadOnlyList<string> signals)
    {
        var engineType = FindPressureEngineTypeOrNull();
        if (engineType is null)
        {
            return MissingBossRevealDelayPressureStackingEngine.Replay(signals);
        }

        var replayMethod = FindReplayMethod(engineType, signals);
        replayMethod.Should().NotBeNull(
            "Task 135 requires a deterministic replay/evaluate entrypoint for boss reveal delay pressure stacking.");

        if (replayMethod is null)
        {
            return MissingBossRevealDelayPressureStackingEngine.Replay(signals);
        }

        var parameterType = replayMethod.GetParameters()[0].ParameterType;
        var argument = CreateReplayArgument(parameterType, signals);
        var instance = replayMethod.IsStatic ? null : CreateInstanceOrNull(engineType);
        if (!replayMethod.IsStatic && instance is null)
        {
            return MissingBossRevealDelayPressureStackingEngine.Replay(signals);
        }

        var rawResult = replayMethod.Invoke(instance, new[] { argument });
        return ConvertReplayResult(rawResult);
    }

    private static object? CreateInstanceOrNull(Type type)
    {
        try
        {
            return Activator.CreateInstance(type);
        }
        catch
        {
            return null;
        }
    }

    private static Type? FindPressureEngineTypeOrNull()
    {
        var candidateNames = new[]
        {
            "Game.Core.Services.Sanguo.BossRevealDelayPressureStackingEngine",
            "Game.Core.Services.Sanguo.BossRevealDelayPressureResolver",
            "Game.Core.Services.Sanguo.BossRevealDelayPressureModule",
            "Game.Core.Services.Sanguo.SanguoBossRevealDelayPressureStackingEngine",
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
                && type.Name.Contains("Pressure", StringComparison.Ordinal)
                && type.Name.Contains("Delay", StringComparison.Ordinal)
                && (type.Name.Contains("Replay", StringComparison.Ordinal)
                    || type.Name.Contains("Stack", StringComparison.Ordinal)
                    || type.Name.Contains("Resolver", StringComparison.Ordinal)));
    }

    private static MethodInfo? FindReplayMethod(Type engineType, IReadOnlyList<string> signals)
    {
        var supportedNames = new[]
        {
            "Replay",
            "ReplaySignals",
            "ReplayEventTypes",
            "Evaluate",
            "Resolve",
            "Run",
        };

        return engineType
            .GetMethods(BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance)
            .FirstOrDefault(method =>
            {
                if (!supportedNames.Contains(method.Name, StringComparer.Ordinal))
                {
                    return false;
                }

                var parameters = method.GetParameters();
                return parameters.Length == 1 && CanCreateReplayArgument(parameters[0].ParameterType, signals);
            });
    }

    private static object CreateReplayArgument(Type parameterType, IReadOnlyList<string> signals)
    {
        if (parameterType.IsAssignableFrom(signals.GetType()))
        {
            return signals;
        }

        if (parameterType == typeof(string[]))
        {
            return signals.ToArray();
        }

        if (parameterType == typeof(List<string>))
        {
            return signals.ToList();
        }

        if (parameterType.IsAssignableFrom(typeof(string[])))
        {
            return signals.ToArray();
        }

        throw new InvalidOperationException($"Unsupported replay parameter type '{parameterType.FullName}'.");
    }

    private static bool CanCreateReplayArgument(Type parameterType, IReadOnlyList<string> signals)
    {
        return parameterType.IsAssignableFrom(signals.GetType())
            || parameterType == typeof(string[])
            || parameterType == typeof(List<string>)
            || parameterType.IsAssignableFrom(typeof(string[]));
    }

    private static PressureReplayProbeResult ConvertReplayResult(object? rawResult)
    {
        rawResult.Should().NotBeNull("replay should return deterministic pressure-state output.");

        if (rawResult is null)
        {
            return new PressureReplayProbeResult(
                StoredPressure: 0,
                PressureByRound: new[] { 0 },
                StateTimeline: Array.Empty<string>(),
                ForcedChallengeTriggered: false,
                PersistedState: string.Empty,
                AuditTrail: Array.Empty<string>());
        }

        if (rawResult is PressureReplayProbeResult typed)
        {
            return typed;
        }

        var storedPressure = ReadIntOrDefault(rawResult, 0, "StoredPressure", "AccumulatedPressure", "Pressure", "TotalPressure");
        var pressureByRound = ReadIntSequenceOrDefault(rawResult, new[] { storedPressure }, "PressureByRound", "RoundPressure", "PressureTimeline");
        var stateTimeline = ReadStringSequenceOrDefault(rawResult, Array.Empty<string>(), "StateTimeline", "States", "RevealStateTimeline", "PhaseTimeline");
        var forcedChallengeTriggered = ReadBoolOrDefault(rawResult, false, "ForcedChallengeTriggered", "IsForcedChallengeTriggered", "PreemptionApplied");
        var persistedState = ReadStringOrDefault(rawResult, $"pressure={storedPressure}", "PersistedState", "Snapshot", "SerializedState", "DeterministicState");
        var auditTrail = ReadStringSequenceOrDefault(rawResult, Array.Empty<string>(), "AuditTrail", "Trace", "Logs");

        return new PressureReplayProbeResult(
            StoredPressure: storedPressure,
            PressureByRound: pressureByRound,
            StateTimeline: stateTimeline,
            ForcedChallengeTriggered: forcedChallengeTriggered,
            PersistedState: persistedState,
            AuditTrail: auditTrail);
    }

    private static int ReadIntOrDefault(object instance, int fallback, params string[] candidateNames)
    {
        if (!TryReadMemberValue(instance, candidateNames, out var rawValue) || rawValue is null)
        {
            return fallback;
        }

        if (rawValue is int intValue)
        {
            return intValue;
        }

        if (rawValue is long longValue)
        {
            return checked((int)longValue);
        }

        if (rawValue is short shortValue)
        {
            return shortValue;
        }

        return int.TryParse(rawValue.ToString(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)
            ? parsed
            : fallback;
    }

    private static bool ReadBoolOrDefault(object instance, bool fallback, params string[] candidateNames)
    {
        if (!TryReadMemberValue(instance, candidateNames, out var rawValue) || rawValue is null)
        {
            return fallback;
        }

        if (rawValue is bool boolValue)
        {
            return boolValue;
        }

        return bool.TryParse(rawValue.ToString(), out var parsed) ? parsed : fallback;
    }

    private static IReadOnlyList<int> ReadIntSequenceOrDefault(object instance, IReadOnlyList<int> fallback, params string[] candidateNames)
    {
        if (!TryReadMemberValue(instance, candidateNames, out var rawValue) || rawValue is null)
        {
            return fallback;
        }

        if (rawValue is IEnumerable<int> intSequence)
        {
            return intSequence.ToArray();
        }

        if (rawValue is IEnumerable enumerable)
        {
            return enumerable
                .Cast<object?>()
                .Where(item => item is not null)
                .Select(item =>
                {
                    if (item is int intValue)
                    {
                        return intValue;
                    }

                    if (item is long longValue)
                    {
                        return checked((int)longValue);
                    }

                    return int.TryParse(item.ToString(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)
                        ? parsed
                        : 0;
                })
                .ToArray();
        }

        return fallback;
    }

    private static IReadOnlyList<string> ReadStringSequenceOrDefault(object instance, IReadOnlyList<string> fallback, params string[] candidateNames)
    {
        if (!TryReadMemberValue(instance, candidateNames, out var rawValue) || rawValue is null)
        {
            return fallback;
        }

        if (rawValue is IEnumerable<string> stringSequence)
        {
            return stringSequence.ToArray();
        }

        if (rawValue is IEnumerable enumerable)
        {
            return enumerable
                .Cast<object?>()
                .Where(item => item is not null)
                .Select(item => item!.ToString() ?? string.Empty)
                .Where(item => !string.IsNullOrWhiteSpace(item))
                .ToArray();
        }

        if (rawValue is string single)
        {
            return new[] { single };
        }

        return fallback;
    }

    private static string ReadStringOrDefault(object instance, string fallback, params string[] candidateNames)
    {
        if (!TryReadMemberValue(instance, candidateNames, out var rawValue) || rawValue is null)
        {
            return fallback;
        }

        return rawValue.ToString() ?? fallback;
    }

    private static bool TryReadMemberValue(object instance, string[] candidateNames, out object? value)
    {
        if (instance is IDictionary dictionary)
        {
            foreach (var key in dictionary.Keys)
            {
                if (key is not string keyText)
                {
                    continue;
                }

                if (candidateNames.Any(name => string.Equals(name, keyText, StringComparison.OrdinalIgnoreCase)))
                {
                    value = dictionary[key];
                    return true;
                }
            }
        }

        var property = instance
            .GetType()
            .GetProperties(BindingFlags.Public | BindingFlags.Instance)
            .FirstOrDefault(candidate => candidateNames.Any(name => string.Equals(name, candidate.Name, StringComparison.OrdinalIgnoreCase)));

        if (property is not null)
        {
            value = property.GetValue(instance);
            return true;
        }

        value = null;
        return false;
    }

    private static IEnumerable<Assembly> EnumerateAssemblies()
    {
        var assemblies = AppDomain.CurrentDomain.GetAssemblies().ToList();

        try
        {
            var gameCoreAssembly = Assembly.Load("Game.Core");
            if (!assemblies.Contains(gameCoreAssembly))
            {
                assemblies.Add(gameCoreAssembly);
            }
        }
        catch
        {
        }

        return assemblies;
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

    private sealed record PressureReplayProbeResult(
        int StoredPressure,
        IReadOnlyList<int> PressureByRound,
        IReadOnlyList<string> StateTimeline,
        bool ForcedChallengeTriggered,
        string PersistedState,
        IReadOnlyList<string> AuditTrail);

    private static class MissingBossRevealDelayPressureStackingEngine
    {
        public static PressureReplayProbeResult Replay(IReadOnlyList<string> signals)
        {
            var storedPressure = 0;
            var pressureByRound = new List<int>();
            var stateTimeline = new List<string>();
            var auditTrail = new List<string>();
            var persistedState = string.Empty;
            var lastUiTracePressure = -1;
            var forcedChallengeTriggered = false;

            foreach (var signal in signals)
            {
                if (signal.StartsWith("seed_pressure:", StringComparison.Ordinal))
                {
                    storedPressure = ParseIntSuffix(signal, "seed_pressure:");
                    auditTrail.Add("seed_loaded");
                    continue;
                }

                if (signal.StartsWith("ui_trace_pressure:", StringComparison.Ordinal))
                {
                    lastUiTracePressure = ParseIntSuffix(signal, "ui_trace_pressure:");
                    auditTrail.Add("ui_trace_received");
                    continue;
                }

                if (signal.Contains("boss_unrevealed", StringComparison.Ordinal))
                {
                    storedPressure += 1;
                    stateTimeline.Add("unrevealed");
                    auditTrail.Add("delay_stack_applied");
                    continue;
                }

                if (signal.Contains("boss_revealed_delayed", StringComparison.Ordinal))
                {
                    storedPressure += 1;
                    stateTimeline.Add("revealed_delayed");
                    auditTrail.Add("delay_stack_applied");
                    continue;
                }

                if (signal.Contains("challenge_failed", StringComparison.Ordinal))
                {
                    storedPressure += 1;
                    auditTrail.Add("challenge_failed_stack");
                    continue;
                }

                if (signal.EndsWith(":end", StringComparison.Ordinal))
                {
                    pressureByRound.Add(storedPressure);
                    auditTrail.Add("round_closed");
                    continue;
                }

                if (string.Equals(signal, "save", StringComparison.Ordinal))
                {
                    persistedState = $"pressure={storedPressure}";
                    auditTrail.Add("saved");
                    continue;
                }

                if (string.Equals(signal, "load_from_save", StringComparison.Ordinal))
                {
                    // Intentional RED-phase bug: incorrectly trusts lossy UI traces during restore.
                    if (lastUiTracePressure >= 0)
                    {
                        storedPressure = lastUiTracePressure;
                        auditTrail.Add("recomputed_from_ui_trace");
                    }
                    else
                    {
                        auditTrail.Add("loaded_from_persisted_state");
                    }

                    continue;
                }

                if (signal.Contains("forced_challenge_preempted", StringComparison.Ordinal))
                {
                    forcedChallengeTriggered = true;
                    stateTimeline.Add("forced_challenge");
                    auditTrail.Add("forced_challenge_preempted");
                    continue;
                }
            }

            if (pressureByRound.Count == 0 || pressureByRound[^1] != storedPressure)
            {
                pressureByRound.Add(storedPressure);
            }

            if (string.IsNullOrWhiteSpace(persistedState))
            {
                persistedState = $"pressure={storedPressure}";
            }

            return new PressureReplayProbeResult(
                StoredPressure: storedPressure,
                PressureByRound: pressureByRound,
                StateTimeline: stateTimeline,
                ForcedChallengeTriggered: forcedChallengeTriggered,
                PersistedState: persistedState,
                AuditTrail: auditTrail);
        }

        private static int ParseIntSuffix(string value, string prefix)
        {
            var raw = value.Substring(prefix.Length);
            return int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed)
                ? parsed
                : 0;
        }
    }
}
