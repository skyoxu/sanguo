using Game.Core.Contracts;
using Game.Core.Contracts.Sanguo;
using Game.Core.Domain;
using MoneyValue = Game.Core.Domain.ValueObjects.Money;

namespace Game.Core.Services;

/// <summary>
/// 三国大富翁经济结算管理器，负责月末收益结算、年度地价调整与季度环境事件发布。
/// 所有经济规则遵循 ADR-0021（经济系统），事件发布遵循 ADR-0004（CloudEvents 契约）。
/// </summary>
/// <remarks>
/// 相关 ADR：
/// - ADR-0005: 质量门禁（覆盖率、文档规范）
/// - ADR-0015: 性能预算（算法复杂度 O(players × cities)）
/// - ADR-0018: 测试策略（单元测试、边界测试）
/// - ADR-0021: 经济规则（月末结算、年度调整、季度事件）
/// - ADR-0024: 事件溯源（CorrelationId/CausationId）
/// </remarks>
public sealed class SanguoEconomyManager
{
    private readonly IEventBus _bus;

    /// <summary>
    /// 初始化经济结算管理器。
    /// </summary>
    /// <param name="bus">事件总线，用于发布领域事件（不能为 null）。</param>
    /// <exception cref="ArgumentNullException">当 <paramref name="bus"/> 为 null 时抛出。</exception>
    public SanguoEconomyManager(IEventBus bus)
    {
        _bus = bus ?? throw new ArgumentNullException(nameof(bus));
    }

    /// <summary>
    /// 计算所有未出局玩家的月末收益结算金额。
    /// 遍历每个玩家的拥有城池，累加其 BaseToll 作为月收入。
    /// </summary>
    /// <param name="players">玩家列表（不能为 null；已出局玩家会被跳过）。</param>
    /// <param name="citiesById">城池字典，键为城池 ID（不能为 null；必须包含所有玩家拥有的城池 ID）。</param>
    /// <returns>玩家结算列表，每项包含 PlayerId 和 AmountDelta（已出局玩家不在结果中）。</returns>
    /// <exception cref="ArgumentNullException">当 <paramref name="players"/> 或 <paramref name="citiesById"/> 为 null 时抛出。</exception>
    /// <exception cref="InvalidOperationException">当玩家拥有的城池 ID 在字典中不存在时抛出。</exception>
    /// <remarks>
    /// 算法复杂度：O(players × cities)，符合 ADR-0015 性能预算。
    /// </remarks>
    public IReadOnlyList<PlayerSettlement> CalculateMonthSettlements(
        IReadOnlyList<ISanguoPlayerView> players,
        IReadOnlyDictionary<string, City> citiesById
    )
    {
        ArgumentNullException.ThrowIfNull(players, nameof(players));
        ArgumentNullException.ThrowIfNull(citiesById, nameof(citiesById));

        var settlements = new List<PlayerSettlement>(players.Count);
        foreach (var player in players)
        {
            if (player.IsEliminated)
                continue;

            var income = CalculateMonthlyIncome(player, citiesById);
            settlements.Add(new PlayerSettlement(player.PlayerId, income.ToDecimal()));
        }

        return settlements;
    }

    /// <summary>
    /// 在跨越月份边界时发布月末结算事件。
    /// 仅当 previousDate 和 currentDate 的年份或月份不同时才发布 SanguoMonthSettled 事件。
    /// </summary>
    /// <param name="gameId">游戏 ID（不能为空字符串）。</param>
    /// <param name="previousDate">上一个日期（用于检测月份边界）。</param>
    /// <param name="currentDate">当前日期（用于检测月份边界）。</param>
    /// <param name="settlements">玩家结算列表（不能为 null）。</param>
    /// <param name="correlationId">关联 ID（不能为空字符串）。</param>
    /// <param name="causationId">因果 ID（可选）。</param>
    /// <param name="occurredAt">事件发生时间。</param>
    /// <exception cref="ArgumentException">当 <paramref name="gameId"/> 或 <paramref name="correlationId"/> 为空字符串时抛出。</exception>
    /// <exception cref="ArgumentNullException">当 <paramref name="settlements"/> 为 null 时抛出。</exception>
    /// <remarks>
    /// 遵循 ADR-0004（CloudEvents 契约）和 ADR-0024（事件溯源）。
    /// 边界检测：previousDate.Year == currentDate.Year && previousDate.Month == currentDate.Month 时不发布。
    /// </remarks>
    public void PublishMonthSettlementIfBoundary(
        string gameId,
        DateTime previousDate,
        DateTime currentDate,
        IReadOnlyList<PlayerSettlement> settlements,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt
    )
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        ArgumentNullException.ThrowIfNull(settlements, nameof(settlements));

