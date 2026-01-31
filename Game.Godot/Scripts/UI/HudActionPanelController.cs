using Godot;
using Game.Godot.Adapters;
using Game.Core.Services.Sanguo;
using System;
using System.Collections.Generic;
using System.Text.Json;

namespace Game.Godot.Scripts.UI;

public sealed class HudActionPanelController
{
    private const string ActionBuild = "build";
    private const string UiTileActionSelectedEventType = "ui.sanguo.tile.action.selected";

    private readonly Control _actionPanel;
    private readonly Label _actionTitle;
    private readonly VBoxContainer _actionButtons;
    private readonly Button _skipButton;
    private readonly Button _diceButton;
    private readonly EventToast? _toast;
    private readonly EventBusAdapter? _bus;
    private readonly string _eventSource;

    private readonly Dictionary<int, TileInfo> _tilesByIndex = new();
    private readonly Dictionary<string, string> _cityOwnersByCityId = new(StringComparer.Ordinal);
    private bool _awaitingTileAction;
    private string _awaitingCorrelationId = string.Empty;
    private int _awaitingToIndex;
    private string? _activePlayerId;

    public HudActionPanelController(
        Control actionPanel,
        Label actionTitle,
        VBoxContainer actionButtons,
        Button skipButton,
        Button diceButton,
        EventToast? toast,
        EventBusAdapter? bus,
        string eventSource)
    {
        _actionPanel = actionPanel ?? throw new ArgumentNullException(nameof(actionPanel));
        _actionTitle = actionTitle ?? throw new ArgumentNullException(nameof(actionTitle));
        _actionButtons = actionButtons ?? throw new ArgumentNullException(nameof(actionButtons));
        _skipButton = skipButton ?? throw new ArgumentNullException(nameof(skipButton));
        _diceButton = diceButton ?? throw new ArgumentNullException(nameof(diceButton));
        _toast = toast;
        _bus = bus;
        _eventSource = string.IsNullOrWhiteSpace(eventSource) ? nameof(HudActionPanelController) : eventSource;
    }

    public void Bind()
    {
        _skipButton.Pressed += OnSkipTileActionPressed;
    }

    public void Unbind()
    {
        _skipButton.Pressed -= OnSkipTileActionPressed;
        HideTileActionPanel();
    }

    public void SetActivePlayerId(string? activePlayerId)
    {
        _activePlayerId = activePlayerId;
    }

    public bool IsAwaitingTileAction() => _awaitingTileAction;

    public void HandleActivePlayerChanged(string? previousActive, string? currentActive)
    {
        if (_awaitingTileAction && previousActive != null && !string.Equals(previousActive, currentActive, StringComparison.Ordinal))
        {
            HideTileActionPanel();
        }
    }

    public void LoadMapTiles(SanguoMapDefinition map)
    {
        _tilesByIndex.Clear();
        _cityOwnersByCityId.Clear();

        foreach (var tile in map.Tiles)
        {
            var actions = tile.Actions is null ? Array.Empty<string>() : new List<string>(tile.Actions).ToArray();
            _tilesByIndex[tile.PositionIndex] = new TileInfo(
                TileId: tile.TileId ?? string.Empty,
                TileType: tile.TileType ?? string.Empty,
                Name: tile.Name ?? string.Empty,
                Actions: actions);
        }
    }

    public void UpdateCityOwner(string buyerId, string cityId)
    {
        if (string.IsNullOrWhiteSpace(buyerId) || string.IsNullOrWhiteSpace(cityId))
        {
            return;
        }

        _cityOwnersByCityId[cityId] = buyerId;
    }

    public void HandleTokenMoved(HudTokenMovedDto dto)
    {
        if (_tilesByIndex.Count == 0)
        {
            return;
        }

        if (string.IsNullOrWhiteSpace(dto.PlayerId) || IsAiPlayerId(dto.PlayerId))
        {
            return;
        }

        if (_activePlayerId == null || !string.Equals(_activePlayerId, dto.PlayerId, StringComparison.Ordinal))
        {
            return;
        }

        if (!_tilesByIndex.TryGetValue(dto.ToIndex, out var tile))
        {
            return;
        }

        var correlationId = dto.CorrelationId ?? string.Empty;
        ShowTileActionPanel(dto.PlayerId, dto.ToIndex, correlationId, tile);
    }

