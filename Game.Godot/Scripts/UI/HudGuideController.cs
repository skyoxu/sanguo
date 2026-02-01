using Godot;
using Game.Core.Contracts.Sanguo;
using System;

namespace Game.Godot.Scripts.UI;

public sealed class HudGuideController
{
    private const string GuideTitleKey = "help.tutorial.section.learning_route";
    private static readonly string[] GuideStepKeys =
    {
        "help.tutorial.step_01",
        "help.tutorial.step_02",
        "help.tutorial.step_03",
        "help.tutorial.step_04",
        "help.tutorial.step_05",
        "help.tutorial.step_06",
    };

    private readonly PanelContainer _guidePanel;
    private readonly Label _guideTitle;
    private readonly Label _guideText;
    private readonly GuideHighlightOverlay _guideOverlay;
    private readonly Button _diceButton;
    private readonly Label _moneyLabel;
    private readonly Control? _actionPanel;
    private readonly Control? _toastControl;
    private readonly Control? _logPanelControl;
    private readonly Func<string, Control?> _findControl;
    private readonly Func<string, string> _translateOrFallback;
    private int _guideStepIndex;

    public HudGuideController(
        PanelContainer guidePanel,
        Label guideTitle,
        Label guideText,
        GuideHighlightOverlay guideOverlay,
        Button diceButton,
        Label moneyLabel,
        Control? actionPanel,
        Control? toastControl,
        Control? logPanelControl,
        Func<string, Control?> findControl,
        Func<string, string> translateOrFallback)
    {
        _guidePanel = guidePanel ?? throw new ArgumentNullException(nameof(guidePanel));
        _guideTitle = guideTitle ?? throw new ArgumentNullException(nameof(guideTitle));
        _guideText = guideText ?? throw new ArgumentNullException(nameof(guideText));
        _guideOverlay = guideOverlay ?? throw new ArgumentNullException(nameof(guideOverlay));
        _diceButton = diceButton ?? throw new ArgumentNullException(nameof(diceButton));
        _moneyLabel = moneyLabel ?? throw new ArgumentNullException(nameof(moneyLabel));
        _actionPanel = actionPanel;
        _toastControl = toastControl;
        _logPanelControl = logPanelControl;
        _findControl = findControl ?? throw new ArgumentNullException(nameof(findControl));
        _translateOrFallback = translateOrFallback ?? throw new ArgumentNullException(nameof(translateOrFallback));
    }

    public void Initialize()
    {
        _guideStepIndex = 0;
        _guidePanel.Visible = false;
        _guideOverlay.Visible = false;
    }

    public void UpdateGuideHintForEventType(string type, bool enableText, bool enableHighlight)
    {
        if (string.IsNullOrWhiteSpace(type))
        {
            return;
        }

        if (string.Equals(type, SanguoGameStarted.EventType, StringComparison.Ordinal))
        {
            UpdateGuideStep(1, enableText, enableHighlight);
        }
        else if (string.Equals(type, SanguoGameTurnStarted.EventType, StringComparison.Ordinal))
        {
            UpdateGuideStep(2, enableText, enableHighlight);
        }
        else if (string.Equals(type, SanguoTokenMoved.EventType, StringComparison.Ordinal))
        {
            UpdateGuideStep(3, enableText, enableHighlight);
        }
        else if (string.Equals(type, SanguoCityBought.EventType, StringComparison.Ordinal)
                 || string.Equals(type, SanguoCityOwnerChanged.EventType, StringComparison.Ordinal)
                 || string.Equals(type, SanguoCityTollPaid.EventType, StringComparison.Ordinal))
        {
            UpdateGuideStep(4, enableText, enableHighlight);
        }
        else if (string.Equals(type, SanguoCombatStarted.EventType, StringComparison.Ordinal))
        {
            UpdateGuideStep(5, enableText, enableHighlight);
        }
        else if (string.Equals(type, SanguoGameEnded.EventType, StringComparison.Ordinal))
        {
            UpdateGuideStep(6, enableText, enableHighlight);
        }
    }

    private void UpdateGuideStep(int stepIndex, bool enableText, bool enableHighlight)
    {
        if (stepIndex <= _guideStepIndex || stepIndex < 1 || stepIndex > GuideStepKeys.Length)
        {
            return;
        }

        _guideStepIndex = stepIndex;
        if (enableText)
        {
            _guidePanel.Visible = true;
            _guideTitle.Text = _translateOrFallback(GuideTitleKey);
            var key = GuideStepKeys[stepIndex - 1];
            _guideText.Text = _translateOrFallback(key);
        }
        else
        {
            _guidePanel.Visible = false;
        }

        if (enableHighlight)
        {
            UpdateGuideHighlightForStep(stepIndex);
        }
        else
        {
            _guideOverlay.ClearHighlight();
            _guideOverlay.Visible = false;
        }
    }

    private void UpdateGuideHighlightForStep(int stepIndex)
    {
        var target = FindGuideTargetForStep(stepIndex);
        if (target == null)
        {
            _guideOverlay.ClearHighlight();
            _guideOverlay.Visible = false;
            return;
        }

        var globalRect = target.GetGlobalRect();
        var overlayRect = _guideOverlay.GetGlobalRect();
        var localPosition = globalRect.Position - overlayRect.Position;
        _guideOverlay.SetHighlightRect(new Rect2(localPosition, globalRect.Size));
        _guideOverlay.Visible = true;
    }

    private Control? FindGuideTargetForStep(int stepIndex)
    {
        return stepIndex switch
        {
            1 => _findControl("/root/Main/MenuLayer/MainMenu/ConfigCenter/NewGameConfig")
                 ?? _findControl("/root/Main/MenuLayer/MainMenu/MenuRow/MenuBox/BtnPlay"),
            2 => _diceButton,
            3 => _toastControl ?? _logPanelControl,
            4 => _actionPanel != null && _actionPanel.Visible ? _actionPanel : _moneyLabel,
            5 => _findControl("/root/Main/Overlays/SanguoBattleView/Panel")
                 ?? _findControl("/root/Main/SanguoBattleView/Panel"),
            6 => _findControl("/root/Main/Overlays/SettlementScreen/Center/Panel")
                 ?? _findControl("/root/Main/SettlementScreen/Center/Panel"),
            _ => null
        };
    }
}