        if (previousDate.Year == currentDate.Year && previousDate.Month == currentDate.Month)
            return;

        var evt = new DomainEvent(
            Type: SanguoMonthSettled.EventType,
            Source: nameof(SanguoEconomyManager),
            Data: JsonElementEventData.FromObject(new SanguoMonthSettled(
                GameId: gameId,
                Year: previousDate.Year,
                Month: previousDate.Month,
                PlayerSettlements: settlements,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        );

        _bus.PublishAsync(evt).GetAwaiter().GetResult();
    }

    /// <summary>
    /// 计算每个城池的年度价格调整结果。
    /// 使用年度倍数乘以当前基础价格得到新价格。
    /// </summary>
    /// <param name="cities">城池列表（不能为 null）。</param>
    /// <param name="yearlyMultiplier">年度价格倍数（必须非负）。</param>
    /// <returns>调整结果列表，每项包含城池 ID、旧价格与新价格（所有城池均返回）。</returns>
    /// <exception cref="ArgumentNullException">当 <paramref name="cities"/> 为 null 时抛出。</exception>
    /// <exception cref="ArgumentOutOfRangeException">当 <paramref name="yearlyMultiplier"/> 为负数时抛出。</exception>
    /// <remarks>
    /// 遵循 ADR-0021（经济规则：年度地价调整）。算法复杂度：O(cities)。
    /// </remarks>
    public IReadOnlyList<(string CityId, MoneyValue OldPrice, MoneyValue NewPrice)> CalculateYearlyPriceAdjustments(
        IReadOnlyList<City> cities,
        decimal yearlyMultiplier
    )
    {
        ArgumentNullException.ThrowIfNull(cities, nameof(cities));

        if (yearlyMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(yearlyMultiplier), "Yearly price multiplier must be non-negative.");

        var results = new List<(string CityId, MoneyValue OldPrice, MoneyValue NewPrice)>(cities.Count);
        foreach (var city in cities)
        {
            var oldPrice = city.BasePrice;
            var newPrice = MoneyValue.FromDecimal(oldPrice.ToDecimal() * yearlyMultiplier);
            results.Add((city.Id, oldPrice, newPrice));
        }

        return results;
    }

    /// <summary>
    /// 在跨越年度边界时发布年度地价调整事件。
    /// 仅当 previousDate 和 currentDate 的年份不同时才发布事件。对每个城池发布一个独立的 SanguoYearPriceAdjusted 事件。
    /// </summary>
    /// <param name="gameId">游戏 ID（不能为空字符串）。</param>
    /// <param name="previousDate">上一个日期（用于检测年度边界）。</param>
    /// <param name="currentDate">当前日期（用于检测年度边界）。</param>
    /// <param name="cities">城池列表（不能为 null；将为每个城池发布独立事件）。</param>
    /// <param name="yearlyMultiplier">年度价格倍数（必须非负；将应用于所有城池）。</param>
    /// <param name="correlationId">关联 ID（不能为空字符串）。</param>
    /// <param name="causationId">因果 ID（可选）。</param>
    /// <param name="occurredAt">事件发生时间。</param>
    /// <exception cref="ArgumentException">当 <paramref name="gameId"/> 或 <paramref name="correlationId"/> 为空字符串时抛出。</exception>
    /// <exception cref="ArgumentNullException">当 <paramref name="cities"/> 为 null 时抛出。</exception>
    /// <remarks>
    /// 遵循 ADR-0004（CloudEvents 契约）、ADR-0021（经济规则：年度地价调整）和 ADR-0024（事件溯源）。
    /// 边界检测：previousDate.Year == currentDate.Year 时不发布。
    /// 调用 CalculateYearlyPriceAdjustments() 计算调整结果，然后为每个城池发布独立的 SanguoYearPriceAdjusted 事件。
    /// </remarks>
    public void PublishYearlyPriceAdjustmentIfBoundary(
        string gameId,
        DateTime previousDate,
        DateTime currentDate,
        IReadOnlyList<City> cities,
        decimal yearlyMultiplier,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt
    )
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        ArgumentNullException.ThrowIfNull(cities, nameof(cities));

        if (previousDate.Year == currentDate.Year)
            return;

        var adjustments = CalculateYearlyPriceAdjustments(cities, yearlyMultiplier);
        foreach (var (cityId, oldPrice, newPrice) in adjustments)
        {
            var evt = new DomainEvent(
                Type: SanguoYearPriceAdjusted.EventType,
                Source: nameof(SanguoEconomyManager),
                Data: JsonElementEventData.FromObject(new SanguoYearPriceAdjusted(
                    GameId: gameId,
                    Year: previousDate.Year,
                    CityId: cityId,
                    OldPrice: oldPrice.ToDecimal(),
                    NewPrice: newPrice.ToDecimal(),
                    OccurredAt: occurredAt,
                    CorrelationId: correlationId,
                    CausationId: causationId
                )),
                Timestamp: DateTime.UtcNow,
                Id: Guid.NewGuid().ToString("N")
            );

            _bus.PublishAsync(evt).GetAwaiter().GetResult();
        }
    }

