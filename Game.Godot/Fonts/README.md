Place your project fonts here (e.g., NotoSans-Regular.ttf) and set the ThemeApplier FontPath export to point to it:

- Path: `res://Game.Godot/Fonts/NotoSans-Regular.ttf`
- Scene: `Game.Godot/Scenes/Main.tscn` → Node `ThemeApplier`
- Script: `Game.Godot/Scripts/UI/ThemeApplier.cs` (export `FontPath`)

If the font file is not present, the app keeps using the system default font.
