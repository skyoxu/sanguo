using Godot;

namespace Game.Godot.Examples.Components;

public partial class Modal : Control
{
    [Signal] public delegate void ConfirmedEventHandler();
    [Signal] public delegate void ClosedEventHandler();

    private Label _title = default!;
    private Label _message = default!;
    private Button _btnOk = default!;
    private Button _btnClose = default!;

    [Export] public string Title { get; set; } = "Notice";

    public override void _Ready()
    {
        _title = GetNode<Label>("Panel/VBox/Title");
        _message = GetNode<Label>("Panel/VBox/Message");
        _btnOk = GetNode<Button>("Panel/VBox/HBox/Ok");
        _btnClose = GetNode<Button>("Panel/VBox/HBox/Close");

        _title.Text = Title;
        _btnOk.Pressed += () => { EmitSignal(SignalName.Confirmed); Hide(); };
        _btnClose.Pressed += () => { EmitSignal(SignalName.Closed); Hide(); };

        Hide();
    }

    public void Open(string message)
    {
        _message.Text = message ?? string.Empty;
        Show();
    }
}

