using System.Threading.Tasks;
using Game.Core.Domain.Entities;

namespace Game.Core.Repositories;

public interface IUserRepository
{
    Task UpsertAsync(User user);
    Task<User?> FindByUsernameAsync(string username);
}

