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
$mk = Start-Process -FilePath "cmd" -ArgumentList @("/c","mklink","/J","$link","$runtime") -PassThru -NoNewWindow -WindowStyle Hidden
$ok = $mk.WaitForExit(10000)
if (-not $ok -or $mk.ExitCode -ne 0 -or -not (Test-Path $link)) {
  Write-Warning "mklink failed or not available (exit=$($mk.ExitCode)); falling back to copy."
  # Fallback copy (exclude bin/obj/.import/.godot/logs)
  $exclude = @('bin','obj','.import','.godot','logs')
  New-Item -ItemType Directory -Force -Path $link | Out-Null
  Get-ChildItem -Force -LiteralPath $runtime | ForEach-Object {
    if ($exclude -contains $_.Name) { return }
    Copy-Item -Recurse -Force -LiteralPath $_.FullName -Destination (Join-Path $link $_.Name)
  }
  New-Item -ItemType File -Force -Path (Join-Path $link '._copied') | Out-Null
  if (-not (Test-Path $link)) { Write-Error "Failed to prepare test runtime at $link" }
  Write-Host "Copied runtime to $link"
} else {
  Write-Host "Junction created."
}
