using System;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Utilities;

public sealed class NoGodotDependencyTests
{
    // ACC:T26.1
    [Fact]
    public void ShouldNotReferenceGodot_WhenInspectingGameCoreAssemblyReferences()
    {
        var coreAssembly = LoadGameCoreAssembly();

        var referencedAssemblyNames = coreAssembly
            .GetReferencedAssemblies()
            .Select(a => a.Name ?? string.Empty)
            .ToArray();

        referencedAssemblyNames.Should().NotContain(n => n.StartsWith("Godot", StringComparison.OrdinalIgnoreCase));
        referencedAssemblyNames.Should().NotContain("GodotSharp");
    }

    [Fact]
    public void ShouldHaveAtLeastOneDefinedType_WhenLoadingGameCoreAssembly()
    {
        var coreAssembly = LoadGameCoreAssembly();
        coreAssembly.DefinedTypes.Should().NotBeEmpty();
    }

    private static Assembly LoadGameCoreAssembly()
    {
        var loaded = AppDomain.CurrentDomain
            .GetAssemblies()
            .Where(a => !a.IsDynamic)
            .FirstOrDefault(a =>
            {
                var name = a.GetName().Name;
                return name is not null && name.Equals("Game.Core", StringComparison.OrdinalIgnoreCase);
            });

        if (loaded is not null)
        {
            return loaded;
        }

        foreach (var assemblyName in new[] { "Game.Core", "GameCore" })
        {
            try
            {
                return Assembly.Load(new AssemblyName(assemblyName));
            }
            catch
            {
            }
        }

        var candidates = AppDomain.CurrentDomain
            .GetAssemblies()
            .Where(a => !a.IsDynamic)
            .Select(a => a.GetName().Name)
            .Where(n => !string.IsNullOrWhiteSpace(n))
            .ToArray();

        throw new InvalidOperationException(
            "Unable to load the Game.Core assembly. Loaded assemblies: " + string.Join(", ", candidates));
    }
}
