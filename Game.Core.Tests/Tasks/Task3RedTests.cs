using System;
using FluentAssertions;
using Game.Core.Domain;
using Xunit;

namespace Game.Core.Tests.Tasks;

public class Task3RedTests
{
    [Fact]
    public void CityModel_ShouldExist_AndExposeExpectedApi()
    {
        var domainAssembly = typeof(Player).Assembly;

        var cityType = domainAssembly.GetType("Game.Core.Domain.City");
        cityType.Should().NotBeNull("Task 3 requires a City domain model in Game.Core.Domain");

        var ctor = cityType!.GetConstructor(new[]
        {
            typeof(string),   // id
            typeof(string),   // name
            typeof(string),   // regionId
            typeof(decimal),  // basePrice
            typeof(decimal),  // baseToll
        });
        ctor.Should().NotBeNull("City should have a ctor (string id, string name, string regionId, decimal basePrice, decimal baseToll)");

        object city = ctor!.Invoke(new object[] { "c1", "CityName", "r1", 100m, 10m });

        cityType.GetProperty("Id")?.PropertyType.Should().Be(typeof(string));
        cityType.GetProperty("Name")?.PropertyType.Should().Be(typeof(string));
        cityType.GetProperty("RegionId")?.PropertyType.Should().Be(typeof(string));
        cityType.GetProperty("BasePrice")?.PropertyType.Should().Be(typeof(decimal));
        cityType.GetProperty("BaseToll")?.PropertyType.Should().Be(typeof(decimal));

        var getPrice = cityType.GetMethod("GetPrice", new[] { typeof(decimal) });
        var getToll = cityType.GetMethod("GetToll", new[] { typeof(decimal) });
        getPrice.Should().NotBeNull("City should expose GetPrice(decimal multiplier)");
        getToll.Should().NotBeNull("City should expose GetToll(decimal multiplier)");

        var price = (decimal)getPrice!.Invoke(city, new object[] { 1.0m })!;
        var toll = (decimal)getToll!.Invoke(city, new object[] { 1.0m })!;
        price.Should().Be(100m);
        toll.Should().Be(10m);
    }
}
