using Godot;
using System;

namespace Game.Godot.Scripts.Sanguo;

internal sealed class SanguoBoardLayout
{
    private int _totalPositions;
    private float _stepPixels;
    private Vector2 _origin;
    private bool _useSquareLayout;

    private int _layoutPerimeterSteps;
    private int _layoutEdgeSteps;

    internal int TotalPositions => _totalPositions;
    internal float StepPixels => _stepPixels;
    internal Vector2 Origin => _origin;
    internal bool UseSquareLayout => _useSquareLayout;

    internal int LayoutEdgeSteps
    {
        get
        {
            EnsureCache();
            return _layoutEdgeSteps;
        }
    }

    internal void Configure(int totalPositions, float stepPixels, Vector2 origin, bool useSquareLayout)
    {
        if (totalPositions < 0)
        {
            totalPositions = 0;
        }

        stepPixels = MathF.Max(0f, stepPixels);

        var changed = totalPositions != _totalPositions
            || Math.Abs(stepPixels - _stepPixels) > 0.0001f
            || origin != _origin
            || useSquareLayout != _useSquareLayout;

        _totalPositions = totalPositions;
        _stepPixels = stepPixels;
        _origin = origin;
        _useSquareLayout = useSquareLayout;

        if (changed)
        {
            _layoutPerimeterSteps = 0;
            _layoutEdgeSteps = 0;
        }
    }

    internal int ClampIndex(int index)
    {
        if (_totalPositions <= 0)
        {
            return 0;
        }

        if (index < 0)
        {
            return 0;
        }

        if (index >= _totalPositions)
        {
            return index % _totalPositions;
        }

        return index;
    }

    internal Vector2 GetBasePositionForIndex(int index)
    {
        if (_totalPositions <= 0)
        {
            return _origin;
        }

        var clamped = ClampIndex(index);

        if (!_useSquareLayout)
        {
            return _origin + new Vector2(clamped * _stepPixels, 0f);
        }

        EnsureCache();
        var stepIndex = (int)Math.Floor((double)clamped * _layoutPerimeterSteps / _totalPositions);
        if (stepIndex >= _layoutPerimeterSteps)
        {
            stepIndex = _layoutPerimeterSteps - 1;
        }

        var x = 0;
        var y = 0;
        var edge = _layoutEdgeSteps;
        if (stepIndex < edge)
        {
            x = stepIndex;
            y = 0;
        }
        else if (stepIndex < (2 * edge))
        {
            x = edge;
            y = stepIndex - edge;
        }
        else if (stepIndex < (3 * edge))
        {
            x = edge - (stepIndex - (2 * edge));
            y = edge;
        }
        else
        {
            x = 0;
            y = edge - (stepIndex - (3 * edge));
        }

        return _origin + new Vector2(x * _stepPixels, y * _stepPixels);
    }

    private void EnsureCache()
    {
        if (_layoutPerimeterSteps > 0 && _layoutEdgeSteps > 0)
        {
            return;
        }

        if (_totalPositions <= 0)
        {
            _layoutEdgeSteps = 1;
            _layoutPerimeterSteps = 4;
            return;
        }

        var sideLen = Math.Max(2, (int)Math.Ceiling(_totalPositions / 4.0) + 1);
        _layoutEdgeSteps = sideLen - 1;
        _layoutPerimeterSteps = 4 * _layoutEdgeSteps;
    }
}

