using System;
using System.IO;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task227FreezeConflictPolicyTests
{
    private static readonly string RepositoryRoot = FindRepositoryRoot();

    // ACC:T227.1
    [Fact]
    [Trait("acceptance", "ACC:T227.1")]
    public void ShouldKeepRulesFreezeConflictClause_WhenCombatBaselineIsFrozen()
    {
        var text = ReadRepositoryFile("docs/prd/PRD_V4_RULES_FREEZE.md");

        text.Should().Contain("Any implementation that conflicts with this freeze must be treated as a bug");
        text.Should().Contain("unless superseded by a later freeze revision");
    }

    // ACC:T227.2
    [Fact]
    [Trait("acceptance", "ACC:T227.2")]
    public void ShouldRequireLaterFreezeRevision_WhenConflictIsAccepted()
    {
        var text = ReadRepositoryFile("docs/prd/PRD_V4_RULES_FREEZE.md");

        text.Should().Contain("Any rule change in sections 1-11 requires:");
        text.Should().Contain("update this freeze file");
        text.Should().Contain("provide matching implementation or task evidence");
    }

    // ACC:T227.3
    [Fact]
    [Trait("acceptance", "ACC:T227.3")]
    public void ShouldRouteFreezeConflictEvidenceThroughTaskXunit_WhenTaskRequiresDeterministicCoverage()
    {
        var type = ResolvePolicyType();

        type.Should().NotBeNull("the deterministic freeze-conflict behavior must have xUnit-covered core evidence");
        typeof(Task227FreezeConflictPolicyTests).Assembly.GetName().Name.Should().Be("Game.Core.Tests");
    }

    // ACC:T227.4
    [Fact]
    [Trait("acceptance", "ACC:T227.4")]
    public void ShouldKeepFreezeConflictImplementationInPureCore_WhenPolicyIsImplemented()
    {
        var type = ResolvePolicyType();

        type.Should().NotBeNull();
        type!.Namespace.Should().StartWith("Game.Core.");
    }

    // ACC:T227.5
    [Fact]
    [Trait("acceptance", "ACC:T227.5")]
    public void ShouldTreatConflictAsDefect_WhenNoLaterFreezeRevisionSupersedesIt()
    {
        var result = EvaluateFreezeConflict(conflictsWithFrozenRule: true, laterFreezeRevision: null);

        result.IsDefect.Should().BeTrue("a conflicting implementation must be classified as a bug until a later freeze revision supersedes it");
        result.IsBlocked.Should().BeTrue();
        result.IsAccepted.Should().BeFalse();
        result.ReasonCode.Should().Be("freeze_conflict_blocked");
    }

    // ACC:T227.6
    [Fact]
    [Trait("acceptance", "ACC:T227.6")]
    public void ShouldAcceptConflict_WhenLaterFreezeRevisionExplicitlySupersedesIt()
    {
        var result = EvaluateFreezeConflict(conflictsWithFrozenRule: true, laterFreezeRevision: "freeze-main-r2");

        result.IsAccepted.Should().BeTrue("a later freeze revision is the only valid basis for accepting a conflicting rule change");
        result.IsBlocked.Should().BeFalse();
        result.IsDefect.Should().BeFalse();
        result.ReasonCode.Should().Be("superseded_by_later_freeze_revision");
    }

    // ACC:T227.7
    [Fact]
    [Trait("acceptance", "ACC:T227.7")]
    public void ShouldCoverPrimaryDeterministicBehavior_WhenConflictPolicyRunsTwice()
    {
        var first = EvaluateFreezeConflict(conflictsWithFrozenRule: true, laterFreezeRevision: null);
        var second = EvaluateFreezeConflict(conflictsWithFrozenRule: true, laterFreezeRevision: null);

        second.Should().Be(first, "freeze conflict evaluation must be deterministic for identical inputs");
    }

    // ACC:T227.8
    [Fact]
    [Trait("acceptance", "ACC:T227.8")]
    public void ShouldProvideRedFirstCoverage_WhenImplementationConflictsWithFrozenRules()
    {
        var result = EvaluateFreezeConflict(conflictsWithFrozenRule: true, laterFreezeRevision: string.Empty);

        result.IsAccepted.Should().BeFalse("empty supersession evidence must not unblock a conflict");
        result.IsBlocked.Should().BeTrue();
        result.ReasonCode.Should().Be("freeze_conflict_blocked");
    }

    // ACC:T227.8
    [Fact]
    [Trait("acceptance", "ACC:T227.8")]
    public void ShouldRejectConflict_WhenLaterFreezeRevisionIsWhitespaceOnly()
    {
        var result = EvaluateFreezeConflict(conflictsWithFrozenRule: true, laterFreezeRevision: "   ");

        result.IsAccepted.Should().BeFalse("whitespace-only supersession evidence must not unblock a conflict");
        result.IsBlocked.Should().BeTrue();
        result.IsDefect.Should().BeTrue();
        result.ReasonCode.Should().Be("freeze_conflict_blocked");
    }

    // ACC:T227.9
    [Fact]
    [Trait("acceptance", "ACC:T227.9")]
    public void ShouldStayInCoreAssembly_WhenFreezeConflictPolicyIsImplemented()
    {
        var type = ResolvePolicyType();

        type.Should().NotBeNull("freeze conflict behavior must live in Game.Core pure logic");
        type!.Assembly.GetName().Name.Should().Be("Game.Core");
        type.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static)
            .Select(field => field.FieldType.FullName ?? string.Empty)
            .Should().NotContain(fieldType => fieldType.StartsWith("Godot.", StringComparison.Ordinal));
    }

    // ACC:T227.10
    [Fact]
    [Trait("acceptance", "ACC:T227.10")]
    public void ShouldAvoidGodotDependencies_WhenFreezeConflictPolicyEvaluatesCoreRules()
    {
        var type = ResolvePolicyType();

        type.Should().NotBeNull();
        type!.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
            .SelectMany(method => method.GetParameters().Select(parameter => parameter.ParameterType.FullName ?? string.Empty))
            .Should().NotContain(parameterType => parameterType.StartsWith("Godot.", StringComparison.Ordinal));
    }

    // ACC:T227.11
    [Fact]
    [Trait("acceptance", "ACC:T227.11")]
    public void ShouldLeaveNonConflictingChangeAccepted_WhenNoFreezeConflictExists()
    {
        var result = EvaluateFreezeConflict(conflictsWithFrozenRule: false, laterFreezeRevision: null);

        result.IsAccepted.Should().BeTrue();
        result.IsBlocked.Should().BeFalse();
        result.IsDefect.Should().BeFalse();
        result.ReasonCode.Should().Be("no_freeze_conflict");
    }

    // ACC:T227.12
    [Fact]
    [Trait("acceptance", "ACC:T227.12")]
    public void ShouldRemainDeterministic_WhenPreviouslyPassingPolicyCasesRunTogether()
    {
        var accepted = EvaluateFreezeConflict(conflictsWithFrozenRule: false, laterFreezeRevision: null);
        var blocked = EvaluateFreezeConflict(conflictsWithFrozenRule: true, laterFreezeRevision: null);
        var superseded = EvaluateFreezeConflict(conflictsWithFrozenRule: true, laterFreezeRevision: "freeze-main-r2");

        accepted.ReasonCode.Should().Be("no_freeze_conflict");
        blocked.ReasonCode.Should().Be("freeze_conflict_blocked");
        superseded.ReasonCode.Should().Be("superseded_by_later_freeze_revision");
    }

    // ACC:T227.13
    [Fact]
    [Trait("acceptance", "ACC:T227.13")]
    public void ShouldExposeAuditStableStatus_WhenChapterThreeCoverageEvidenceIsRequired()
    {
        var result = EvaluateFreezeConflict(conflictsWithFrozenRule: true, laterFreezeRevision: null);

        result.Status.Should().Be("BlockedAsBug");
        result.EvidenceLane.Should().Be("xunit-core");
    }

    // ACC:T227.14
    [Fact]
    [Trait("acceptance", "ACC:T227.14")]
    public void ShouldKeepBaselineValidatorEvidenceRequired_WhenTaskViewIsWritten()
    {
        var result = EvaluateFreezeConflict(conflictsWithFrozenRule: true, laterFreezeRevision: null);

        result.RequiresTripletBaselineValidation.Should().BeTrue("task view writes for this freeze policy must be followed by Chapter 3.8 triplet baseline validators");
    }

    private static FreezeConflictEvaluation EvaluateFreezeConflict(bool conflictsWithFrozenRule, string? laterFreezeRevision)
    {
        var type = ResolvePolicyType();
        if (type is null)
        {
            return FreezeConflictEvaluation.MissingImplementation;
        }

        var method = type.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
            .FirstOrDefault(candidate => candidate.Name == "Evaluate" && candidate.GetParameters().Length == 6);

        method.Should().NotBeNull("FreezeConflictPolicy must expose Evaluate with deterministic core inputs");

        var target = method!.IsStatic ? null : Activator.CreateInstance(type);
        var value = method.Invoke(target, new object?[]
        {
            "freeze-main-r1",
            "FRZ-MAIN-001",
            "candidate-change",
            conflictsWithFrozenRule,
            laterFreezeRevision,
            "Game.Core.Tests/Tasks/Task227FreezeConflictPolicyTests.cs",
        });

        value.Should().NotBeNull("freeze conflict evaluation must return an observable result");
        return FreezeConflictEvaluation.From(value!);
    }

    private static Type? ResolvePolicyType()
    {
        return Type.GetType("Game.Core.Services.FreezeConflictPolicy, Game.Core", throwOnError: false)
            ?? Type.GetType("Game.Core.Domain.FreezeConflictPolicy, Game.Core", throwOnError: false);
    }

    private static string ReadRepositoryFile(string relativePath)
    {
        return File.ReadAllText(Path.Combine(RepositoryRoot, relativePath));
    }

    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (File.Exists(Path.Combine(directory.FullName, "Game.sln")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate repository root from test output directory.");
    }

    private readonly record struct FreezeConflictEvaluation(
        bool IsAccepted,
        bool IsBlocked,
        bool IsDefect,
        bool RequiresTripletBaselineValidation,
        string ReasonCode,
        string Status,
        string EvidenceLane)
    {
        public static FreezeConflictEvaluation MissingImplementation => new(
            IsAccepted: true,
            IsBlocked: false,
            IsDefect: false,
            RequiresTripletBaselineValidation: false,
            ReasonCode: "missing_freeze_conflict_policy",
            Status: "MissingImplementation",
            EvidenceLane: "missing");

        public static FreezeConflictEvaluation From(object value)
        {
            var type = value.GetType();
            return new FreezeConflictEvaluation(
                ReadBoolean(type, value, nameof(IsAccepted)),
                ReadBoolean(type, value, nameof(IsBlocked)),
                ReadBoolean(type, value, nameof(IsDefect)),
                ReadBoolean(type, value, nameof(RequiresTripletBaselineValidation)),
                ReadString(type, value, nameof(ReasonCode)),
                ReadString(type, value, nameof(Status)),
                ReadString(type, value, nameof(EvidenceLane)));
        }

        private static bool ReadBoolean(Type type, object value, string name)
        {
            var property = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance);
            property.Should().NotBeNull($"evaluation result must expose {name}");
            property!.PropertyType.Should().Be(typeof(bool));
            return (bool)property.GetValue(value)!;
        }

        private static string ReadString(Type type, object value, string name)
        {
            var property = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance);
            property.Should().NotBeNull($"evaluation result must expose {name}");
            property!.PropertyType.Should().Be(typeof(string));
            return (string)property.GetValue(value)!;
        }
    }
}
