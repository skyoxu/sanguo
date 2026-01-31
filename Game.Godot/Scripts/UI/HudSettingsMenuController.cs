using Godot;
using System;

namespace Game.Godot.Scripts.UI;

public sealed class HudSettingsMenuController
{
    private readonly Node _owner;
    private readonly Control _menu;
    private readonly Button _openButton;
    private readonly Button _resumeButton;
    private readonly Button _saveButton;
    private readonly Button _loadButton;
    private readonly Button _settingButton;
    private readonly Button _helpButton;
    private readonly Button _quitButton;
    private readonly Action _onSave;
    private readonly Action _onLoad;
    private readonly Action _onSetting;
    private readonly Action _onHelp;
    private readonly Action _onQuit;

    public HudSettingsMenuController(
        Node owner,
        Control menu,
        Button openButton,
        Button resumeButton,
        Button saveButton,
        Button loadButton,
        Button settingButton,
        Button helpButton,
        Button quitButton,
        Action onSave,
        Action onLoad,
        Action onSetting,
        Action onHelp,
        Action onQuit)
    {
        _owner = owner ?? throw new ArgumentNullException(nameof(owner));
        _menu = menu ?? throw new ArgumentNullException(nameof(menu));
        _openButton = openButton ?? throw new ArgumentNullException(nameof(openButton));
        _resumeButton = resumeButton ?? throw new ArgumentNullException(nameof(resumeButton));
        _saveButton = saveButton ?? throw new ArgumentNullException(nameof(saveButton));
        _loadButton = loadButton ?? throw new ArgumentNullException(nameof(loadButton));
        _settingButton = settingButton ?? throw new ArgumentNullException(nameof(settingButton));
        _helpButton = helpButton ?? throw new ArgumentNullException(nameof(helpButton));
        _quitButton = quitButton ?? throw new ArgumentNullException(nameof(quitButton));
        _onSave = onSave ?? throw new ArgumentNullException(nameof(onSave));
        _onLoad = onLoad ?? throw new ArgumentNullException(nameof(onLoad));
        _onSetting = onSetting ?? throw new ArgumentNullException(nameof(onSetting));
        _onHelp = onHelp ?? throw new ArgumentNullException(nameof(onHelp));
        _onQuit = onQuit ?? throw new ArgumentNullException(nameof(onQuit));
    }

    public void Bind()
    {
        _menu.Visible = false;
        _menu.ProcessMode = Node.ProcessModeEnum.WhenPaused;

        _openButton.Pressed += OnOpenPressed;
        _resumeButton.Pressed += OnResumePressed;
        _saveButton.Pressed += OnSavePressed;
        _loadButton.Pressed += OnLoadPressed;
        _settingButton.Pressed += OnSettingPressed;
        _helpButton.Pressed += OnHelpPressed;
        _quitButton.Pressed += OnQuitPressed;
    }

    public void Unbind()
    {
        _openButton.Pressed -= OnOpenPressed;
        _resumeButton.Pressed -= OnResumePressed;
        _saveButton.Pressed -= OnSavePressed;
        _loadButton.Pressed -= OnLoadPressed;
        _settingButton.Pressed -= OnSettingPressed;
        _helpButton.Pressed -= OnHelpPressed;
        _quitButton.Pressed -= OnQuitPressed;

        if (_owner.GetTree().Paused)
        {
            _owner.GetTree().Paused = false;
        }
        _menu.Visible = false;
    }

    private void OnOpenPressed()
    {
        _menu.Visible = true;
        _owner.GetTree().Paused = true;
    }

    private void OnResumePressed()
    {
        _menu.Visible = false;
        _owner.GetTree().Paused = false;
    }

    private void OnSavePressed() => _onSave();
    private void OnLoadPressed() => _onLoad();
    private void OnSettingPressed() => _onSetting();
    private void OnHelpPressed() => _onHelp();
    private void OnQuitPressed() => _onQuit();
}
