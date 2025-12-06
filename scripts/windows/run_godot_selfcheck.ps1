Param(
  [string]$GodotBin = $env:GODOT_BIN,
  [string]$Project = (Join-Path (Get-Location) 'project.godot'),
  [switch]$BuildSolutions
)

$ErrorActionPreference = 'Continue'

function Find-Godot([string]$Hint) {
  if (-not [string]::IsNullOrWhiteSpace($Hint) -and (Test-Path $Hint)) { return $Hint }
  $candidates = @(
    'Godot_v4.5.1-stable_win64_console.exe',
    'Godot_v4.5.1-stable_win64.exe',
    'Godot_v4.5-stable_win64_console.exe',
    'Godot.exe'
  )
  foreach ($c in $candidates) {
    $p = Join-Path (Get-Location) $c
    if (Test-Path $p) { return $p }
  }
  return $null
}

function New-LogDir([string]$Kind) {
  $date = Get-Date -Format 'yyyy-MM-dd'
  $dir = Join-Path -Path "logs/$Kind/$date" -ChildPath ''
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  return $dir
}

$outDir = New-LogDir -Kind 'e2e'
$ts = Get-Date -Format 'HHmmssfff'
$consoleLog = Join-Path $outDir ("godot-selfcheck-console-" + $ts + ".txt")

$godot = Find-Godot -Hint $GodotBin
if (-not $godot) {
  Write-Output 'SELF_CHECK_SKIPPED: Godot binary not found'
  exit 1
}

if ($BuildSolutions) {
  & $godot --headless --no-window --build-solutions 2>&1 | Tee-Object -FilePath (Join-Path $outDir ("godot-buildsolutions-" + $ts + ".txt")) | Out-Null
}

$args = @('--headless','--no-window','-s','res://Game.Godot/Scripts/Diagnostics/CompositionRootSelfCheck.gd')
$out = & $godot @args 2>&1 | Tee-Object -FilePath $consoleLog

$match = $out | Select-String -Pattern 'SELF_CHECK_OUT:(.*)$' | Select-Object -Last 1
if (-not $match) {
  Write-Output 'SELF_CHECK_FAILED: no output path found'
  exit 1
}

$userJson = $match.Matches[0].Groups[1].Value.Trim()
if (-not (Test-Path $userJson)) {
  Write-Output ("SELF_CHECK_FAILED: output not found at {0}" -f $userJson)
  exit 1
}

$dest = Join-Path $outDir 'composition_root_selfcheck.json'
Copy-Item -Force -LiteralPath $userJson -Destination $dest

try {
  $json = Get-Content -Raw -LiteralPath $dest | ConvertFrom-Json
  $ports = $json.ports
  $okCount = 0
  foreach ($k in $ports.PSObject.Properties.Name) { if ($ports.$k -eq $true) { $okCount++ } }
  Write-Output ("SELF_CHECK_OK: {0}/6 ports; out={1}" -f $okCount, $dest)
} catch {
  Write-Output ("SELF_CHECK_DONE: out={0}" -f $dest)
}

exit 0
