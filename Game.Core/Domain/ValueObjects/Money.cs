using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Game.Core.Domain.ValueObjects;

/// <summary>
/// Immutable money value stored in minor units to ensure deterministic arithmetic and shared invariants.
/// </summary>
/// <remarks>
/// Invariants:
/// - Must be between 0 and <see cref="MaxMajorUnits"/> (inclusive).
/// - All arithmetic is checked against <see cref="MaxMajorUnits"/>.
/// </remarks>
[JsonConverter(typeof(MoneyJsonConverter))]
public readonly record struct Money : IComparable<Money>
{
    public const int MinorUnitsPerUnit = 100;
    public const long MaxMajorUnits = 99_999_999L;
    public const long MaxMinorUnits = MaxMajorUnits * MinorUnitsPerUnit;

    public Money(long minorUnits)
    {
        if (minorUnits < 0 || minorUnits > MaxMinorUnits)
            throw new ArgumentOutOfRangeException(nameof(minorUnits), $"Money must be between 0 and {MaxMajorUnits}.");

        MinorUnits = minorUnits;
    }

    /// <summary>
    /// Money value expressed in minor units (1/<see cref="MinorUnitsPerUnit"/>).
    /// </summary>
    public long MinorUnits { get; }

    public static Money Zero => new(0);

    public static Money FromMajorUnits(long majorUnits)
    {
        if (majorUnits < 0 || majorUnits > MaxMajorUnits)
            throw new ArgumentOutOfRangeException(nameof(majorUnits), $"Money must be between 0 and {MaxMajorUnits}.");

        return new Money(checked(majorUnits * MinorUnitsPerUnit));
    }

    public static Money FromDecimal(decimal amount)
    {
        if (amount < 0)
            throw new ArgumentOutOfRangeException(nameof(amount), "Money must be non-negative.");

        if (amount > MaxMajorUnits)
            throw new ArgumentOutOfRangeException(nameof(amount), $"Money must not exceed {MaxMajorUnits}.");

        var scaled = amount * MinorUnitsPerUnit;
        var rounded = decimal.Round(scaled, 0, MidpointRounding.AwayFromZero);
        return new Money(checked((long)rounded));
    }

    public decimal ToDecimal() => MinorUnits / (decimal)MinorUnitsPerUnit;

    public Money Add(Money other)
    {
        var sum = checked(MinorUnits + other.MinorUnits);
        if (sum > MaxMinorUnits)
            throw new OverflowException($"Money must not exceed {MaxMajorUnits}.");

        return new Money(sum);
    }

    public Money AddCapped(Money other, out Money overflow)
    {
        var sum = checked(MinorUnits + other.MinorUnits);
        if (sum <= MaxMinorUnits)
        {
            overflow = Zero;
            return new Money(sum);
        }

        overflow = new Money(sum - MaxMinorUnits);
        return new Money(MaxMinorUnits);
    }

    public Money Subtract(Money other)
    {
        if (other.MinorUnits > MinorUnits)
            throw new InvalidOperationException("Money must not become negative.");

        return new Money(MinorUnits - other.MinorUnits);
    }

    public int CompareTo(Money other) => MinorUnits.CompareTo(other.MinorUnits);

    public static Money operator +(Money left, Money right) => left.Add(right);
    public static Money operator -(Money left, Money right) => left.Subtract(right);

    public static bool operator <(Money left, Money right) => left.MinorUnits < right.MinorUnits;
    public static bool operator <=(Money left, Money right) => left.MinorUnits <= right.MinorUnits;
    public static bool operator >(Money left, Money right) => left.MinorUnits > right.MinorUnits;
    public static bool operator >=(Money left, Money right) => left.MinorUnits >= right.MinorUnits;

    public override string ToString() => ToDecimal().ToString("0.##", CultureInfo.InvariantCulture);

    private sealed class MoneyJsonConverter : JsonConverter<Money>
    {
        public override Money Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
        {
            if (reader.TokenType == JsonTokenType.Number)
            {
                if (reader.TryGetInt64(out var asInt))
                {
                    try
                    {
                        return FromMajorUnits(asInt);
                    }
                    catch (Exception ex) when (ex is ArgumentOutOfRangeException or OverflowException)
                    {
                        throw new JsonException("Money value is out of range.", ex);
                    }
                }

                try
                {
                    return FromDecimal(reader.GetDecimal());
                }
                catch (Exception ex) when (ex is ArgumentOutOfRangeException or OverflowException)
                {
                    throw new JsonException("Money value is out of range.", ex);
                }
            }

            if (reader.TokenType == JsonTokenType.String)
            {
                var text = reader.GetString();
                if (string.IsNullOrWhiteSpace(text))
                    throw new JsonException("Money value is empty.");

                if (!decimal.TryParse(text, NumberStyles.Number, CultureInfo.InvariantCulture, out var amount))
                    throw new JsonException($"Invalid money value: {text}");

                try
                {
                    return FromDecimal(amount);
                }
                catch (Exception ex) when (ex is ArgumentOutOfRangeException or OverflowException)
                {
                    throw new JsonException("Money value is out of range.", ex);
                }
            }

            throw new JsonException($"Invalid token for Money: {reader.TokenType}");
        }

        public override void Write(Utf8JsonWriter writer, Money value, JsonSerializerOptions options)
            => writer.WriteNumberValue(value.ToDecimal());
    }
}
