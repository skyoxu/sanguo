# Phase 7: LegacyUIFramework → Godot Control UI 迁移

> 状态: 设计阶段
> 预估工时: 15-20 天
> 风险等级: 中
> 前置条件: Phase 1-6 完成

---

## 目标

将 LegacyProject 的 LegacyUIFramework 19 + Tailwind CSS UI 迁移到 godotgame 的 Godot Control 节点系统，保持功能等价性与可测试性。

---

## 技术栈对比

| 层次 | LegacyProject (Web) | godotgame (Godot) |
|-----|---------------|------------------|
| UI框架 | LegacyUIFramework 19 (JSX) | Godot Control 节点 (.tscn) |
| 布局系统 | Flexbox / CSS Grid | Container 节点 (VBoxContainer, HBoxContainer, GridContainer) |
| 样式 | Tailwind CSS v4 | Godot Theme (.tres) + StyleBox |
| 事件 | LegacyUIFramework onClick / onChange | Godot Signals (pressed, text_changed) |
| 状态管理 | useState / useReducer | C# Properties + Signals |
| 组件复用 | LegacyUIFramework Components | 场景继承 + Composition |
| 响应式 | CSS媒体查询 | Anchor/Margin + viewport信号 |

---

## LegacyUIFramework 组件 → Godot Control 映射

### 基础组件映射表

| LegacyUIFramework 组件 | Godot Control | 说明 |
|-----------|--------------|------|
| `<div>` | `Control` / `Panel` | 通用容器 |
| `<button>` | `Button` | 按钮 |
| `<input type="text">` | `LineEdit` | 单行文本输入 |
| `<textarea>` | `TextEdit` | 多行文本输入 |
| `<label>` | `Label` | 文本标签 |
| `<img>` | `TextureRect` | 图片显示 |
| `<select>` | `OptionButton` | 下拉选择器 |
| `<input type="checkbox">` | `CheckBox` | 复选框 |
| `<input type="radio">` | `CheckButton` (互斥组) | 单选按钮 |
| `<progress>` | `ProgressBar` | 进度条 |
| `<ul>/<ol>` | `ItemList` / `Tree` | 列表/树形 |

### 布局容器映射

| LegacyUIFramework 布局 | Godot Container | 说明 |
|-----------|----------------|------|
| `display: flex; flex-direction: column` | `VBoxContainer` | 垂直布局 |
| `display: flex; flex-direction: row` | `HBoxContainer` | 水平布局 |
| `display: grid` | `GridContainer` | 网格布局 |
| `position: absolute` | Control + `set_position()` | 绝对定位 |
| `position: relative` | Control + Anchors | 相对定位 |

---

## 1. 基础组件迁移示例

### LegacyUIFramework Button → Godot Button

**LegacyUIFramework (LegacyProject)**:

```tsx
// src/components/ui/PrimaryButton.tsx

import { ButtonHTMLAttributes } from 'LegacyUIFramework';

interface PrimaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}

export function PrimaryButton({
  variant = 'primary',
  size = 'md',
  children,
  ...props
}: PrimaryButtonProps) {
  const baseClasses = 'font-bold rounded transition-colors';
  const variantClasses = {
    primary: 'bg-blue-500 hover:bg-blue-600 text-white',
    secondary: 'bg-gray-500 hover:bg-gray-600 text-white',
    danger: 'bg-red-500 hover:bg-red-600 text-white',
  };
  const sizeClasses = {
    sm: 'px-2 py-1 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]}`}
      {...props}
    >
      {children}
    </button>
  );
}
```

**Godot (godotgame)**:

**场景文件** (`Game.Godot/Scenes/UI/PrimaryButton.tscn`):

```
[gd_scene load_steps=4 format=3 uid="uid://button_primary"]

[ext_resource type="Script" path="res://Scripts/UI/PrimaryButton.cs" id="1"]
[ext_resource type="Theme" uid="uid://theme_default" path="res://Themes/default_theme.tres" id="2"]

[sub_resource type="StyleBoxFlat" id="1"]
bg_color = Color(0.2, 0.5, 1, 1)  # primary blue
corner_radius_top_left = 8
corner_radius_top_right = 8
corner_radius_bottom_left = 8
corner_radius_bottom_right = 8

[sub_resource type="StyleBoxFlat" id="2"]
bg_color = Color(0.3, 0.6, 1, 1)  # hover blue

[node name="PrimaryButton" type="Button"]
custom_minimum_size = Vector2(100, 40)
theme = ExtResource("2")
theme_override_styles/normal = SubResource("1")
theme_override_styles/hover = SubResource("2")
text = "Button"
script = ExtResource("1")
```

**C# 脚本** (`Game.Godot/Scripts/UI/PrimaryButton.cs`):

```csharp
using Godot;

namespace Game.Godot.Scripts.UI;

public partial class PrimaryButton : Button
{
    public enum ButtonVariant
    {
        Primary,
        Secondary,
        Danger
    }

    public enum ButtonSize
    {
        Small,
        Medium,
        Large
    }

    [Export]
    public ButtonVariant Variant { get; set; } = ButtonVariant.Primary;

    [Export]
    public ButtonSize Size { get; set; } = ButtonSize.Medium;

    public override void _Ready()
    {
        ApplyVariant();
        ApplySize();
    }

    private void ApplyVariant()
    {
        var normalStyle = new StyleBoxFlat();
        var hoverStyle = new StyleBoxFlat();

        switch (Variant)
        {
            case ButtonVariant.Primary:
                normalStyle.BgColor = new Color(0.2f, 0.5f, 1f); // blue-500
                hoverStyle.BgColor = new Color(0.3f, 0.6f, 1f); // blue-600
                break;
            case ButtonVariant.Secondary:
                normalStyle.BgColor = new Color(0.5f, 0.5f, 0.5f); // gray-500
                hoverStyle.BgColor = new Color(0.6f, 0.6f, 0.6f); // gray-600
                break;
            case ButtonVariant.Danger:
                normalStyle.BgColor = new Color(1f, 0.2f, 0.2f); // red-500
                hoverStyle.BgColor = new Color(1f, 0.3f, 0.3f); // red-600
                break;
        }

        // Apply corner radius
        normalStyle.CornerRadiusAll = 8;
        hoverStyle.CornerRadiusAll = 8;

        AddThemeStyleboxOverride("normal", normalStyle);
        AddThemeStyleboxOverride("hover", hoverStyle);
    }

