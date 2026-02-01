using Godot;
using System;

namespace Game.Godot.Scripts.UI;

public partial class HelpTutorial : Control
{
    private const string GroupName = "help_tutorial";
    private const string SectionLearningRoute = "help.tutorial.section.learning_route";
    private const string SectionTeamKnowledgeBase = "help.tutorial.section.team_knowledge_base";
    private const int LearningRouteLastIndex = 5; // steps 01..06
    private const int KnowledgeBaseFirstIndex = 6; // steps 07..08

    private static readonly string[] StepKeys =
    [
        "help.tutorial.step_01",
        "help.tutorial.step_02",
        "help.tutorial.step_03",
        "help.tutorial.step_04",
        "help.tutorial.step_05",
        "help.tutorial.step_06",
        "help.tutorial.step_07",
        "help.tutorial.step_08",
    ];

    private Label _sectionTitle = default!;
    private RichTextLabel _content = default!;
    private Button _btnPrev = default!;
    private Button _btnNext = default!;
    private Button _btnClose = default!;

    private int _stepIndex;

    public override void _Ready()
    {
        AddToGroup(GroupName);
        ProcessMode = Node.ProcessModeEnum.Always;
        MouseFilter = Control.MouseFilterEnum.Stop;

        _sectionTitle = GetNode<Label>("Panel/VBox/SectionTitle");
        _content = GetNode<RichTextLabel>("Panel/VBox/Content");
        _btnPrev = GetNode<Button>("Panel/VBox/HBox/BtnPrev");
        _btnNext = GetNode<Button>("Panel/VBox/HBox/BtnNext");
        _btnClose = GetNode<Button>("Panel/VBox/HBox/BtnClose");

        _btnPrev.Pressed += OnPrevPressed;
        _btnNext.Pressed += OnNextPressed;
        _btnClose.Pressed += OnClosePressed;

        _stepIndex = 0;
        RenderStep();
    }

    private void OnPrevPressed()
    {
        if (_stepIndex <= 0)
        {
            _stepIndex = 0;
        }
        else if (_stepIndex < KnowledgeBaseFirstIndex)
        {
            _stepIndex = Math.Max(0, _stepIndex - 1);
        }
        else
        {
            // Knowledge base pages loop within their own section.
            _stepIndex = _stepIndex == KnowledgeBaseFirstIndex ? StepKeys.Length - 1 : _stepIndex - 1;
        }
        RenderStep();
    }

    private void OnNextPressed()
    {
        if (_stepIndex < LearningRouteLastIndex)
        {
            _stepIndex++;
        }
        else if (_stepIndex == LearningRouteLastIndex)
        {
            // End of the learning route. Do not wrap to Step 01; transition to knowledge base.
            _stepIndex = KnowledgeBaseFirstIndex;
        }
        else
        {
            // Knowledge base pages loop within their own section.
            _stepIndex = _stepIndex >= StepKeys.Length - 1 ? KnowledgeBaseFirstIndex : _stepIndex + 1;
        }
        RenderStep();
    }

    private void OnClosePressed()
    {
        Visible = false;
    }

    private void RenderStep()
    {
        var key = StepKeys[_stepIndex];
        var sectionKey = _stepIndex <= LearningRouteLastIndex ? SectionLearningRoute : SectionTeamKnowledgeBase;
        _sectionTitle.Text = TranslateOrFallback(sectionKey);

        var text = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(text) || text == key)
        {
            text = key;
        }

        _content.Text = text;
        _btnPrev.Disabled = StepKeys.Length <= 1 || (_stepIndex == 0);
        _btnNext.Disabled = StepKeys.Length <= 1;
        _btnPrev.Text = TranslateOrFallback("ui.help.prev", "Prev");
        _btnNext.Text = TranslateOrFallback(_stepIndex == LearningRouteLastIndex ? "ui.help.finish" : "ui.help.next",
            _stepIndex == LearningRouteLastIndex ? "Finish" : "Next");
        _btnClose.Text = TranslateOrFallback("ui.help.close", "Close");
    }

    private static string TranslateOrFallback(string key)
    {
        var text = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(text) || text == key)
        {
            return key;
        }

        return text;
    }
}
