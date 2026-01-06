using System;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task18CoreAssemblyDependencyRulesTests
{
    // ACC:T18.1
    [Fact]
    public void ShouldNotReferenceGodotAssemblies_WhenLoadingCoreAssembly()
    {
        var referenced = typeof(Task18CoreAssemblyDependencyRulesTests).Assembly.GetReferencedAssemblies();

        var coreAssemblyName = referenced
            .FirstOrDefault(a => string.Equals(a.Name, "Game.Core", StringComparison.OrdinalIgnoreCase))
            ?? referenced.FirstOrDefault(a => a.Name != null && a.Name.StartsWith("Game.Core", StringComparison.OrdinalIgnoreCase));

        coreAssemblyName.Should().NotBeNull("Game.Core.Tests should reference the pure core assembly for engine-free unit testing");

        var coreAssembly = Assembly.Load(coreAssemblyName!);

        coreAssembly.DefinedTypes.Should().NotBeEmpty("the core assembly should contain production types");

        var dependencyNames = coreAssembly
            .GetReferencedAssemblies()
            .Select(a => a.Name)
            .Where(n => !string.IsNullOrWhiteSpace(n))
            .ToArray();

        dependencyNames.Should().NotContain(n => n!.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
        dependencyNames.Should().NotContain("GodotSharp");
    }
}