    private void ApplySize()
    {
        var (minWidth, minHeight, fontSize) = Size switch
        {
            ButtonSize.Small => (80f, 32f, 14),
            ButtonSize.Medium => (100f, 40f, 16),
            ButtonSize.Large => (120f, 48f, 18),
            _ => (100f, 40f, 16)
        };

        CustomMinimumSize = new Vector2(minWidth, minHeight);
        AddThemeFontSizeOverride("font_size", fontSize);
    }
}
```

### LegacyUIFramework Form Input → Godot LineEdit

**LegacyUIFramework (LegacyProject)**:

```tsx
// src/components/ui/TextInput.tsx

import { InputHTMLAttributes, useState } from 'LegacyUIFramework';

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function TextInput({ label, error, ...props }: TextInputProps) {
  const [focused, setFocused] = useState(false);

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <input
        className={`
          px-3 py-2 border rounded
          ${focused ? 'border-blue-500 ring-2 ring-blue-200' : 'border-gray-300'}
          ${error ? 'border-red-500' : ''}
        `}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        {...props}
      />
      {error && (
        <span className="text-sm text-red-500">{error}</span>
      )}
    </div>
  );
}
```

**Godot (godotgame)**:

**场景文件** (`Game.Godot/Scenes/UI/TextInput.tscn`):

```
[gd_scene load_steps=3 format=3 uid="uid://input_text"]

[ext_resource type="Script" path="res://Scripts/UI/TextInput.cs" id="1"]

[node name="TextInput" type="VBoxContainer"]
script = ExtResource("1")

[node name="Label" type="Label" parent="."]
text = "Label"
visible = false

[node name="LineEdit" type="LineEdit" parent="."]
custom_minimum_size = Vector2(200, 40)
placeholder_text = ""

[node name="ErrorLabel" type="Label" parent="."]
text = ""
modulate = Color(1, 0.2, 0.2, 1)
visible = false
```

**C# 脚本** (`Game.Godot/Scripts/UI/TextInput.cs`):

```csharp
using Godot;

namespace Game.Godot.Scripts.UI;

public partial class TextInput : VBoxContainer
{
    [Signal]
    public delegate void TextChangedEventHandler(string newText);

    [Signal]
    public delegate void TextSubmittedEventHandler(string text);

    [Export]
    public string LabelText
    {
        get => _labelText;
        set
        {
            _labelText = value;
            UpdateLabel();
        }
    }

    [Export]
    public string PlaceholderText
    {
        get => _placeholderText;
        set
        {
            _placeholderText = value;
            UpdatePlaceholder();
        }
    }

    [Export]
    public string ErrorText
    {
        get => _errorText;
        set
        {
            _errorText = value;
            UpdateError();
        }
    }

    private string _labelText = string.Empty;
    private string _placeholderText = string.Empty;
    private string _errorText = string.Empty;

    private Label _label = null!;
    private LineEdit _lineEdit = null!;
    private Label _errorLabel = null!;

    public override void _Ready()
    {
        _label = GetNode<Label>("Label");
        _lineEdit = GetNode<LineEdit>("LineEdit");
        _errorLabel = GetNode<Label>("ErrorLabel");

        // Connect signals
        _lineEdit.TextChanged += OnLineEditTextChanged;
        _lineEdit.TextSubmitted += OnLineEditTextSubmitted;
        _lineEdit.FocusEntered += OnFocusEntered;
        _lineEdit.FocusExited += OnFocusExited;

        UpdateLabel();
        UpdatePlaceholder();
        UpdateError();
    }

    private void OnLineEditTextChanged(string newText)
    {
        EmitSignal(SignalName.TextChanged, newText);
    }

    private void OnLineEditTextSubmitted(string text)
    {
        EmitSignal(SignalName.TextSubmitted, text);
    }

    private void OnFocusEntered()
    {
        // Apply focus style
        var normalStyle = new StyleBoxFlat
        {
            BgColor = Colors.White,
            BorderColor = new Color(0.2f, 0.5f, 1f), // blue-500
            BorderWidthAll = 2,
            CornerRadiusAll = 4
        };
        _lineEdit.AddThemeStyleboxOverride("normal", normalStyle);
    }

    private void OnFocusExited()
    {
        // Remove focus style
        var normalStyle = new StyleBoxFlat
        {
            BgColor = Colors.White,
            BorderColor = new Color(0.7f, 0.7f, 0.7f), // gray-300
            BorderWidthAll = 1,
            CornerRadiusAll = 4
        };
        _lineEdit.AddThemeStyleboxOverride("normal", normalStyle);
    }

    private void UpdateLabel()
    {
        if (_label == null) return;

        if (string.IsNullOrEmpty(_labelText))
        {
            _label.Visible = false;
        }
        else
        {
            _label.Text = _labelText;
            _label.Visible = true;
        }
    }

    private void UpdatePlaceholder()
    {
        if (_lineEdit != null)
        {
            _lineEdit.PlaceholderText = _placeholderText;
        }
    }

    private void UpdateError()
    {
        if (_errorLabel == null) return;

        if (string.IsNullOrEmpty(_errorText))
        {
            _errorLabel.Visible = false;
        }
        else
        {
            _errorLabel.Text = _errorText;
            _errorLabel.Visible = true;

            // Apply error border to LineEdit
            var errorStyle = new StyleBoxFlat
            {
                BgColor = Colors.White,
                BorderColor = new Color(1f, 0.2f, 0.2f), // red-500
                BorderWidthAll = 2,
                CornerRadiusAll = 4
            };
            _lineEdit.AddThemeStyleboxOverride("normal", errorStyle);
        }
    }