    private void ShowTileActionPanel(string playerId, int toIndex, string correlationId, TileInfo tile)
    {
        var actions = FilterTileActionsForUi(playerId, tile);
        if (actions.Length == 0)
        {
            return;
        }

        _awaitingTileAction = true;
        _awaitingCorrelationId = correlationId ?? string.Empty;
        _awaitingToIndex = toIndex;

        _diceButton.Disabled = true;
        _actionTitle.Text = $"Tile: {tile.Name}";

        foreach (var child in _actionButtons.GetChildren())
        {
            if (child is Node n)
            {
                n.QueueFree();
            }
        }

        foreach (var action in actions)
        {
            var a = action ?? string.Empty;
            if (string.IsNullOrWhiteSpace(a))
            {
                continue;
            }

            var btn = new Button { Text = a, FocusMode = FocusModeEnum.All };
            btn.Pressed += () => OnTileActionPressed(playerId, toIndex, _awaitingCorrelationId, a);
            _actionButtons.AddChild(btn);
        }

        _actionPanel.Visible = true;
        _toast?.ShowMessage($"Choose action for '{tile.Name}' or Skip.");
    }

    private void OnTileActionPressed(string playerId, int toIndex, string correlationId, string action)
    {
        PublishTileActionSelected(playerId, toIndex, correlationId, action);
        HideTileActionPanel();
    }

    private void OnSkipTileActionPressed()
    {
        if (_activePlayerId == null)
        {
            return;
        }

        PublishTileActionSelected(_activePlayerId, _awaitingToIndex, _awaitingCorrelationId, "skip");
        HideTileActionPanel();
    }

    private void PublishTileActionSelected(string playerId, int toIndex, string correlationId, string action)
    {
        if (_bus == null)
        {
            return;
        }

        var payload = JsonSerializer.Serialize(new
        {
            GameId = "g1",
            PlayerId = playerId,
            ToIndex = toIndex,
            Action = action,
            CorrelationId = string.IsNullOrWhiteSpace(correlationId) ? Guid.NewGuid().ToString("N") : correlationId,
            CausationId = UiTileActionSelectedEventType,
        });

        _bus.PublishSimple(UiTileActionSelectedEventType, _eventSource, payload);
    }

    private void HideTileActionPanel()
    {
        _awaitingTileAction = false;
        _awaitingCorrelationId = string.Empty;
        _awaitingToIndex = 0;
        _actionPanel.Visible = false;
    }

    private static bool IsCityTile(TileInfo tile) =>
        string.Equals((tile.TileType ?? string.Empty).Trim(), "city", StringComparison.OrdinalIgnoreCase);

    private static bool IsBuildAction(string actionId) =>
        string.Equals((actionId ?? string.Empty).Trim(), ActionBuild, StringComparison.OrdinalIgnoreCase);

    private static bool IsBuyLandAction(string actionId) =>
        string.Equals((actionId ?? string.Empty).Trim(), "buy_land", StringComparison.OrdinalIgnoreCase);

    private string[] FilterTileActionsForUi(string playerId, TileInfo tile)
    {
        if (tile.Actions.Length == 0)
        {
            return Array.Empty<string>();
        }

        var isCity = IsCityTile(tile);
        var cityId = (tile.TileId ?? string.Empty).Trim();
        var ownerId = string.Empty;
        var hasOwner = isCity
            && !string.IsNullOrWhiteSpace(cityId)
            && _cityOwnersByCityId.TryGetValue(cityId, out ownerId);
        var isOwnedByActive = hasOwner && string.Equals(ownerId, playerId, StringComparison.Ordinal);

        var filtered = new List<string>(tile.Actions.Length);
        foreach (var raw in tile.Actions)
        {
            var a = (raw ?? string.Empty).Trim();
            if (string.IsNullOrWhiteSpace(a))
            {
                continue;
            }

            if (IsBuildAction(a))
            {
                if (!isOwnedByActive)
                {
                    continue;
                }
            }
            else if (IsBuyLandAction(a))
            {
                if (!isCity || hasOwner)
                {
                    continue;
                }
            }

            filtered.Add(a);
        }

        return filtered.ToArray();
    }

    private static bool IsAiPlayerId(string playerId)
        => !string.IsNullOrWhiteSpace(playerId) && playerId.StartsWith("ai-", StringComparison.OrdinalIgnoreCase);

    private readonly record struct TileInfo(string TileId, string TileType, string Name, string[] Actions);
}
