param(
  [Parameter(Mandatory=$true)][string]$Name
)
$ErrorActionPreference = 'Stop'

# Normalize name
$sceneName = $Name -replace '[^A-Za-z0-9_]',''
if ([string]::IsNullOrWhiteSpace($sceneName)) { throw "Invalid screen name" }

$scenesDir = Join-Path $PSScriptRoot '..\..\Game.Godot\Scenes\Screens'
$scriptsDir = Join-Path $PSScriptRoot '..\..\Game.Godot\Scripts\Screens'
New-Item -ItemType Directory -Force -Path $scenesDir | Out-Null
New-Item -ItemType Directory -Force -Path $scriptsDir | Out-Null

$csPath = Join-Path $scriptsDir ("$sceneName.cs")
$tscnPath = Join-Path $scenesDir ("$sceneName.tscn")
$relScript = "res://Game.Godot/Scripts/Screens/$sceneName.cs"

$cs = @"
using Godot;

namespace Game.Godot.Scripts.Screens;

public partial class $sceneName : Control
{
    public override void _Ready()
    {
        // Wire signals and compose UI here
        GD.Print("[$sceneName] _Ready");
    }

    // Optional lifecycle hooks recognized by ScreenNavigator
    public void Enter() => GD.Print("[$sceneName] Enter");
    public void Exit()  => GD.Print("[$sceneName] Exit");
}
"@

$tscn = @"
[gd_scene load_steps=2 format=3]

[ext_resource type=\"Script\" path=\"$relScript\" id=\"1\"]

[node name=\"$sceneName\" type=\"Control\"]
script = ExtResource(\"1\")
"@

Set-Content -Path $csPath -Encoding UTF8 -Value $cs
Set-Content -Path $tscnPath -Encoding UTF8 -Value $tscn

Write-Host "Created screen:"
Write-Host "  $tscnPath"
Write-Host "  $csPath"
