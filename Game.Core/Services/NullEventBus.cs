using Game.Core.Contracts;

namespace Game.Core.Services;

/// <summary>
/// Null-object implementation of <see cref="IEventBus"/> to enforce non-null dependencies.
/// </summary>
public sealed class NullEventBus : IEventBus
{
    public static NullEventBus Instance { get; } = new();

    private NullEventBus()
    {
    }

    public Task PublishAsync(DomainEvent evt) => Task.CompletedTask;

    public IDisposable Subscribe(Func<DomainEvent, Task> handler) => NoopDisposable.Instance;

    private sealed class NoopDisposable : IDisposable
    {
        public static NoopDisposable Instance { get; } = new();

        private NoopDisposable()
        {
        }

        public void Dispose()
        {
        }
    }
}

