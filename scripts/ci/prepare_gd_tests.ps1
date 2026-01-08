param(
  [string]$ProjectPath = 'Tests.Godot',
  [string]$RuntimeDir = 'Game.Godot'
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$proj = Join-Path $root $ProjectPath
$runtime = Join-Path $root $RuntimeDir
if (-not (Test-Path $proj)) { Write-Error "Test project path not found: $proj" }
if (-not (Test-Path $runtime)) { Write-Error "Runtime dir not found: $runtime" }

# Create a junction inside Tests.Godot to expose runtime under res://
$link = Join-Path $proj $RuntimeDir
if (Test-Path $link) {
  Write-Host "Test runtime link already exists: $link"
  exit 0
}

Write-Host "Creating junction: $link -> $runtime"
$mkOut = & cmd /c mklink /J "$link" "$runtime" 2>&1
$rc = $LASTEXITCODE
if ($rc -ne 0 -or -not (Test-Path $link)) {
  $msg = ($mkOut | Out-String).Trim()
  Write-Error "Failed to create junction (exit=$rc). Output: $msg"
}

Write-Host "Junction created."
