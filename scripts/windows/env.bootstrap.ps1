Param(
  [string]$ProjectRoot = ".",
  [string]$GodotBin = "",
  [string]$GodotProject = "",
  [switch]$DryRun
)

# English comments/logs only; outputs UTF-8.
$ErrorActionPreference = 'SilentlyContinue'

function New-LogDir {
  $date = Get-Date -Format 'yyyy-MM-dd'
  $dir = Join-Path -Path "logs/ci/$date/env" -ChildPath ''
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  return $dir
}

function Find-Godot([
  string]$Root) {
  $candidates = @(
    'Godot_v4.5.1-stable_win64.exe',
    'Godot_v4.5.1-stable_mono_win64_console.exe',
    'Godot_v4.5-stable_win64.exe',
    'Godot.exe'
  )
  foreach ($c in $candidates) {
    $p = Join-Path -Path $Root -ChildPath $c
    if (Test-Path $p) { return $p }
  }
  return $null
}

$outDir = New-LogDir
$log = @{}
$log.timestamp = (Get-Date).ToString('o')
$log.machine = $env:COMPUTERNAME
$log.projectRoot = (Resolve-Path $ProjectRoot).Path

if ([string]::IsNullOrWhiteSpace($GodotBin)) {
  $GodotBin = $env:GODOT_BIN
}
if ([string]::IsNullOrWhiteSpace($GodotProject)) {
  $GodotProject = $env:GODOT_PROJECT
}

if (-not $GodotBin) { $GodotBin = Find-Godot -Root $ProjectRoot }
if (-not $GodotProject) { $GodotProject = Join-Path -Path $ProjectRoot -ChildPath 'project.godot' }

$log.detected = @{ GODOT_BIN = $GodotBin; GODOT_PROJECT = $GodotProject }
$log.exists = @{ bin = (Test-Path $GodotBin); project = (Test-Path $GodotProject) }
$log.envBefore = @{ GODOT_BIN = $env:GODOT_BIN; GODOT_PROJECT = $env:GODOT_PROJECT }

if (-not $DryRun) {
  if ($GodotBin) { & setx GODOT_BIN $GodotBin | Out-Null }
  if ($GodotProject) { & setx GODOT_PROJECT $GodotProject | Out-Null }
}

$log.envAfter = @{ GODOT_BIN = if ($DryRun) { $env:GODOT_BIN } else { (Get-Item Env:GODOT_BIN).Value }; GODOT_PROJECT = if ($DryRun) { $env:GODOT_PROJECT } else { (Get-Item Env:GODOT_PROJECT).Value } }
$log.dryRun = [bool]$DryRun

$outPath = Join-Path $outDir 'env-bootstrap.json'
$log | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 $outPath
Write-Output ("ENV_BOOTSTRAP done dryRun={0} out={1}" -f $DryRun, $outPath)
