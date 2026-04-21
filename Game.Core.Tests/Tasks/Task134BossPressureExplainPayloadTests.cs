using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using FluentAssertions;
using Xunit;

namespace Game.Core.Tests.Tasks;

public sealed class Task134BossPressureExplainPayloadTests
{
    // ACC:T134.1
    [Fact]
    [Trait("acceptance", "ACC:T134.1")]
    public void ShouldEmitSourceValueAndDurationDeterministically_WhenMappingBossPressureExplainPayloadItems()
    {
        var rawEntries = CreateExplainEntries();

        var firstResult = InvokeMapper(rawEntries);
        var secondResult = InvokeMapper(rawEntries);

        firstResult.Items.Should().HaveCount(rawEntries.Count);
        firstResult.Items.Select(item => item.Source).Should().Equal(rawEntries.Select(entry => entry.Source));
        firstResult.Items.Select(item => item.Value).Should().Equal(rawEntries.Select(entry => entry.Value));
        firstResult.Items.Select(item => item.Duration).Should().Equal(rawEntries.Select(entry => entry.Duration));
        secondResult.Should().BeEquivalentTo(firstResult, options => options.WithStrictOrdering());
    }

    // ACC:T134.2
    [Fact]
    [Trait("acceptance", "ACC:T134.2")]
    public void ShouldExposeDedicatedMapperModule_WhenResolvingTask134SplitScope()
    {
        var mapperType = FindMapperTypeOrNull();
        mapperType.Should().NotBeNull(
            "Task 134 requires a dedicated boss pressure explain payload mapper module for the T102 split scope.");

        if (mapperType is null)
        {
            return;
        }

        var mapMethod = FindMapMethod(mapperType);
        mapMethod.Should().NotBeNull(
            "the dedicated mapper module should expose a public Map(...) style entry point that produces explain payload items.");
    }

    private static IReadOnlyList<ExplainEntryInput> CreateExplainEntries()
    {
        return new[]
        {
            new ExplainEntryInput(Source: "base_boss_pressure", Value: 1, Duration: 1, FromDelayStacking: false),
            new ExplainEntryInput(Source: "delay_stack_pressure", Value: 2, Duration: 3, FromDelayStacking: true),
        };
    }

    private static ExplainPayloadResult InvokeMapper(IReadOnlyList<ExplainEntryInput> rawEntries)
    {
        var mapperType = FindMapperTypeOrNull();
        if (mapperType is null)
        {
            return MissingBossPressureExplainPayloadMapper.Map(rawEntries);
        }

        var mapMethod = FindMapMethod(mapperType);
        if (mapMethod is null)
        {
            return MissingBossPressureExplainPayloadMapper.Map(rawEntries);
        }

        var parameterType = mapMethod.GetParameters()[0].ParameterType;
        var argument = CreateArgument(parameterType, rawEntries);
        var mapperInstance = mapMethod.IsStatic ? null : CreateMapperInstanceOrNull(mapperType);
        if (!mapMethod.IsStatic && mapperInstance is null)
        {
            return MissingBossPressureExplainPayloadMapper.Map(rawEntries);
        }

        var rawResult = mapMethod.Invoke(mapperInstance, new[] { argument });
        return ConvertMapResult(rawResult);
    }

    private static object? CreateMapperInstanceOrNull(Type mapperType)
    {
        try
        {
            return Activator.CreateInstance(mapperType);
        }
        catch
        {
            return null;
        }
    }

    private static Type? FindMapperTypeOrNull()
    {
        var candidateNames = new[]
        {
            "Game.Core.Services.Sanguo.BossPressureExplainPayloadMapper",
            "Game.Core.Services.Sanguo.BossPressureExplainMapper",
            "Game.Core.Services.Sanguo.SanguoBossPressureExplainPayloadMapper",
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
                && type.Name.Contains("Explain", StringComparison.Ordinal)
                && type.Name.Contains("Mapper", StringComparison.Ordinal));
    }