    public string GetText() => _lineEdit?.Text ?? string.Empty;
    public void SetText(string text) => _lineEdit.Text = text;
    public void Clear() => _lineEdit.Text = string.Empty;
}
```

---

## 2. 布局系统迁移

### Flexbox → VBoxContainer/HBoxContainer

**LegacyUIFramework Flexbox (LegacyProject)**:

```tsx
// src/components/ui/UserCard.tsx

export function UserCard({ username, level, avatar }: UserCardProps) {
  return (
    <div className="flex flex-col gap-4 p-4 bg-white rounded shadow">
      <div className="flex items-center gap-3">
        <img
          src={avatar}
          alt={username}
          className="w-16 h-16 rounded-full"
        />
        <div className="flex flex-col">
          <span className="text-lg font-bold">{username}</span>
          <span className="text-sm text-gray-500">Level {level}</span>
        </div>
      </div>
      <div className="flex justify-between">
        <button className="px-4 py-2 bg-blue-500 text-white rounded">
          Profile
        </button>
        <button className="px-4 py-2 bg-gray-300 rounded">
          Settings
        </button>
      </div>
    </div>
  );
}
```

**Godot Container (godotgame)**:

**场景文件** (`Game.Godot/Scenes/UI/UserCard.tscn`):

```
[gd_scene load_steps=2 format=3 uid="uid://card_user"]

[ext_resource type="Script" path="res://Scripts/UI/UserCard.cs" id="1"]

[node name="UserCard" type="PanelContainer"]
custom_minimum_size = Vector2(300, 150)
script = ExtResource("1")

[node name="MarginContainer" type="MarginContainer" parent="."]
theme_override_constants/margin_left = 16
theme_override_constants/margin_top = 16
theme_override_constants/margin_right = 16
theme_override_constants/margin_bottom = 16

[node name="VBoxContainer" type="VBoxContainer" parent="MarginContainer"]
theme_override_constants/separation = 16

[node name="UserInfo" type="HBoxContainer" parent="MarginContainer/VBoxContainer"]
theme_override_constants/separation = 12

[node name="Avatar" type="TextureRect" parent="MarginContainer/VBoxContainer/UserInfo"]
custom_minimum_size = Vector2(64, 64)
stretch_mode = 5

[node name="Details" type="VBoxContainer" parent="MarginContainer/VBoxContainer/UserInfo"]
theme_override_constants/separation = 4

[node name="Username" type="Label" parent="MarginContainer/VBoxContainer/UserInfo/Details"]
text = "Username"
theme_override_font_sizes/font_size = 18

[node name="Level" type="Label" parent="MarginContainer/VBoxContainer/UserInfo/Details"]
text = "Level 1"
theme_override_font_sizes/font_size = 14
modulate = Color(0.5, 0.5, 0.5, 1)

[node name="Actions" type="HBoxContainer" parent="MarginContainer/VBoxContainer"]
alignment = 1
theme_override_constants/separation = 8

[node name="ProfileButton" type="Button" parent="MarginContainer/VBoxContainer/Actions"]
text = "Profile"

[node name="SettingsButton" type="Button" parent="MarginContainer/VBoxContainer/Actions"]
text = "Settings"
```

**C# 脚本** (`Game.Godot/Scripts/UI/UserCard.cs`):

```csharp
using Godot;

namespace Game.Godot.Scripts.UI;

public partial class UserCard : PanelContainer
{
    [Signal]
    public delegate void ProfilePressedEventHandler();

    [Signal]
    public delegate void SettingsPressedEventHandler();

    [Export]
    public string Username { get; set; } = "Username";

    [Export]
    public int Level { get; set; } = 1;

    [Export]
    public Texture2D? AvatarTexture { get; set; }

    private Label _usernameLabel = null!;
    private Label _levelLabel = null!;
    private TextureRect _avatarRect = null!;
    private Button _profileButton = null!;
    private Button _settingsButton = null!;

    public override void _Ready()
    {
        _usernameLabel = GetNode<Label>("MarginContainer/VBoxContainer/UserInfo/Details/Username");
        _levelLabel = GetNode<Label>("MarginContainer/VBoxContainer/UserInfo/Details/Level");
        _avatarRect = GetNode<TextureRect>("MarginContainer/VBoxContainer/UserInfo/Avatar");
        _profileButton = GetNode<Button>("MarginContainer/VBoxContainer/Actions/ProfileButton");
        _settingsButton = GetNode<Button>("MarginContainer/VBoxContainer/Actions/SettingsButton");

        // Connect signals
        _profileButton.Pressed += () => EmitSignal(SignalName.ProfilePressed);
        _settingsButton.Pressed += () => EmitSignal(SignalName.SettingsPressed);

        UpdateDisplay();
    }

    private void UpdateDisplay()
    {
        if (_usernameLabel != null)
            _usernameLabel.Text = Username;

        if (_levelLabel != null)
            _levelLabel.Text = $"Level {Level}";

        if (_avatarRect != null && AvatarTexture != null)
            _avatarRect.Texture = AvatarTexture;
    }

    public void SetUserData(string username, int level, Texture2D? avatar = null)
    {
        Username = username;
        Level = level;
        AvatarTexture = avatar;
        UpdateDisplay();
    }
}
```

---

## 3. 状态管理迁移

### LegacyUIFramework useState 鈫?Godot Properties + Signals

**LegacyUIFramework State (LegacyProject)**:

```tsx
// src/components/game/HealthBar.tsx

import { useState, useEffect } from 'LegacyUIFramework';

