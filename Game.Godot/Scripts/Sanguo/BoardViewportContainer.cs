using Godot;

namespace Game.Godot.Scripts.Sanguo;

public partial class BoardViewportContainer : SubViewportContainer
{
    [Export]
    public NodePath ViewportPath { get; set; } = new NodePath("BoardViewport");

    [Export]
    public NodePath BoardViewPath { get; set; } = new NodePath("BoardViewport/SanguoBoardView");

    private SubViewport? _viewport;
    private Node? _boardView;

    public override void _Ready()
    {
        Stretch = false;
        SetProcessInput(true);
        SetProcessUnhandledInput(true);
        _viewport = GetNodeOrNull<SubViewport>(ViewportPath);
        _boardView = GetNodeOrNull<Node>(BoardViewPath);
        UpdateViewportSize();
        CallDeferred(nameof(UpdateViewportSize));
        Resized += OnResized;
    }

    public override void _ExitTree()
    {
        Resized -= OnResized;
    }

    private void OnResized()
    {
        UpdateViewportSize();
    }

    public override void _Input(InputEvent @event)
    {
        if (!IsMouseEventWithinContainer(@event))
        {
            return;
        }

        if (_viewport == null)
        {
            _viewport = GetNodeOrNull<SubViewport>(ViewportPath);
        }

        if (_viewport == null)
        {
            return;
        }

        _viewport.PushInput(@event, true);
    }

    public override void _GuiInput(InputEvent @event)
    {
        if (_viewport == null)
        {
            _viewport = GetNodeOrNull<SubViewport>(ViewportPath);
        }

        if (_viewport == null)
        {
            return;
        }

        _viewport.PushInput(@event, true);
        AcceptEvent();
    }

    private bool IsMouseEventWithinContainer(InputEvent @event)
    {
        if (@event is not InputEventMouse)
        {
            return false;
        }

        var rect = GetGlobalRect();
        return rect.HasPoint(GetGlobalMousePosition());
    }

    private void UpdateViewportSize()
    {
        if (_viewport == null)
        {
            _viewport = GetNodeOrNull<SubViewport>(ViewportPath);
        }

        if (_viewport == null)
        {
            return;
        }

        if (_boardView == null)
        {
            _boardView = GetNodeOrNull<Node>(BoardViewPath);
        }

        var size = Size;
        if (size.X < 1 || size.Y < 1)
        {
            return;
        }

        _viewport.Size = new Vector2I((int)size.X, (int)size.Y);

        if (_boardView != null && _boardView.HasMethod("ResetCameraView"))
        {
            _boardView.Call("ResetCameraView");
        }
    }
}