    private static MethodInfo? FindMapMethod(Type mapperType)
    {
        var supportedNames = new[]
        {
            "Map",
            "MapExplainPayload",
            "MapPressureExplainPayload",
            "BuildExplainPayload",
        };

        return mapperType
            .GetMethods(BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance)
            .FirstOrDefault(method =>
            {
                if (!supportedNames.Contains(method.Name, StringComparer.Ordinal))
                {
                    return false;
                }

                var parameters = method.GetParameters();
                return parameters.Length == 1;
            });
    }

    private static object CreateArgument(Type parameterType, IReadOnlyList<ExplainEntryInput> rawEntries)
    {
        if (parameterType.IsAssignableFrom(rawEntries.GetType()))
        {
            return rawEntries;
        }

        if (parameterType == typeof(ExplainEntryInput[]))
        {
            return rawEntries.ToArray();
        }

        if (parameterType == typeof(List<ExplainEntryInput>))
        {
            return rawEntries.ToList();
        }

        if (!TryGetSequenceElementType(parameterType, out var elementType) || elementType is null)
        {
            throw new InvalidOperationException($"Unsupported mapper parameter type '{parameterType.FullName}'.");
        }

        var typedList = CreateTypedList(elementType, rawEntries);

        if (parameterType.IsArray)
        {
            return CreateArray(elementType, typedList);
        }

        if (parameterType.IsAssignableFrom(typedList.GetType()))
        {
            return typedList;
        }

        try
        {
            var instance = Activator.CreateInstance(parameterType, typedList);
            if (instance is not null)
            {
                return instance;
            }
        }
        catch
        {
        }

        return typedList;
    }

    private static IList CreateTypedList(Type elementType, IReadOnlyList<ExplainEntryInput> rawEntries)
    {
        var listType = typeof(List<>).MakeGenericType(elementType);
        var typedList = Activator.CreateInstance(listType) as IList;
        typedList.Should().NotBeNull($"unable to build typed list '{listType.FullName}' for mapper argument conversion.");

        if (typedList is null)
        {
            throw new InvalidOperationException($"Unable to build typed list '{listType.FullName}'.");
        }

        foreach (var rawEntry in rawEntries)
        {
            typedList.Add(ConvertEntry(elementType, rawEntry));
        }

        return typedList;
    }

    private static Array CreateArray(Type elementType, IList typedList)
    {
        var typedArray = Array.CreateInstance(elementType, typedList.Count);
        for (var index = 0; index < typedList.Count; index++)
        {
            typedArray.SetValue(typedList[index], index);
        }

        return typedArray;
    }

    private static object ConvertEntry(Type targetType, ExplainEntryInput rawEntry)
    {
        if (targetType == typeof(ExplainEntryInput) || targetType.IsAssignableFrom(typeof(ExplainEntryInput)))
        {
            return rawEntry;
        }

        if (TryCreateByConstructor(targetType, rawEntry, out var ctorBuilt) && ctorBuilt is not null)
        {
            SetPropertyIfExists(ctorBuilt, "Source", rawEntry.Source);
            SetPropertyIfExists(ctorBuilt, "Value", rawEntry.Value);
            SetPropertyIfExists(ctorBuilt, "Duration", rawEntry.Duration);
            SetPropertyIfExists(ctorBuilt, "FromDelayStacking", rawEntry.FromDelayStacking);
            return ctorBuilt;
        }

        var instance = Activator.CreateInstance(targetType);
        instance.Should().NotBeNull($"unable to create mapper input entry type '{targetType.FullName}'.");

        if (instance is null)
        {
            throw new InvalidOperationException($"Unable to create mapper input entry type '{targetType.FullName}'.");
        }

        SetPropertyIfExists(instance, "Source", rawEntry.Source);
        SetPropertyIfExists(instance, "Value", rawEntry.Value);
        SetPropertyIfExists(instance, "Duration", rawEntry.Duration);
        SetPropertyIfExists(instance, "FromDelayStacking", rawEntry.FromDelayStacking);
        SetPropertyIfExists(instance, "IsFromDelayStacking", rawEntry.FromDelayStacking);

        return instance;
    }

