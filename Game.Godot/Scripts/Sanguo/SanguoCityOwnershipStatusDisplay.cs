using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;
using Godot;
using System.Text.Json;

namespace Game.Godot.Scripts.Sanguo;

public partial class SanguoCityOwnershipStatusDisplay : Control
{
    private const string OwnerPrefixKey = "ui.city_status.owner";
    private const string UnownedKey = "ui.city_status.unowned";
    private static readonly JsonDocumentOptions JsonOptions = new() { MaxDepth = 32 };

    private EventBusAdapter? _bus;
    private string _ownerId = string.Empty;
    private string _cityId = string.Empty;
    private Label? _statusLabel;

    [Export]
    public string OwnerId
    {
        get => _ownerId;
        set
        {
            _ownerId = value ?? string.Empty;
            UpdateStatusText();
        }
    }

    [Export]
    public string CityId
    {
        get => _cityId;
        set
        {
            _cityId = value ?? string.Empty;
            UpdateStatusText();
        }
    }

    public override void _Ready()
    {
        _statusLabel = GetNodeOrNull<Label>("OwnershipStatusLabel");
        UpdateStatusText();

        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (_bus == null)
        {
            return;
        }

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        if (!_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
        {
            _bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
        }
    }

    public override void _ExitTree()
    {
        if (_bus == null)
        {
            return;
        }

        var callable = new Callable(this, nameof(OnDomainEventEmitted));
        if (_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
        {
            _bus.Disconnect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
        }

        _bus = null;
    }

    private void OnDomainEventEmitted(
        string type,
        string source,
        string dataJson,
        string id,
        string specVersion,
        string dataContentType,
        string timestampIso
    )
    {
        if (type != SanguoCityBought.EventType)
        {
            return;
        }

        var json = string.IsNullOrWhiteSpace(dataJson) ? "{}" : dataJson;
        if (json.Length > 65536)
        {
            return;
        }

        try
        {
            using var doc = JsonDocument.Parse(json, JsonOptions);
            var root = doc.RootElement;

            if (!root.TryGetProperty("CityId", out var cityIdProp))
            {
                return;
            }

            var cityId = cityIdProp.GetString() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(cityId))
            {
                return;
            }

            if (!string.IsNullOrWhiteSpace(_cityId) && !string.Equals(_cityId, cityId, System.StringComparison.Ordinal))
            {
                return;
            }

            if (!root.TryGetProperty("BuyerId", out var buyerIdProp))
            {
                return;
            }

            var buyerId = buyerIdProp.GetString() ?? string.Empty;
            if (string.IsNullOrWhiteSpace(buyerId))
            {
                return;
            }

            OwnerId = buyerId;
        }
        catch
        {
            // View-only: ignore parse failures (core validation happens in Game.Core).
        }
    }

    private void UpdateStatusText()
    {
        if (_statusLabel is null)
            return;

        if (string.IsNullOrWhiteSpace(_ownerId))
        {
            _statusLabel.Text = TranslateOrFallback(UnownedKey, "Unowned");
            Visible = false;
            return;
        }

        Visible = true;
        var ownerPrefix = TranslateOrFallback(OwnerPrefixKey, "Owner");
        _statusLabel.Text = $"{ownerPrefix}: {_ownerId}";
    }

    private static string TranslateOrFallback(string key, string fallback)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return fallback;
        }

        var translated = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(translated) || string.Equals(translated, key, System.StringComparison.Ordinal))
        {
            return fallback;
        }

        return translated;
    }
}
