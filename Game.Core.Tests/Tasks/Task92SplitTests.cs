using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using FluentAssertions;
using Game.Core.Services.Sanguo;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task92SplitTests
{
    private const int TaskId = 92;

    private static readonly string[] ViewFiles =
    {
        "tasks_back.json",
        "tasks_gameplay.json",
    };

    private static readonly string[] ExpectedMandatoryAccIds =
    {
        "A-008",
        "A-009",
        "A-010",
        "A-011",
        "A-012",
    };

    // ACC:T92.1
    [Fact]
    [Trait("acceptance", "ACC:T92.1")]
    public void ShouldKeepTaskSpecificDeterministicEvidence_WhenReadingTask92FromTaskViews()
    {
        var repoRoot = FindRepoRoot();

        foreach (var viewFile in ViewFiles)
        {
            var task = GetTaskByTaskmasterId(repoRoot, viewFile, TaskId);
            var acceptanceRefs = ReadStringArray(task, "acceptanceRefs");
            var acceptance = ReadStringArray(task, "acceptance");
            var testRefs = ReadStringArray(task, "test_refs");

            acceptanceRefs.Should().Equal("A-008~A-012");
            acceptance.Should().HaveCount(1);
            acceptance[0].Should().Contain("UI assertion gate runner");
            acceptance[0].Should().Contain("A-008~A-012");
            acceptance[0].Should().Contain("Game.Core.Tests/Tasks/Task92SplitTests.cs");
            testRefs.Should().Contain("Game.Core.Tests/Tasks/Task92SplitTests.cs");
        }
    }

    // ACC:T92.1
    [Fact]
    [Trait("acceptance", "ACC:T92.1")]
    public void ShouldRegisterOnlyA008ToA012MandatoryUnits_WhenEnumeratingUiAssertionGateRunner()
    {
        var runnerType = ResolveUiAssertionGateRunnerType();
        var gateUnits = ReadGateUnits(runnerType);

        var mandatoryAccIds = gateUnits
            .Where(static unit => unit.IsMandatory)
            .Select(static unit => unit.AccId)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static id => id, StringComparer.Ordinal)
            .ToArray();

        mandatoryAccIds.Should().Equal(
            ExpectedMandatoryAccIds,
            "task 92 split scope is UI assertion gate only and must stay within A-008~A-012.");
    }

    // ACC:T92.1
    [Fact]
    [Trait("acceptance", "ACC:T92.1")]
    public void ShouldRejectOutOfScopeMandatoryUnits_WhenValidatingUiSplitScope()
    {
        var simulatedGateUnits = new[]
        {
            new GateUnitSnapshot("A-008", true),
            new GateUnitSnapshot("A-099", true),
            new GateUnitSnapshot("A-011", true),
        };

        var simulatedOutOfScopeIds = FindOutOfScopeMandatoryIds(simulatedGateUnits);
        simulatedOutOfScopeIds.Should().ContainSingle().Which.Should().Be("A-099");

        var runnerType = ResolveUiAssertionGateRunnerType();
        var actualGateUnits = ReadGateUnits(runnerType);
        var actualOutOfScopeIds = FindOutOfScopeMandatoryIds(actualGateUnits);

        actualOutOfScopeIds.Should().BeEmpty(
            "UI assertion runner must not register mandatory gate units outside A-008~A-012.");
    }

    // ACC:T92.1
    [Fact]
    [Trait("acceptance", "ACC:T92.1")]
    public void ShouldReturnFailSummary_WhenRunningUiAssertionGateWithForcedFailure()
    {
        var runnerType = ResolveUiAssertionGateRunnerType();
        var runResult = RunWithForcedFailures(runnerType, "A-008");

        var exitCode = ReadRequiredProperty<int>(runResult, "ExitCode");
        var status = ReadRequiredProperty<string>(runResult, "Status");
        var summaryJson = ReadRequiredProperty<string>(runResult, "MachineReadableSummaryJson");

        exitCode.Should().NotBe(0, "runner must fail when any required UI assertion fails.");
        status.Should().Be("fail");
        summaryJson.Should().NotBeNullOrWhiteSpace();

        using var summaryDoc = JsonDocument.Parse(summaryJson);
        var root = summaryDoc.RootElement;
        root.GetProperty("status").GetString().Should().Be("fail");
        root.GetProperty("exit_code").GetInt32().Should().Be(exitCode);

        var records = root.GetProperty("records").EnumerateArray().ToArray();
        records.Should().NotBeEmpty();
        records.Should().Contain(record =>
            string.Equals(record.GetProperty("acc_id").GetString(), "A-008", StringComparison.Ordinal) &&
            string.Equals(record.GetProperty("state").GetString(), "fail", StringComparison.OrdinalIgnoreCase));

        var mandatoryAccIds = records
            .Where(record => record.TryGetProperty("mandatory", out var mandatory) && mandatory.GetBoolean())
            .Select(record => record.GetProperty("acc_id").GetString() ?? string.Empty)
            .Where(static accId => !string.IsNullOrWhiteSpace(accId))
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static accId => accId, StringComparer.Ordinal)
            .ToArray();

        mandatoryAccIds.Should().Equal(
            ExpectedMandatoryAccIds,
            "task 92 split completion evidence must remain scoped to A-008~A-012 mandatory records.");
    }

    // ACC:T92.1
    [Fact]
    [Trait("acceptance", "ACC:T92.1")]
    public void ShouldReturnOkSummary_WhenRunningUiAssertionGateWithoutForcedFailure()
    {
        var runnerType = ResolveUiAssertionGateRunnerType();
        var runResult = RunWithForcedFailures(runnerType, Array.Empty<string>());

        var exitCode = ReadRequiredProperty<int>(runResult, "ExitCode");
        var status = ReadRequiredProperty<string>(runResult, "Status");
        var summaryJson = ReadRequiredProperty<string>(runResult, "MachineReadableSummaryJson");

        exitCode.Should().Be(0);
        status.Should().Be("ok");
        summaryJson.Should().NotBeNullOrWhiteSpace();

        using var summaryDoc = JsonDocument.Parse(summaryJson);
        var root = summaryDoc.RootElement;
        root.GetProperty("status").GetString().Should().Be("ok");
        root.GetProperty("exit_code").GetInt32().Should().Be(exitCode);

        var records = root.GetProperty("records").EnumerateArray().ToArray();
        records.Should().NotBeEmpty();

        var mandatoryRecords = records
            .Where(record => record.TryGetProperty("mandatory", out var mandatory) && mandatory.GetBoolean())
            .ToArray();
        mandatoryRecords.Should().NotBeEmpty();
        mandatoryRecords.Should().OnlyContain(record =>
            string.Equals(record.GetProperty("state").GetString(), "pass", StringComparison.OrdinalIgnoreCase));

        var mandatoryAccIds = mandatoryRecords
            .Select(record => record.GetProperty("acc_id").GetString() ?? string.Empty)
            .Where(static accId => !string.IsNullOrWhiteSpace(accId))
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static accId => accId, StringComparer.Ordinal)
            .ToArray();

        mandatoryAccIds.Should().Equal(ExpectedMandatoryAccIds);
    }

    private static IReadOnlyList<GateUnitSnapshot> ReadGateUnits(Type runnerType)
    {
        var getRequiredGateUnitsMethod = runnerType.GetMethod(
            "GetRequiredGateUnits",
            BindingFlags.Public | BindingFlags.Static,
            binder: null,
            types: Type.EmptyTypes,
            modifiers: null);

        getRequiredGateUnitsMethod.Should().NotBeNull(
            "task 92 split must expose GetRequiredGateUnits() for deterministic gate coverage.");

        var rawGateUnits = getRequiredGateUnitsMethod!.Invoke(null, parameters: null);
        rawGateUnits.Should().NotBeNull();
        rawGateUnits.Should().BeAssignableTo<IEnumerable>();

        var gateUnits = new List<GateUnitSnapshot>();
        foreach (var unit in (IEnumerable)rawGateUnits!)
        {
            unit.Should().NotBeNull();
            var accId = ReadRequiredProperty<string>(unit!, "AccId");
            var isMandatory = ReadRequiredProperty<bool>(unit!, "IsMandatory");
            gateUnits.Add(new GateUnitSnapshot(accId, isMandatory));
        }

        gateUnits.Should().NotBeEmpty("UI assertion gate runner must enumerate auditable gate units.");
        return gateUnits;
    }

    private static object RunWithForcedFailures(Type runnerType, params string[] failingAccIds)
    {
        var runWithForcedFailuresMethod = runnerType
            .GetMethods(BindingFlags.Public | BindingFlags.Static)
            .FirstOrDefault(method =>
            {
                if (!string.Equals(method.Name, "RunWithForcedFailures", StringComparison.Ordinal))
                {
                    return false;
                }

                var parameters = method.GetParameters();
                return parameters.Length == 1 &&
                       parameters[0].ParameterType.IsAssignableFrom(typeof(string[]));
            });

        runWithForcedFailuresMethod.Should().NotBeNull(
            "task 92 split must expose RunWithForcedFailures(IEnumerable<string>) for deterministic failure evidence.");

        var result = runWithForcedFailuresMethod!.Invoke(null, new object[] { failingAccIds });
        result.Should().NotBeNull();
        return result!;
    }

    private static Type ResolveUiAssertionGateRunnerType()
    {
        var coreAssembly = typeof(CoreAssertionGateRunner).Assembly;

        var candidate = coreAssembly.GetType("Game.Core.Services.Sanguo.UiAssertionGateRunner", throwOnError: false, ignoreCase: false)
                        ?? coreAssembly.GetType("Game.Core.Services.Sanguo.UIAssertionGateRunner", throwOnError: false, ignoreCase: false)
                        ?? GetLoadableTypes(coreAssembly).FirstOrDefault(type =>
                            string.Equals(type.Name, "UiAssertionGateRunner", StringComparison.Ordinal) ||
                            string.Equals(type.Name, "UIAssertionGateRunner", StringComparison.Ordinal));

        candidate.Should().NotBeNull(
            "task 92 split must explicitly implement a dedicated UI assertion gate runner for A-008~A-012.");

        return candidate!;
    }

    private static IReadOnlyList<Type> GetLoadableTypes(Assembly assembly)
    {
        try
        {
            return assembly.GetTypes();
        }
        catch (ReflectionTypeLoadException ex)
        {
            return ex.Types.Where(static type => type is not null).Cast<Type>().ToArray();
        }
    }

    private static string[] FindOutOfScopeMandatoryIds(IEnumerable<GateUnitSnapshot> gateUnits)
    {
        var allowedAccIds = new HashSet<string>(ExpectedMandatoryAccIds, StringComparer.Ordinal);
        return gateUnits
            .Where(unit => unit.IsMandatory && !allowedAccIds.Contains(unit.AccId))
            .Select(static unit => unit.AccId)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(static id => id, StringComparer.Ordinal)
            .ToArray();
    }

    private static T ReadRequiredProperty<T>(object source, string propertyName)
    {
        var property = source.GetType().GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance);
        property.Should().NotBeNull(
            $"Instance of type {source.GetType().FullName} must expose '{propertyName}' for deterministic split evidence.");

        var value = property!.GetValue(source);
        value.Should().NotBeNull($"Property '{propertyName}' must not be null.");
        value.Should().BeAssignableTo<T>();

        return (T)value!;
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            var marker = Path.Combine(dir.FullName, ".taskmaster", "tasks", "tasks.json");
            if (File.Exists(marker))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException("Repo root not found (missing .taskmaster/tasks/tasks.json).");
    }

    private static JsonElement GetTaskByTaskmasterId(string repoRoot, string fileName, int taskmasterId)
    {
        using var doc = LoadJson(repoRoot, ".taskmaster", "tasks", fileName);
        foreach (var task in doc.RootElement.EnumerateArray())
        {
            if (task.TryGetProperty("taskmaster_id", out var idProperty) &&
                idProperty.ValueKind == JsonValueKind.Number &&
                idProperty.TryGetInt32(out var idValue) &&
                idValue == taskmasterId)
            {
                return task.Clone();
            }
        }

        throw new InvalidOperationException($"Task {taskmasterId} not found in {fileName}.");
    }

    private static string[] ReadStringArray(JsonElement task, string propertyName)
    {
        task.TryGetProperty(propertyName, out var property)
            .Should().BeTrue($"Task {TaskId} must contain '{propertyName}'.");

        property.ValueKind.Should().Be(JsonValueKind.Array);

        return property
            .EnumerateArray()
            .Select(static item => item.GetString() ?? string.Empty)
            .ToArray();
    }

    private static JsonDocument LoadJson(string repoRoot, params string[] relativeParts)
    {
        var path = Path.Combine(new[] { repoRoot }.Concat(relativeParts).ToArray());
        using var stream = File.OpenRead(path);
        return JsonDocument.Parse(stream);
    }

    private readonly record struct GateUnitSnapshot(string AccId, bool IsMandatory);
}