    private static bool TryCreateByConstructor(Type targetType, ExplainEntryInput rawEntry, out object? instance)
    {
        var constructors = targetType.GetConstructors()
            .OrderByDescending(ctor => ctor.GetParameters().Length)
            .ToArray();

        foreach (var constructor in constructors)
        {
            var parameters = constructor.GetParameters();
            if (parameters.Length == 0)
            {
                continue;
            }

            var args = parameters
                .Select(parameter => MapConstructorValue(parameter, rawEntry))
                .ToArray();

            try
            {
                instance = constructor.Invoke(args);
                return true;
            }
            catch
            {
            }
        }

        instance = null;
        return false;
    }

    private static object? MapConstructorValue(ParameterInfo parameter, ExplainEntryInput rawEntry)
    {
        var parameterName = parameter.Name ?? string.Empty;
        var normalizedName = parameterName.ToLowerInvariant();

        if (normalizedName.Contains("source", StringComparison.Ordinal))
        {
            return ConvertValue(rawEntry.Source, parameter.ParameterType);
        }

        if (normalizedName.Contains("value", StringComparison.Ordinal)
            || normalizedName.Contains("pressure", StringComparison.Ordinal)
            || normalizedName.Contains("amount", StringComparison.Ordinal))
        {
            return ConvertValue(rawEntry.Value, parameter.ParameterType);
        }

        if (normalizedName.Contains("duration", StringComparison.Ordinal)
            || normalizedName.Contains("round", StringComparison.Ordinal)
            || normalizedName.Contains("turn", StringComparison.Ordinal))
        {
            return ConvertValue(rawEntry.Duration, parameter.ParameterType);
        }

        if (normalizedName.Contains("delay", StringComparison.Ordinal)
            || normalizedName.Contains("stack", StringComparison.Ordinal))
        {
            return ConvertValue(rawEntry.FromDelayStacking, parameter.ParameterType);
        }

        if (parameter.HasDefaultValue)
        {
            return parameter.DefaultValue;
        }

        return parameter.ParameterType.IsValueType
            ? Activator.CreateInstance(parameter.ParameterType)
            : null;
    }

    private static void SetPropertyIfExists(object instance, string propertyName, object value)
    {
        var property = instance
            .GetType()
            .GetProperty(propertyName, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);

        if (property is null || !property.CanWrite)
        {
            return;
        }

        property.SetValue(instance, ConvertValue(value, property.PropertyType));
    }

    private static object? ConvertValue(object value, Type targetType)
    {
        var nonNullableType = Nullable.GetUnderlyingType(targetType) ?? targetType;

        if (nonNullableType.IsInstanceOfType(value))
        {
            return value;
        }

        if (nonNullableType.IsEnum && value is int intValue)
        {
            return Enum.ToObject(nonNullableType, intValue);
        }

        return Convert.ChangeType(value, nonNullableType);
    }

    private static ExplainPayloadResult ConvertMapResult(object? rawResult)
    {
        rawResult.Should().NotBeNull("Map(...) should return deterministic boss pressure explain payload data.");

        if (rawResult is null)
        {
            return new ExplainPayloadResult(Array.Empty<ExplainPayloadItem>());
        }

        var items = ReadPayloadItems(rawResult);
        return new ExplainPayloadResult(items);
    }

    private static IReadOnlyList<ExplainPayloadItem> ReadPayloadItems(object rawResult)
    {
        if (rawResult is IEnumerable enumerable && rawResult is not string)
        {
            return enumerable
                .Cast<object?>()
                .Where(item => item is not null)
                .Select(item => ReadPayloadItem(item!))
                .ToArray();
        }

        var itemsProperty = FindProperty(
            rawResult.GetType(),
            "Items",
            "PayloadItems",
            "ExplainItems",
            "Entries");

        itemsProperty.Should().NotBeNull(
            "mapper result should expose a payload item list via Items, PayloadItems, ExplainItems, or Entries.");

        var rawItems = itemsProperty?.GetValue(rawResult);
        rawItems.Should().BeAssignableTo<IEnumerable>();

        return ((IEnumerable)rawItems!)
            .Cast<object?>()
            .Where(item => item is not null)
            .Select(item => ReadPayloadItem(item!))
            .ToArray();
    }

