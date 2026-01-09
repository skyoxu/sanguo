using Godot;
using Game.Godot.Adapters;
using System;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public partial class MainMenu : Control
{
    private const string UiMenuStart = "ui.menu.start";
    private const string UiMenuSettings = "ui.menu.settings";
    private const string UiMenuQuit = "ui.menu.quit";
    private const string UiMenuLoad = "ui.menu.load";
    private const string UiMenuStartFailed = "ui.menu.start.failed";
    private const string UiMenuHelp = "ui.menu.help";

    private const string TurnStarted = "core.sanguo.game.turn.started";
    private const string HelpTutorialGroup = "help_tutorial";
    private const string HelpTutorialScenePath = "res://Game.Godot/Scenes/UI/HelpTutorial.tscn";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
        MaxDepth = 16,
    };

    private Button _btnPlay = default!;
    private Button _btnLoad = default!;
    private Button _btnSettings = default!;
    private Button? _btnHelp;
    private Button _btnQuit = default!;
    private Control _loadPanel = default!;
    private Label _statusLabel = default!;

    private EventBusAdapter? _bus;
    private bool _startPending;

    public override void _Ready()
    {
        _btnPlay = GetNode<Button>("VBox/BtnPlay");
        _btnLoad = GetNode<Button>("VBox/BtnLoad");
        _btnSettings = GetNode<Button>("VBox/BtnSettings");
        _btnHelp = GetNodeOrNull<Button>("VBox/BtnHelp");
        _btnQuit = GetNode<Button>("VBox/BtnQuit");
        _loadPanel = GetNode<Control>("LoadPanel");
        _statusLabel = GetNode<Label>("StatusLabel");

        _bus = GetNodeOrNull<EventBusAdapter>("/root/EventBus");
        if (_bus != null)
        {
            var callable = new Callable(this, nameof(OnDomainEventEmitted));
            if (!_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
            {
                _bus.Connect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
            }
        }

        _btnPlay.Pressed += OnPlayPressed;
        _btnLoad.Pressed += OnLoadPressed;
        _btnSettings.Pressed += OnSettingsPressed;
        if (_btnHelp != null)
        {
            _btnHelp.Pressed += OnHelpPressed;
        }
        _btnQuit.Pressed += OnQuitPressed;

        _loadPanel.Visible = false;
        _statusLabel.Visible = false;
        _statusLabel.Text = string.Empty;
        _startPending = false;
    }

    public override void _ExitTree()
    {
        if (_bus != null)
        {
            var callable = new Callable(this, nameof(OnDomainEventEmitted));
            if (_bus.IsConnected(EventBusAdapter.SignalName.DomainEventEmitted, callable))
            {
                _bus.Disconnect(EventBusAdapter.SignalName.DomainEventEmitted, callable);
            }
        }

        _bus = null;
    }

    public void ShowMenu() => Visible = true;
    public void HideMenu() => Visible = false;

    private void SetButtonsEnabled(bool enabled)
    {
        _btnPlay.Disabled = !enabled;
        _btnLoad.Disabled = !enabled;
        _btnSettings.Disabled = !enabled;
        if (_btnHelp != null)
        {
            _btnHelp.Disabled = !enabled;
        }
        _btnQuit.Disabled = !enabled;
    }

    private void ShowStatus(string message)
    {
        _statusLabel.Text = message ?? string.Empty;
        _statusLabel.Visible = !string.IsNullOrWhiteSpace(_statusLabel.Text);
    }

    private void ClearStatus()
    {
        _statusLabel.Text = string.Empty;
        _statusLabel.Visible = false;
    }

    private void Publish(string type, string source, string dataJson = "{}")
    {
        _bus?.PublishSimple(type, source, dataJson);
    }

    private void OnPlayPressed()
    {
        _startPending = true;
        ClearStatus();
        ShowStatus("Starting...");
        SetButtonsEnabled(false);
        Publish(UiMenuStart, "ui");
    }

    private void OnSettingsPressed()
    {
        Publish(UiMenuSettings, "ui");
    }

    private void OnLoadPressed()
    {
        Publish(UiMenuLoad, "ui");
        _loadPanel.Visible = true;
    }

    private void OnQuitPressed()
    {
        Publish(UiMenuQuit, "ui");
    }

    private void OnHelpPressed()
    {
        Publish(UiMenuHelp, "ui");
        ToggleHelpTutorial();
    }

    public void ToggleHelpTutorial()
    {
        var nodes = GetTree().GetNodesInGroup(HelpTutorialGroup);
        if (nodes.Count > 0)
        {
            var anyVisible = false;
            foreach (var node in nodes)
            {
                if (node is CanvasItem ci && ci.Visible)
                {
                    anyVisible = true;
                    break;
                }
            }

            var newVisible = !anyVisible;
            foreach (var node in nodes)
            {
                if (node is CanvasItem ci)
                {
                    ci.Visible = newVisible;
                }
            }

            return;
        }

        if (!ResourceLoader.Exists(HelpTutorialScenePath))
        {
            return;
        }

        var packed = GD.Load<PackedScene>(HelpTutorialScenePath);
        var instance = packed?.Instantiate();
        if (instance is CanvasItem canvas)
        {
            GetTree().Root.AddChild(canvas);
            canvas.Visible = true;
        }
    }

    private void OnDomainEventEmitted(string type, string _source, string dataJson, string _id, string _specVersion, string _dataContentType, string _timestampIso)
    {
        if (!_startPending)
        {
            return;
        }

        if (string.Equals(type, TurnStarted, StringComparison.Ordinal))
        {
            _startPending = false;
            ClearStatus();
            SetButtonsEnabled(true);
            HideMenu();
            return;
        }

        if (string.Equals(type, UiMenuStartFailed, StringComparison.Ordinal))
        {
            _startPending = false;
            SetButtonsEnabled(true);
            ShowMenu();
            ShowStatus("Start failed: " + (TryExtractStartFailedReason(dataJson) ?? "unknown"));
        }
    }

    private static string? TryExtractStartFailedReason(string dataJson)
    {
        if (string.IsNullOrWhiteSpace(dataJson))
        {
            return null;
        }

        try
        {
            using var doc = JsonDocument.Parse(dataJson, new JsonDocumentOptions
            {
                AllowTrailingCommas = true,
                CommentHandling = JsonCommentHandling.Skip,
                MaxDepth = 16,
            });

            if (doc.RootElement.ValueKind != JsonValueKind.Object)
            {
                return null;
            }

            if (doc.RootElement.TryGetProperty("reason", out var reason) && reason.ValueKind == JsonValueKind.String)
            {
                return reason.GetString();
            }

            if (doc.RootElement.TryGetProperty("message", out var msg) && msg.ValueKind == JsonValueKind.String)
            {
                return msg.GetString();
            }
        }
        catch
        {
        }

        try
        {
            var dict = JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string, object>>(dataJson, JsonOptions);
            if (dict == null) return null;
            if (dict.TryGetValue("reason", out var r) && r != null) return r.ToString();
            if (dict.TryGetValue("message", out var m) && m != null) return m.ToString();
        }
        catch
        {
        }

        return null;
    }
}