export function HealthBar({ maxHealth = 100 }: { maxHealth?: number }) {
  const [currentHealth, setCurrentHealth] = useState(maxHealth);
  const [isLowHealth, setIsLowHealth] = useState(false);

  useEffect(() => {
    setIsLowHealth(currentHealth < maxHealth * 0.3);
  }, [currentHealth, maxHealth]);

  const healthPercentage = (currentHealth / maxHealth) * 100;

  return (
    <div className="w-64 h-8 bg-gray-300 rounded overflow-hidden">
      <div
        className={`h-full transition-all ${
          isLowHealth ? 'bg-red-500' : 'bg-green-500'
        }`}
        style={{ width: `${healthPercentage}%` }}
      />
      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold">
        {currentHealth} / {maxHealth}
      </span>
    </div>
  );
}
```

**Godot Properties (godotgame)**:

**场景文件** (`Game.Godot/Scenes/UI/HealthBar.tscn`):

```
[gd_scene load_steps=2 format=3 uid="uid://bar_health"]

[ext_resource type="Script" path="res://Scripts/UI/HealthBar.cs" id="1"]

[node name="HealthBar" type="Control"]
custom_minimum_size = Vector2(256, 32)
script = ExtResource("1")

[node name="Background" type="Panel" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0

[node name="HealthFill" type="Panel" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 0.0
anchor_bottom = 1.0

[node name="Label" type="Label" parent="."]
layout_mode = 1
anchors_preset = 8
anchor_left = 0.5
anchor_top = 0.5
anchor_right = 0.5
anchor_bottom = 0.5
offset_left = -50.0
offset_top = -10.0
offset_right = 50.0
offset_bottom = 10.0
text = "100 / 100"
horizontal_alignment = 1
vertical_alignment = 1
```

**C# 脚本** (`Game.Godot/Scripts/UI/HealthBar.cs`):

```csharp
using Godot;

namespace Game.Godot.Scripts.UI;

public partial class HealthBar : Control
{
    [Signal]
    public delegate void HealthChangedEventHandler(int oldHealth, int newHealth);

    [Signal]
    public delegate void HealthDepletedEventHandler();

    [Export]
    public int MaxHealth
    {
        get => _maxHealth;
        set
        {
            _maxHealth = value;
            UpdateDisplay();
        }
    }

    [Export]
    public int CurrentHealth
    {
        get => _currentHealth;
        set
        {
            int oldHealth = _currentHealth;
            _currentHealth = Mathf.Clamp(value, 0, _maxHealth);

            if (_currentHealth != oldHealth)
            {
                EmitSignal(SignalName.HealthChanged, oldHealth, _currentHealth);

                if (_currentHealth == 0)
                {
                    EmitSignal(SignalName.HealthDepleted);
                }

                UpdateDisplay();
            }
        }
    }

    private int _maxHealth = 100;
    private int _currentHealth = 100;

    private Panel _background = null!;
    private Panel _healthFill = null!;
    private Label _label = null!;

    private readonly Color _normalHealthColor = new(0.2f, 0.8f, 0.2f); // green
    private readonly Color _lowHealthColor = new(1f, 0.2f, 0.2f); // red
    private readonly float _lowHealthThreshold = 0.3f;

    public override void _Ready()
    {
        _background = GetNode<Panel>("Background");
        _healthFill = GetNode<Panel>("HealthFill");
        _label = GetNode<Label>("Label");

        // Style background
        var bgStyle = new StyleBoxFlat
        {
            BgColor = new Color(0.3f, 0.3f, 0.3f), // gray
            CornerRadiusAll = 4
        };
        _background.AddThemeStyleboxOverride("panel", bgStyle);

        UpdateDisplay();
    }

    private void UpdateDisplay()
    {
        if (_healthFill == null || _label == null) return;

        // Calculate health percentage
        float healthPercentage = (float)_currentHealth / _maxHealth;
        bool isLowHealth = healthPercentage < _lowHealthThreshold;

        // Update fill width
        _healthFill.AnchorRight = healthPercentage;

        // Update fill color
        var fillStyle = new StyleBoxFlat
        {
            BgColor = isLowHealth ? _lowHealthColor : _normalHealthColor,
            CornerRadiusAll = 4
        };
        _healthFill.AddThemeStyleboxOverride("panel", fillStyle);

        // Update label
        _label.Text = $"{_currentHealth} / {_maxHealth}";
    }

    public void TakeDamage(int amount)
    {
        CurrentHealth -= amount;
    }

    public void Heal(int amount)
    {
        CurrentHealth += amount;
    }

    public void ResetHealth()
    {
        CurrentHealth = MaxHealth;
    }
}
```

---

## 4. Godot Theme 系统

### 创建主题资源

**Theme 文件** (`Game.Godot/Themes/default_theme.tres`):

```
[gd_resource type="Theme" load_steps=10 format=3 uid="uid://theme_default"]

[sub_resource type="StyleBoxFlat" id="button_normal"]
bg_color = Color(0.2, 0.5, 1, 1)
corner_radius_all = 8

[sub_resource type="StyleBoxFlat" id="button_hover"]
bg_color = Color(0.3, 0.6, 1, 1)
corner_radius_all = 8

[sub_resource type="StyleBoxFlat" id="button_pressed"]
bg_color = Color(0.1, 0.4, 0.9, 1)
corner_radius_all = 8

[sub_resource type="StyleBoxFlat" id="lineedit_normal"]
bg_color = Color(1, 1, 1, 1)
border_width_all = 1
border_color = Color(0.7, 0.7, 0.7, 1)
corner_radius_all = 4

[sub_resource type="StyleBoxFlat" id="lineedit_focus"]
bg_color = Color(1, 1, 1, 1)
border_width_all = 2
border_color = Color(0.2, 0.5, 1, 1)
corner_radius_all = 4

[sub_resource type="StyleBoxFlat" id="panel"]
bg_color = Color(0.95, 0.95, 0.95, 1)
corner_radius_all = 8

[resource]
Button/styles/normal = SubResource("button_normal")
Button/styles/hover = SubResource("button_hover")
Button/styles/pressed = SubResource("button_pressed")
Button/font_sizes/font_size = 16
Button/colors/font_color = Color(1, 1, 1, 1)

LineEdit/styles/normal = SubResource("lineedit_normal")
LineEdit/styles/focus = SubResource("lineedit_focus")
LineEdit/font_sizes/font_size = 16
LineEdit/colors/font_color = Color(0, 0, 0, 1)

Panel/styles/panel = SubResource("panel")

Label/font_sizes/font_size = 16
Label/colors/font_color = Color(0.2, 0.2, 0.2, 1)
```

### 应用 Theme

**方式 1：在场景中应用**

```
[node name="UI" type="Control"]
theme = preload("res://Themes/default_theme.tres")
```

**方式 2：在项目设置中全局应用**

```ini
# project.godot

[gui]

theme/custom="res://Themes/default_theme.tres"
```

**方式 3：通过代码应用**

```csharp
public override void _Ready()
{
    var theme = GD.Load<Theme>("res://Themes/default_theme.tres");
    Theme = theme;
}
```

---

## 5. 响应式布局

### Anchor 与 Margin 系统

**Godot Anchor 预设**:

| Preset | 说明 | Anchor Values |
|--------|------|--------------|
| Top Left | 左上角 | (0, 0, 0, 0) |
| Top Right | 右上角 | (1, 0, 1, 0) |
| Bottom Left | 左下角 | (0, 1, 0, 1) |
| Bottom Right | 右下角 | (1, 1, 1, 1) |
| Center | 居中 | (0.5, 0.5, 0.5, 0.5) |
| Full Rect | 填满父容器 | (0, 0, 1, 1) |

**响应式示例**:

```csharp
// Game.Godot/Scripts/UI/ResponsivePanel.cs

using Godot;

namespace Game.Godot.Scripts.UI;

public partial class ResponsivePanel : Panel
{
    [Export]
    public Vector2 MinSize { get; set; } = new(800, 600);

    [Export]
    public Vector2 MaxSize { get; set; } = new(1920, 1080);

    public override void _Ready()
    {
        GetViewport().SizeChanged += OnViewportSizeChanged;
        OnViewportSizeChanged();
    }

    private void OnViewportSizeChanged()
    {
        var viewportSize = GetViewportRect().Size;

        // Calculate responsive size
        var width = Mathf.Clamp(viewportSize.X * 0.8f, MinSize.X, MaxSize.X);
        var height = Mathf.Clamp(viewportSize.Y * 0.8f, MinSize.Y, MaxSize.Y);

        Size = new Vector2(width, height);

        // Center in viewport
        Position = new Vector2(
            (viewportSize.X - width) / 2,
            (viewportSize.Y - height) / 2
        );
    }

    public override void _ExitTree()
    {
        GetViewport().SizeChanged -= OnViewportSizeChanged;
    }
}
```

---

## 6. 表单处理与验证

### LegacyUIFramework Form → Godot Form Container

**LegacyUIFramework Form (LegacyProject)**:

```tsx
// src/components/forms/LoginForm.tsx

import { useState, FormEvent } from 'LegacyUIFramework';
import { TextInput } from '../ui/TextInput';
import { PrimaryButton } from '../ui/PrimaryButton';

export function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    }

    if (password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    if (validate()) {
      console.log('Login:', { username, password });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-80">
      <TextInput
        label="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        error={errors.username}
      />
      <TextInput
        label="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={errors.password}
      />
      <PrimaryButton type="submit">
        Login
      </PrimaryButton>
    </form>
  );
}
```

**Godot Form (godotgame)**:

**场景文件** (`Game.Godot/Scenes/UI/LoginForm.tscn`):

```
[gd_scene load_steps=3 format=3 uid="uid://form_login"]

[ext_resource type="Script" path="res://Scripts/UI/LoginForm.cs" id="1"]
[ext_resource type="PackedScene" uid="uid://input_text" path="res://Scenes/UI/TextInput.tscn" id="2"]

[node name="LoginForm" type="VBoxContainer"]
custom_minimum_size = Vector2(320, 0)
theme_override_constants/separation = 16
script = ExtResource("1")

[node name="UsernameInput" parent="." instance=ExtResource("2")]
label_text = "Username"

[node name="PasswordInput" parent="." instance=ExtResource("2")]
label_text = "Password"
secret = true

[node name="LoginButton" type="Button" parent="."]
text = "Login"
```

**C# 脚本** (`Game.Godot/Scripts/UI/LoginForm.cs`):

```csharp
using Godot;
using System.Collections.Generic;

namespace Game.Godot.Scripts.UI;

public partial class LoginForm : VBoxContainer
{
    [Signal]
    public delegate void LoginSubmittedEventHandler(string username, string password);

    [Signal]
    public delegate void ValidationFailedEventHandler(Dictionary<string, string> errors);

    private TextInput _usernameInput = null!;
    private TextInput _passwordInput = null!;
    private Button _loginButton = null!;

    public override void _Ready()
    {
        _usernameInput = GetNode<TextInput>("UsernameInput");
        _passwordInput = GetNode<TextInput>("PasswordInput");
        _loginButton = GetNode<Button>("LoginButton");

        // Connect signals
        _loginButton.Pressed += OnLoginButtonPressed;

        // Optional: Submit on Enter key
        _passwordInput.TextSubmitted += (_) => OnLoginButtonPressed();
    }

    private void OnLoginButtonPressed()
    {
        if (Validate())
        {
            string username = _usernameInput.GetText();
            string password = _passwordInput.GetText();

            EmitSignal(SignalName.LoginSubmitted, username, password);
        }
    }

    private bool Validate()
    {
        var errors = new Dictionary<string, string>();

        string username = _usernameInput.GetText();
        string password = _passwordInput.GetText();

        // Clear previous errors
        _usernameInput.ErrorText = string.Empty;
        _passwordInput.ErrorText = string.Empty;

        // Validate username
        if (username.Length < 3)
        {
            string errorMsg = "Username must be at least 3 characters";
            _usernameInput.ErrorText = errorMsg;
            errors["username"] = errorMsg;
        }

        // Validate password
        if (password.Length < 6)
        {
            string errorMsg = "Password must be at least 6 characters";
            _passwordInput.ErrorText = errorMsg;
            errors["password"] = errorMsg;
        }

        if (errors.Count > 0)
        {
            EmitSignal(SignalName.ValidationFailed, errors);
            return false;
        }

        return true;
    }

    public void ClearForm()
    {
        _usernameInput.Clear();
        _passwordInput.Clear();
        _usernameInput.ErrorText = string.Empty;
        _passwordInput.ErrorText = string.Empty;
    }
}
```

---

## 7. 列表与可滚动内容

### LegacyUIFramework List → Godot ScrollContainer + VBoxContainer

**LegacyUIFramework List (LegacyProject)**:

```tsx
// src/components/ui/UserList.tsx

interface User {
  id: string;
  username: string;
  level: number;
}

export function UserList({ users }: { users: User[] }) {
  return (
    <div className="h-96 overflow-y-auto bg-gray-100 rounded p-4">
      <div className="flex flex-col gap-2">
        {users.map(user => (
          <div
            key={user.id}
            className="flex items-center gap-3 p-3 bg-white rounded shadow"
          >
            <span className="font-bold">{user.username}</span>
            <span className="text-sm text-gray-500">Lv.{user.level}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Godot List (godotgame)**:

**场景文件** (`Game.Godot/Scenes/UI/UserList.tscn`):

```
[gd_scene load_steps=2 format=3 uid="uid://list_user"]

[ext_resource type="Script" path="res://Scripts/UI/UserList.cs" id="1"]

[node name="UserList" type="Panel"]
custom_minimum_size = Vector2(400, 384)
script = ExtResource("1")

[node name="MarginContainer" type="MarginContainer" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
theme_override_constants/margin_left = 16
theme_override_constants/margin_top = 16
theme_override_constants/margin_right = 16
theme_override_constants/margin_bottom = 16

[node name="ScrollContainer" type="ScrollContainer" parent="MarginContainer"]
layout_mode = 2

[node name="VBoxContainer" type="VBoxContainer" parent="MarginContainer/ScrollContainer"]
layout_mode = 2
size_flags_horizontal = 3
theme_override_constants/separation = 8
```

**C# 脚本** (`Game.Godot/Scripts/UI/UserList.cs`):

```csharp
using Godot;
using System.Collections.Generic;

namespace Game.Godot.Scripts.UI;

public partial class UserList : Panel
{
    [Signal]
    public delegate void UserSelectedEventHandler(string userId);

    private VBoxContainer _container = null!;

    public override void _Ready()
    {
        _container = GetNode<VBoxContainer>("MarginContainer/ScrollContainer/VBoxContainer");
    }

    public void SetUsers(List<UserData> users)
    {
        // Clear existing items
        foreach (Node child in _container.GetChildren())
        {
            child.QueueFree();
        }

        // Add new items
        foreach (var user in users)
        {
            var userItem = CreateUserItem(user);
            _container.AddChild(userItem);
        }
    }

    private Control CreateUserItem(UserData user)
    {
        var panel = new PanelContainer();
        panel.CustomMinimumSize = new Vector2(0, 60);

        var hbox = new HBoxContainer();
        hbox.AddThemeConstantOverride("separation", 12);

        var usernameLabel = new Label
        {
            Text = user.Username,
            SizeFlagsHorizontal = SizeFlags.ExpandFill
        };
        usernameLabel.AddThemeFontSizeOverride("font_size", 16);

        var levelLabel = new Label
        {
            Text = $"Lv.{user.Level}",
            Modulate = new Color(0.5f, 0.5f, 0.5f)
        };
        levelLabel.AddThemeFontSizeOverride("font_size", 14);

        hbox.AddChild(usernameLabel);
        hbox.AddChild(levelLabel);

        var margin = new MarginContainer();
        margin.AddThemeConstantOverride("margin_left", 12);
        margin.AddThemeConstantOverride("margin_top", 8);
        margin.AddThemeConstantOverride("margin_right", 12);
        margin.AddThemeConstantOverride("margin_bottom", 8);
        margin.AddChild(hbox);

        panel.AddChild(margin);

        // Make clickable
        var button = new Button
        {
            Text = string.Empty,
            Flat = true
        };
        button.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        button.Pressed += () => EmitSignal(SignalName.UserSelected, user.Id);

        panel.AddChild(button);

        return panel;
    }

    public class UserData
    {
        public string Id { get; set; } = string.Empty;
        public string Username { get; set; } = string.Empty;
        public int Level { get; set; }
    }
}
```

---

## 8. 测试策略

### GdUnit4 UI 测试

```csharp
// C# equivalent (Godot 4 + C# + GdUnit4)
using Godot;
using System.Threading.Tasks;

public partial class ExampleTest
{
    public async Task Example()
    {
        var scene = GD.Load<PackedScene>("res://Game.Godot/Scenes/MainScene.tscn");
        var inst = scene?.Instantiate();
        var tree = (SceneTree)Engine.GetMainLoop();
        tree.Root.AddChild(inst);
        await ToSignal(tree, SceneTree.SignalName.ProcessFrame);
        inst.QueueFree();
    }
}
```

### xUnit UI Logic 测试

```csharp
// Game.Core.Tests/UI/HealthBarLogicTests.cs

using FluentAssertions;
using Game.Core.Tests.Fakes;
using Xunit;

namespace Game.Core.Tests.UI;

public class HealthBarLogicTests
{
    [Fact]
    public void CurrentHealth_ShouldClampToZero()
    {
        // Arrange
        var healthBar = new FakeHealthBar(maxHealth: 100);

        // Act
        healthBar.TakeDamage(150);

        // Assert
        healthBar.CurrentHealth.Should().Be(0);
    }

    [Fact]
    public void CurrentHealth_ShouldClampToMax()
    {
        // Arrange
        var healthBar = new FakeHealthBar(maxHealth: 100);
        healthBar.TakeDamage(50);

        // Act
        healthBar.Heal(100);

        // Assert
        healthBar.CurrentHealth.Should().Be(100);
    }

    [Fact]
    public void HealthChanged_ShouldEmitSignal()
    {
        // Arrange
        var healthBar = new FakeHealthBar(maxHealth: 100);
        int oldHealthReceived = 0;
        int newHealthReceived = 0;

        healthBar.HealthChangedEvent += (oldHealth, newHealth) =>
        {
            oldHealthReceived = oldHealth;
            newHealthReceived = newHealth;
        };

        // Act
        healthBar.TakeDamage(30);

        // Assert
        oldHealthReceived.Should().Be(100);
        newHealthReceived.Should().Be(70);
    }
}
```

---

## 9. Accessibility (可访问性)

### 键盘导航支持

```csharp
// Game.Godot/Scripts/UI/AccessibleButton.cs

using Godot;

namespace Game.Godot.Scripts.UI;

public partial class AccessibleButton : Button
{
    [Export]
    public string AccessibilityLabel { get; set; } = string.Empty;

    [Export]
    public string AccessibilityHint { get; set; } = string.Empty;

    public override void _Ready()
    {
        FocusMode = FocusModeEnum.All;

        // Set accessibility properties
        if (!string.IsNullOrEmpty(AccessibilityLabel))
        {
            TooltipText = AccessibilityLabel;
        }

        // Visual focus indicator
        FocusEntered += OnFocusEntered;
        FocusExited += OnFocusExited;
    }

    private void OnFocusEntered()
    {
        var focusStyle = new StyleBoxFlat
        {
            BgColor = GetThemeColor("font_color", "Button"),
            BorderColor = new Color(1, 1, 0), // Yellow border
            BorderWidthAll = 3,
            CornerRadiusAll = 8
        };
        AddThemeStyleboxOverride("focus", focusStyle);
    }

    private void OnFocusExited()
    {
        RemoveThemeStyleboxOverride("focus");
    }

    public override void _UnhandledKeyInput(InputEvent @event)
    {
        if (@event is InputEventKey keyEvent && keyEvent.Pressed)
        {
            if (keyEvent.Keycode == Key.Enter || keyEvent.Keycode == Key.Space)
            {
                EmitSignal(SignalName.Pressed);
                AcceptEvent();
            }
        }
    }
}
```

---

## 10. CI 集成

### UI 测试 (GitHub Actions)

```yaml
# .github/workflows/ui-tests.yml

name: UI Tests

on: [push, pull_request]

jobs:
  ui-tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Godot
        uses: chickensoft-games/setup-godot@v1
        with:
          version: 4.5.0
          use-dotnet: true

      - name: Setup .NET 8
        uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '8.0.x'

      - name: Run GdUnit4 UI Tests
        run: |
          godot --headless --path . `
            --script res://addons/gdUnit4/bin/GdUnitCmdTool.cs `
            --conf res://GdUnitRunner.cfg `
            --output ./TestResults/gdunit4-ui-results.xml

      - name: Upload UI Test Results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: ui-test-results
          path: TestResults/gdunit4-ui-results.xml
```

---

## 完成标准

- [ ] 所有核心 UI 组件已迁移（Button, TextInput, Label, Panel, List）
- [ ] 布局系统已从 Flexbox 迁移到 Container 节点
- [ ] Theme 资源已创建并应用
- [ ] 响应式布局支持 (Anchor/Margin)
- [ ] 表单验证逻辑已迁移
- [ ] GdUnit4 UI 测试覆盖主要场景
- [ ] 键盘导航与 Accessibility 支持
- [ ] CI 集成 UI 测试通过

---

## 下一步

完成本阶段后，继续：

-> [Phase-8-Scene-Design.md](Phase-8-Scene-Design.md) — Scene Tree 与 Node 设计

## 最小迁移清单 / Minimal UI Checklist

- 基础控件：Button/Label/LineEdit/TextEdit/OptionButton/ProgressBar（已建 PrimaryButton 示例：`Game.Godot/Scenes/UI/PrimaryButton.tscn`）
- 布局容器：VBoxContainer/HBoxContainer/GridContainer（遵循简洁锚点与最小 margin）
- 命名约定：`<Role>_<Area>_<Action>`，示例：`Btn_Menu_Start`, `Lbl_HUD_Score`
- 资源组织：`Game.Godot/Scenes/UI/**` 与 `Game.Godot/Scripts/UI/**` 一一对应
- 信号约定：`pressed`, `text_changed` 等统一连接至场景脚本或适配层

## 事件与信号 / Events & Signals

- 统一通过 `/root/EventBus` 发出领域事件：`bus.PublishSimple(type, source, data_json)`
- UI → 域：控件信号在脚本中转换为领域指令/事件；域 → UI：订阅事件总线刷新视图


## 新增 UI 场景 / New Scenes (Windows-only)

- MainMenu：`Game.Godot/Scenes/UI/MainMenu.tscn`（事件：ui.menu.start/settings/quit，通过 `/root/EventBus`）
- HUD：`Game.Godot/Scenes/UI/HUD.tscn`（监听 `/root/EventBus` 的 `DomainEventEmitted`，更新 Score/HP）
- InventoryPanel：`Game.Godot/Scenes/UI/InventoryPanel.tscn`（与 `/root/DataStore` 交互，保存/加载简单 JSON）
- 已在 `Game.Godot/Scenes/Main.tscn` 挂载以上场景，作为最小迁移示例，不影响原有演示按钮。


## 主题统一 / Theme

- 主题文件：`Game.Godot/Themes/default_theme.tres`（按钮/面板样式与文本颜色）。
- 应用方式：`Game.Godot/Scenes/Main.tscn` 将主题绑定在根节点，子节点继承；无需逐节点设置。
- 字体：当前使用系统默认字体；如需项目字体，请添加 `.ttf/.otf` 到 `Game.Godot/Fonts/` 后在 Theme 中设置。


## 字体与 Theme 应用 / Fonts

- 将字体放在 `Game.Godot/Fonts/`（如 NotoSans-Regular.ttf），`ThemeApplier` 会在运行时统一覆盖字体；未提供时使用系统默认。
- 配置：在 `Game.Godot/Scenes/Main.tscn` 中选择 `ThemeApplier` 节点，设置导出属性 `FontPath`。

## UI 集成测试示例 / Integration Test

- `tests/UI/Main_Integration_Tests.gd`：点击 MainMenu 的 Play，断言收到 `game.started` 事件（领域驱动链路已打通）。


## 新增面板 / New Panels

- ScorePanel：`Game.Godot/Scenes/UI/ScorePanel.tscn`（+10/+50，事件回传 `core.score.updated`/`score.changed`）
- CombatPanel：`Game.Godot/Scenes/UI/CombatPanel.tscn`（-5/-20，事件回传 `player.health.changed` / Fallback: `player.damaged`）
- 已挂载到 `Main.tscn`，与 HUD/Inventory/Settings 协同展示。


## 图形质量映射 / Graphics Quality Mapping

- low：VSync Off，MSAA 2D/3D 关闭（Viewport.msaa_2d/msaa_3d = 0）
- medium：VSync On，MSAA≈2x（Viewport.msaa_2d/msaa_3d = 1）
- high：VSync On，MSAA≈4x（Viewport.msaa_2d/msaa_3d = 2；如需 8x 可改为 3）
- 保存到 `settings` 表（graphics_quality），加载时自动应用；运行中变更即时生效。

## UI 缩放与窗口 / UI Scaling & Window

- 默认窗口大小：1280x720，`project.godot` → `[display]` → `window/size/viewport_width|height`。
- Stretch：`window/stretch/mode="viewport"`，`window/stretch/aspect="keep"`（适合 UI 场景，保持比例）。
- 若需 DPI 缩放或动态缩放，可在根节点按需调整 `content_scale_factor`。

## 翻译资源 / Translations

- 目录：`Game.Godot/Translations/`（放置 `.translation/.po/.csv` 文件，并在 Project Settings 注册）。
- 运行时：`SettingsLoader` 按 `settings.language` 调用 `TranslationServer.SetLocale(...)`。


## Inventory 面板仓储化 / Inventory via Repository

- `InventoryPanel` 默认启用 `UseRepository=true`，优先使用 `SqlInventoryRepository`（专用表 `inventory_items`）。
- 兼容回退：未检测到 SqlDb 时，回退到 DataStore JSON（旧行为保留，便于演示/离线）。
- 集成测试：`tests/UI/InventoryPanel_Repo_Tests.gd` 覆盖保存/加载。



### 示例面板迁移 / Examples
- 示例场景已迁移至 Game.Godot/Examples/UI/**（Score/Combat/Inventory），默认不在 Main 载入。
- GdUnit 示例测试默认跳过。设置 TEMPLATE_DEMO=1 可启用示例测试。


## 文件组织与命名规范 / File Layout & Naming

- 目录：
  - `Game.Godot/Scenes/Screens/**`：可导航的 Screen（每个 Screen 一个 `.tscn` + 对应 C# 脚本）
  - `Game.Godot/Scenes/UI/**`：通用 UI 片段（不直接导航）
  - `Game.Godot/Scripts/Screens/**`、`Game.Godot/Scripts/UI/**`：脚本位置与场景一一对应
  - 示例/演示：`Game.Godot/Examples/**`（默认不加载）
- 命名：`<Role>_<Area>_<Action>`，例如：`Btn_Menu_Start`，`Lbl_HUD_Score`

## Main → Screen 跳转示例 / Navigation

```csharp
// 在 Main.gd/C# 中加载并切换 Screen
var packed = GD.Load<PackedScene>("res://Game.Godot/Scenes/Screens/MyScreen.tscn");
var screen = packed.Instantiate<Control>();
GetTree().CurrentScene.Free(); // 或隐藏旧节点
GetTree().Root.AddChild(screen);
GetTree().CurrentScene = screen;
```

## 输入映射 / Input Map（模板自动注入）

- `InputMapper` 在启动时确保存在 `ui_accept/ui_cancel/ui_up/down/left/right`。
- 若需自定义快捷键，请在 `Game.Godot/Scripts/Bootstrap/InputMapper.cs` 中调整。

## 脚手架 / Scaffold

- 新建 Screen：`./scripts/scaffold/new_screen.ps1 -Name MyScreen`
  - 生成 `Scenes/Screens/MyScreen.tscn` 与 `Scripts/Screens/MyScreen.cs`


## 可复用组件示例 / Reusable Components (Examples)

- Modal：`Game.Godot/Examples/Components/Modal.tscn`
  - 用法：实例化后 `Open("message")`，监听 `Confirmed`/`Closed` 信号。
- Toast：`Game.Godot/Examples/Components/Toast.tscn`
  - 用法：实例化后调用 `ShowToast("text", seconds)`，自动淡出。
- 以上组件默认不加载；可在需要的 Screen 中实例化作为叠加层。


## 示例 Screen（可选） / Example Screen

- `Game.Godot/Examples/Screens/DemoScreen.tscn`：演示 Modal/Toast 用法。
- 使用方式：在编辑器直接打开该场景，或在你的 Screen 中实例化并调用相应方法。