    /// <summary>
    /// 在跨越月份边界时发布季度环境事件。
    /// 仅当 previousDate 和 currentDate 的年份或月份不同时才发布 SanguoSeasonEventApplied 事件。
    /// </summary>
    /// <param name="gameId">游戏 ID（不能为空字符串）。</param>
    /// <param name="previousDate">上一个日期（用于检测月份边界）。</param>
    /// <param name="currentDate">当前日期（用于检测月份边界）。</param>
    /// <param name="season">季节编号（必须在 1 到 4 之间）。</param>
    /// <param name="affectedRegionIds">受影响的区域 ID 列表（不能为 null）。</param>
    /// <param name="yieldMultiplier">产量倍数（必须非负）。</param>
    /// <param name="correlationId">关联 ID（不能为空字符串）。</param>
    /// <param name="causationId">因果 ID（可选）。</param>
    /// <param name="occurredAt">事件发生时间。</param>
    /// <exception cref="ArgumentException">当 <paramref name="gameId"/> 或 <paramref name="correlationId"/> 为空字符串时抛出。</exception>
    /// <exception cref="ArgumentOutOfRangeException">当 <paramref name="season"/> 不在 1 到 4 之间，或 <paramref name="yieldMultiplier"/> 为负数时抛出。</exception>
    /// <exception cref="ArgumentNullException">当 <paramref name="affectedRegionIds"/> 为 null 时抛出。</exception>
    /// <remarks>
    /// 遵循 ADR-0004（CloudEvents 契约）、ADR-0021（经济规则：季度环境事件）和 ADR-0024（事件溯源）。
    /// 边界检测：previousDate.Year == currentDate.Year &amp;&amp; previousDate.Month == currentDate.Month 时不发布。
    /// 发布的事件使用 currentDate 的年份，而非 previousDate。
    /// </remarks>
    public void PublishSeasonEventIfBoundary(
        string gameId,
        DateTime previousDate,
        DateTime currentDate,
        int season,
        IReadOnlyList<string> affectedRegionIds,
        decimal yieldMultiplier,
        string correlationId,
        string? causationId,
        DateTimeOffset occurredAt
    )
    {
        if (string.IsNullOrWhiteSpace(gameId))
            throw new ArgumentException("GameId must be non-empty.", nameof(gameId));

        if (string.IsNullOrWhiteSpace(correlationId))
            throw new ArgumentException("CorrelationId must be non-empty.", nameof(correlationId));

        if (season is < 1 or > 4)
            throw new ArgumentOutOfRangeException(nameof(season), "Season must be between 1 and 4.");

        ArgumentNullException.ThrowIfNull(affectedRegionIds, nameof(affectedRegionIds));

        if (yieldMultiplier < 0)
            throw new ArgumentOutOfRangeException(nameof(yieldMultiplier), "Yield multiplier must be non-negative.");

        if (previousDate.Year == currentDate.Year && previousDate.Month == currentDate.Month)
            return;

        var evt = new DomainEvent(
            Type: SanguoSeasonEventApplied.EventType,
            Source: nameof(SanguoEconomyManager),
            Data: JsonElementEventData.FromObject(new SanguoSeasonEventApplied(
                GameId: gameId,
                Year: currentDate.Year,
                Season: season,
                AffectedRegionIds: affectedRegionIds,
                YieldMultiplier: yieldMultiplier,
                OccurredAt: occurredAt,
                CorrelationId: correlationId,
                CausationId: causationId
            )),
            Timestamp: DateTime.UtcNow,
            Id: Guid.NewGuid().ToString("N")
        );

        _bus.PublishAsync(evt).GetAwaiter().GetResult();
    }

    private static MoneyValue CalculateMonthlyIncome(ISanguoPlayerView player, IReadOnlyDictionary<string, City> citiesById)
    {
        ArgumentNullException.ThrowIfNull(player, nameof(player));

        var totalMinorUnits = 0L;
        foreach (var cityId in player.OwnedCityIds)
        {
            if (!citiesById.TryGetValue(cityId, out var city))
                throw new InvalidOperationException($"Owned city id not found: {cityId}");

            totalMinorUnits = checked(totalMinorUnits + city.BaseToll.MinorUnits);
        }

        return new MoneyValue(totalMinorUnits);
    }
}

