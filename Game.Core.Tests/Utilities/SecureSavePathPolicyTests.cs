using System;
using System.Reflection;
using FluentAssertions;
using Game.Core.Utilities;
using Xunit;

namespace Game.Core.Tests.Utilities;

public class SecureSavePathPolicyTests
{
    // ACC:T18.2
    [Theory]
    [InlineData("C:/temp/save.json")]
    [InlineData("C:\\temp\\save.json")]
    [InlineData("\\\\server\\share\\save.json")]
    [InlineData("/etc/passwd")]
    public void ShouldRejectAbsolutePaths_WhenResolvingSavePath(string input)
    {
        var ok = SecureSavePathPolicyApi.TryResolve("user://saves", input, out var resolved);

        ok.Should().BeFalse();
        resolved.Should().BeNullOrEmpty();
    }

    // ACC:T18.2
    [Theory]
    [InlineData("../evil.json")]
    [InlineData("..\\evil.json")]
    [InlineData("user://saves/../evil.json")]
    [InlineData("user://saves\\..\\evil.json")]
    [InlineData("user://../evil.json")]
    public void ShouldRejectPathTraversal_WhenResolvingSavePath(string input)
    {
        var ok = SecureSavePathPolicyApi.TryResolve("user://saves", input, out var resolved);

        ok.Should().BeFalse();
        resolved.Should().BeNullOrEmpty();
    }

    // ACC:T18.2
    [Fact]
    public void ShouldAllowRelativePathWithinUserRoot_WhenResolvingSavePath()
    {
        var ok = SecureSavePathPolicyApi.TryResolve("user://saves", "slot1.json", out var resolved);

        ok.Should().BeTrue();
        resolved.Should().NotBeNullOrEmpty();
        resolved.Should().StartWith("user://", "resolved path must stay within the controlled user root");
        resolved.Should().StartWith("user://saves/");
        resolved.Should().NotContain("..", "path traversal must be rejected");
        resolved.Should().NotContain("\\", "Godot paths should use forward slashes");
        resolved.Should().Be("user://saves/slot1.json");
    }

    // ACC:T18.2
    [Fact]
    public void ShouldAllowUserPathWithinRoot_WhenResolvingSavePath()
    {
        var ok = SecureSavePathPolicyApi.TryResolve("user://saves", "user://saves/slot2.json", out var resolved);

        ok.Should().BeTrue();
        resolved.Should().Be("user://saves/slot2.json");
    }

    // ACC:T18.2
    [Fact]
    public void ShouldRejectUserPathOutsideRoot_WhenResolvingSavePath()
    {
        var ok = SecureSavePathPolicyApi.TryResolve("user://saves", "user://other/slot.json", out var resolved);

        ok.Should().BeFalse();
        resolved.Should().BeNullOrEmpty();
    }

    // ACC:T18.2
    [Fact]
    public void ShouldNormalizeUserRootWithSingleSlash_WhenResolvingSavePath()
    {
        var ok = SecureSavePathPolicyApi.TryResolve("user:/saves/", "slot3.json", out var resolved);

        ok.Should().BeTrue();
        resolved.Should().Be("user://saves/slot3.json");
    }

    // ACC:T18.2
    [Fact]
    public void ShouldNormalizeUserPathWithExtraSlashes_WhenResolvingSavePath()
    {
        var ok = SecureSavePathPolicyApi.TryResolve("user://saves", "user://saves//slot4.json", out var resolved);

        ok.Should().BeTrue();
        resolved.Should().Be("user://saves/slot4.json");
    }

    // ACC:T18.2
    [Theory]
    [InlineData("a/./b.json")]
    [InlineData("./b.json")]
    public void ShouldRejectDotSegments_WhenResolvingSavePath(string input)
    {
        var ok = SecureSavePathPolicyApi.TryResolve("user://saves", input, out var resolved);

        ok.Should().BeFalse();
        resolved.Should().BeNullOrEmpty();
    }

    // ACC:T18.2
    [Fact]
    public void ShouldRejectNonUserRoot_WhenResolvingSavePath()
    {
        var ok = SecureSavePathPolicyApi.TryResolve("res://saves", "slot.json", out var resolved);
        ok.Should().BeFalse();
        resolved.Should().BeNullOrEmpty();
    }

    // ACC:T18.2
    [Theory]
    [InlineData("")]
    [InlineData("  ")]
    public void ShouldRejectEmptyRootOrInput_WhenResolvingSavePath(string value)
    {
        var okRoot = SecureSavePathPolicyApi.TryResolve(value, "slot.json", out var resolvedRoot);
        okRoot.Should().BeFalse();
        resolvedRoot.Should().BeNullOrEmpty();

        var okInput = SecureSavePathPolicyApi.TryResolve("user://saves", value, out var resolvedInput);
        okInput.Should().BeFalse();
        resolvedInput.Should().BeNullOrEmpty();
    }

    // ACC:T18.2
    [Fact]
    public void ShouldRejectUserPathEqualToRoot_WhenResolvingSavePath()
    {
        var ok = SecureSavePathPolicyApi.TryResolve("user://saves", "user://saves", out var resolved);
        ok.Should().BeFalse();
        resolved.Should().BeNullOrEmpty();
    }

    // ACC:T18.2
    [Fact]
    public void ShouldNormalizeRelativePathWithExtraSlashes_WhenResolvingSavePath()
    {
        var ok = SecureSavePathPolicyApi.TryResolve("user://saves", "a//b.json", out var resolved);
        ok.Should().BeTrue();
        resolved.Should().Be("user://saves/a/b.json");
    }

    private static class SecureSavePathPolicyApi
    {
        private static readonly Lazy<MethodInfo> TryResolveMethod = new(ResolveTryResolveMethod);

        public static bool TryResolve(string root, string input, out string resolved)
        {
            var method = TryResolveMethod.Value;
            method.Should().NotBeNull("SecureSavePathPolicy.TryResolve must exist to enforce save path security");

            object?[] args = { root, input, string.Empty };
            var result = method.Invoke(null, args);

            result.Should().BeOfType<bool>("TryResolve must return a boolean allow/deny result");
            resolved = args[2] as string ?? string.Empty;

            return (bool)result!;
        }

        private static MethodInfo ResolveTryResolveMethod()
        {
            var coreAssembly = typeof(MathHelper).Assembly;
            var policyType = coreAssembly.GetType("Game.Core.Utilities.SecureSavePathPolicy");
            policyType.Should().NotBeNull("a secure save path policy must exist in Game.Core.Utilities to keep core logic Godot-free");

            var outString = typeof(string).MakeByRefType();
            var method = policyType!.GetMethod(
                name: "TryResolve",
                bindingAttr: BindingFlags.Public | BindingFlags.Static,
                binder: null,
                types: new[] { typeof(string), typeof(string), outString },
                modifiers: null);

            method.Should().NotBeNull("expected signature: public static bool TryResolve(string root, string input, out string resolved)");
            method!.ReturnType.Should().Be(typeof(bool), "TryResolve must return bool");
            return method;
        }
    }
}
