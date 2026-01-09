using Godot;

namespace Game.Godot.Scripts.UI;

public partial class HelpTutorial : Control
{
    private const string GroupName = "help_tutorial";
    private const string SectionLearningRoute = "help.tutorial.section.learning_route";
    private const string SectionTeamKnowledgeBase = "help.tutorial.section.team_knowledge_base";

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
        _stepIndex = (_stepIndex - 1 + StepKeys.Length) % StepKeys.Length;
        RenderStep();
    }

    private void OnNextPressed()
    {
        _stepIndex = (_stepIndex + 1) % StepKeys.Length;
        RenderStep();
    }

    private void OnClosePressed()
    {
        Visible = false;
    }

    private void RenderStep()
    {
        var key = StepKeys[_stepIndex];
        var sectionKey = _stepIndex < 6 ? SectionLearningRoute : SectionTeamKnowledgeBase;
        _sectionTitle.Text = TranslateOrFallback(sectionKey);

        var text = TranslationServer.Translate(key);
        if (string.IsNullOrWhiteSpace(text) || text == key)
        {
            text = key;
        }

        _content.Text = text;
        _btnPrev.Disabled = StepKeys.Length <= 1;
        _btnNext.Disabled = StepKeys.Length <= 1;
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
