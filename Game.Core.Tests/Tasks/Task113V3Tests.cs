using System;
using System.Collections.Generic;
using System.Reflection;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task113V3Tests
{
    private static IReadOnlyDictionary<string, string> ApplyPolicy(string buildMode, IReadOnlyDictionary<string, string> payload)
    {
        var policyType = Type.GetType("Game.Core.Services.DiagnosticPayloadDesensitizationPolicy, Game.Core");
        policyType.Should().NotBeNull("Task 113 requires a diagnostics desensitization policy implementation");

        var method = policyType!.GetMethod(
            "Apply",
            BindingFlags.Public | BindingFlags.Static,
            binder: null,
            types: new[] { typeof(string), typeof(IReadOnlyDictionary<string, string>) },
            modifiers: null);
        method.Should().NotBeNull("Task 113 requires public static Apply(string, IReadOnlyDictionary<string,string>)");

        var value = method!.Invoke(null, new object[] { buildMode, payload });
        value.Should().BeAssignableTo<IReadOnlyDictionary<string, string>>();
        return (IReadOnlyDictionary<string, string>)value!;
    }

    // ACC:T113.1
    [Fact]
    [Trait("acceptance", "ACC:T113.1")]
    public void ShouldMaskSensitiveFields_WhenBuildModeIsRelease()
    {
        var input = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["stackTrace"] = "NullReferenceException at line 42",
            ["authToken"] = "token-abc-123",
            ["eventType"] = "core.traceability.checked",
        };

        var output = ApplyPolicy("release", input);

        output["stackTrace"].Should().MatchRegex(@"^\[masked:[0-9a-f]{12}\]$");
        output["authToken"].Should().MatchRegex(@"^\[masked:[0-9a-f]{12}\]$");
        output["stackTrace"].Should().NotContain("NullReferenceException");
        output["authToken"].Should().NotContain("token-abc-123");
        output["eventType"].Should().Be(input["eventType"]);
    }

    // ACC:T113.2
    [Fact]
    [Trait("acceptance", "ACC:T113.2")]
    public void ShouldKeepRawDiagnostics_WhenBuildModeIsDev()
    {
        var input = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["stackTrace"] = "NullReferenceException at line 42",
            ["authToken"] = "token-abc-123",
            ["eventType"] = "core.traceability.checked",
        };

        var output = ApplyPolicy("dev", input);

        output["stackTrace"].Should().Be(input["stackTrace"]);
        output["authToken"].Should().Be(input["authToken"]);
        output["eventType"].Should().Be(input["eventType"]);
    }

    // ACC:T113.3
    [Fact]
    [Trait("acceptance", "ACC:T113.3")]
    public void ShouldReturnDeterministicOutput_WhenPayloadAndBuildModeAreSame()
    {
        var input = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["stackTrace"] = "NullReferenceException at line 42",
            ["authToken"] = "token-abc-123",
            ["eventType"] = "core.traceability.checked",
        };

        var first = ApplyPolicy("release", input);
        var second = ApplyPolicy("release", input);

        first.Should().BeEquivalentTo(second);
    }

    // ACC:T113.4
    [Fact]
    [Trait("acceptance", "ACC:T113.4")]
    public void ShouldReturnSameMaskedValue_WhenReleaseModeUsesSameSensitiveFieldValue()
    {
        var firstPayload = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["authToken"] = "token-abc-123",
            ["eventType"] = "core.audit.logged",
        };
        var secondPayload = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["authToken"] = "token-abc-123",
            ["eventType"] = "core.traceability.checked",
        };

        var first = ApplyPolicy("release", firstPayload);
        var second = ApplyPolicy("release", secondPayload);

        first["authToken"].Should().Be(second["authToken"]);
        first["authToken"].Should().MatchRegex(@"^\[masked:[0-9a-f]{12}\]$");
    }
}
