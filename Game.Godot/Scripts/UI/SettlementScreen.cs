using System;
using System.Text.Json;
using Godot;
using Game.Core.Contracts.Sanguo;
using Game.Godot.Adapters;

namespace Game.Godot.Scripts.UI;

public partial class SettlementScreen : Control
{
    private const string UiSettlementTitleKey = "ui.settlement.title";
    private const string UiSettlementMainMenuKey = "ui.settlement.main_menu";
    private const string UiSettlementNewGameKey = "ui.settlement.new_game";
    private const string RootEventBusPath = "/root/EventBus";
    private const string RootMainMenuPath = "/root/Main/MenuLayer/MainMenu";
    private const string RootMainMenuPlayButtonPath = "/root/Main/MenuLayer/MainMenu/MenuRow/MenuBox/BtnPlay";

    private static readonly JsonDocumentOptions JsonParseOptions = new()
    {
        MaxDepth = 32,
    };

    private Label? _titleLabel;
    private Label? _winnerLabel;
    private RichTextLabel? _statsSnapshotLabel;
    private Button? _mainMenuButton;
    private Button? _newGameButton;

    private EventBusAdapter? _bus;

    public override void _Ready()
    {
        Visible = false;

        _titleLabel = GetNodeOrNull<Label>("Center/Panel/VBox/Title");
        _winnerLabel = GetNodeOrNull<Label>("Center/Panel/VBox/WinnerLabel");
        _statsSnapshotLabel = GetNodeOrNull<RichTextLabel>("Center/Panel/VBox/StatsSnapshotLabel");
        _mainMenuButton = GetNodeOrNull<Button>("Center/Panel/VBox/Buttons/MainMenuButton");
        _newGameButton = GetNodeOrNull<Button>("Center/Panel/VBox/Buttons/NewGameButton");

        if (_mainMenuButton != null)
        {
            _mainMenuButton.Pressed += OnMainMenuPressed;
        }

        if (_newGameButton != null)
        {
            _newGameButton.Pressed += OnNewGamePressed;
        }

        ClearText();
        ApplyLocalizedTexts();

        _bus = GetNodeOrNull<EventBusAdapter>(RootEventBusPath);
        if (_bus != null)
        {
            var callable = new Callable(this, nameof(OnDomainEventEmitted));
            if (!_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
            {
                _bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
            }
        }
    }

    private void ApplyLocalizedTexts()
    {
        if (_titleLabel != null)
        {
            _titleLabel.Text = TranslateOrFallback(UiSettlementTitleKey, "Game Ended");
        }

        if (_mainMenuButton != null)
        {
            _mainMenuButton.Text = TranslateOrFallback(UiSettlementMainMenuKey, "Main Menu");
        }

        if (_newGameButton != null)
        {
            _newGameButton.Text = TranslateOrFallback(UiSettlementNewGameKey, "New Game");
        }
    }

    private static string TranslateOrFallback(string key, string fallback)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return fallback;
        }

        var translated = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(translated) || string.Equals(translated, key, StringComparison.Ordinal))
        {
            return fallback;
        }

        return translated;
    }

    public override void _ExitTree()
    {
        if (_bus == null)
        {
            return;
        }

        try
        {
            var callable = new Callable(this, nameof(OnDomainEventEmitted));
            if (_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
            {
                _bus.Disconnect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
            }
        }
        catch (Exception)
        {
            // Best-effort cleanup (do not throw in _ExitTree).
        }
    }

    private void OnDomainEventEmitted(
        string type,
        string _source,
        string dataJson,
        string _id,
        string _specVersion,
        string _dataContentType,
        string _timestampIso)
    {
        if (!string.Equals(type, SanguoGameEnded.EventType, StringComparison.Ordinal))
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
            using var doc = JsonDocument.Parse(json, JsonParseOptions);
            ApplyGameEndedPayload(doc.RootElement);
        }
        catch (Exception)
        {
            // Invalid JSON: do not surface a settlement screen with potentially misleading data.
            // Keep the screen hidden and preserve previous state.
            return;
        }
    }

    private void ApplyGameEndedPayload(JsonElement root)
    {
        var winner = root.TryGetProperty("WinnerPlayerId", out var w) && w.ValueKind == JsonValueKind.String
            ? (w.GetString() ?? string.Empty)
            : string.Empty;

        var statsJson = root.TryGetProperty("StatsSnapshot", out var ss) && ss.ValueKind != JsonValueKind.Undefined && ss.ValueKind != JsonValueKind.Null
            ? ss.GetRawText()
            : string.Empty;

        if (_winnerLabel != null)
        {
            _winnerLabel.Text = winner;
        }

        if (_statsSnapshotLabel != null)
        {
            _statsSnapshotLabel.Text = statsJson;
        }

        Visible = true;
    }

    private void OnMainMenuPressed()
    {
        TryShowMainMenu();
        ClearText();
        Visible = false;
    }

    private void OnNewGamePressed()
    {
        TryShowMainMenu();

        var playButton = GetNodeOrNull<Button>(RootMainMenuPlayButtonPath);
        playButton?.EmitSignal(Button.SignalName.Pressed);

        ClearText();
        Visible = false;
    }

    private void TryShowMainMenu()
    {
        var menu = GetNodeOrNull<Control>(RootMainMenuPath);
        if (menu == null)
        {
            return;
        }

        if (menu is MainMenu typed)
        {
            typed.ShowMenu();
            return;
        }

        menu.Visible = true;
    }

    private void ClearText()
    {
        if (_winnerLabel != null)
        {
            _winnerLabel.Text = string.Empty;
        }

        if (_statsSnapshotLabel != null)
        {
            _statsSnapshotLabel.Text = string.Empty;
        }
    }
}