    private static ExplainPayloadItem ReadPayloadItem(object rawItem)
    {
        if (rawItem is ExplainPayloadItem typedItem)
        {
            return typedItem;
        }

        var source = ReadRequiredString(rawItem, "Source", "source");
        var value = ReadRequiredInt(rawItem, "Value", "PressureValue", "Amount", "value");
        var duration = ReadRequiredInt(rawItem, "Duration", "DurationRounds", "DurationTurns", "duration");

        return new ExplainPayloadItem(source, value, duration);
    }

    private static string ReadRequiredString(object instance, params string[] candidateNames)
    {
        var found = TryReadMemberValue(instance, candidateNames, out var rawValue);
        found.Should().BeTrue($"expected one of [{string.Join(", ", candidateNames)}] on explain payload item.");
        rawValue.Should().NotBeNull($"member [{string.Join(", ", candidateNames)}] should not be null.");
        rawValue.Should().BeOfType<string>();

        return rawValue as string ?? string.Empty;
    }

    private static int ReadRequiredInt(object instance, params string[] candidateNames)
    {
        var found = TryReadMemberValue(instance, candidateNames, out var rawValue);
        found.Should().BeTrue($"expected one of [{string.Join(", ", candidateNames)}] on explain payload item.");
        rawValue.Should().NotBeNull($"member [{string.Join(", ", candidateNames)}] should not be null.");

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

        var parsed = int.TryParse(rawValue?.ToString(), out var parsedValue);
        parsed.Should().BeTrue($"member [{string.Join(", ", candidateNames)}] should be integer-compatible.");
        return parsedValue;
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

        var property = FindProperty(instance.GetType(), candidateNames);
        if (property is not null)
        {
            value = property.GetValue(instance);
            return true;
        }

        value = null;
        return false;
    }

    private static PropertyInfo? FindProperty(Type type, params string[] names)
    {
        foreach (var name in names)
        {
            var property = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            if (property is not null)
            {
                return property;
            }
        }

        return null;
    }

    private static bool TryGetSequenceElementType(Type type, out Type? elementType)
    {
        if (type.IsArray)
        {
            elementType = type.GetElementType();
            return elementType is not null;
        }

        if (type.IsGenericType)
        {
            var genericTypeDefinition = type.GetGenericTypeDefinition();
            if (genericTypeDefinition == typeof(IEnumerable<>)
                || genericTypeDefinition == typeof(IReadOnlyCollection<>)
                || genericTypeDefinition == typeof(IReadOnlyList<>)
                || genericTypeDefinition == typeof(ICollection<>)
                || genericTypeDefinition == typeof(IList<>)
                || genericTypeDefinition == typeof(List<>))
            {
                elementType = type.GetGenericArguments()[0];
                return true;
            }
        }

        var enumerableInterface = type
            .GetInterfaces()
            .FirstOrDefault(interfaceType =>
                interfaceType.IsGenericType
                && interfaceType.GetGenericTypeDefinition() == typeof(IEnumerable<>));

        if (enumerableInterface is not null)
        {
            elementType = enumerableInterface.GetGenericArguments()[0];
            return true;
        }

        elementType = null;
        return false;
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

    private sealed record ExplainEntryInput(string Source, int Value, int Duration, bool FromDelayStacking);

    private sealed record ExplainPayloadItem(string Source, int Value, int Duration);

    private sealed record ExplainPayloadResult(IReadOnlyList<ExplainPayloadItem> Items);

    private static class MissingBossPressureExplainPayloadMapper
    {
        public static ExplainPayloadResult Map(IReadOnlyList<ExplainEntryInput> rawEntries)
        {
            var mappedItems = rawEntries
                .Select(entry => new ExplainPayloadItem(
                    Source: entry.Source,
                    Value: entry.Value,
                    Duration: Math.Max(0, entry.Duration - 1)))
                .ToArray();

            return new ExplainPayloadResult(mappedItems);
        }
    }
}
