namespace Game.Core.Domain.ValueObjects;

/// <summary>
/// Fixed calendar date for Sanguo T2 gameplay.
/// Month length is fixed to 30 days and year length is fixed to 12 months.
/// </summary>
public readonly record struct SanguoCalendarDate
{
    public const int DaysPerMonth = 30;
    public const int MonthsPerYear = 12;

    public SanguoCalendarDate(int year, int month, int day)
    {
        if (year < 1)
            throw new ArgumentOutOfRangeException(nameof(year), "Year must be >= 1.");

        if (month is < 1 or > MonthsPerYear)
            throw new ArgumentOutOfRangeException(nameof(month), $"Month must be between 1 and {MonthsPerYear}.");

        if (day is < 1 or > DaysPerMonth)
            throw new ArgumentOutOfRangeException(nameof(day), $"Day must be between 1 and {DaysPerMonth}.");

        Year = year;
        Month = month;
        Day = day;
    }

    public int Year { get; }

    public int Month { get; }

    public int Day { get; }

    public SanguoCalendarDate AddDays(int days)
    {
        if (days < 0)
            throw new ArgumentOutOfRangeException(nameof(days), "Days must be non-negative.");

        var year = Year;
        var month = Month;
        var day = Day;

        for (var i = 0; i < days; i++)
        {
            day += 1;
            if (day <= DaysPerMonth)
                continue;

            day = 1;
            month += 1;
            if (month <= MonthsPerYear)
                continue;

            month = 1;
            year += 1;
        }

        return new SanguoCalendarDate(year, month, day);
    }

    public override string ToString()
        => $"{Year:D4}-{Month:D2}-{Day:D2}";
}

