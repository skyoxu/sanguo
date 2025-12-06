using System.Threading.Tasks;

namespace Game.Core.Ports;

public interface IDataStore
{
    Task SaveAsync(string key, string json);
    Task<string?> LoadAsync(string key);
    Task DeleteAsync(string key);
}
