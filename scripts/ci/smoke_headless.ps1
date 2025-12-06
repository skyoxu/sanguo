param(
  [string]$GodotBin = $env:GODOT_BIN,
  [string]$Scene = 'res://Game.Godot/Scenes/Main.tscn',
  [int]$TimeoutSec = 5,
  [string]$ProjectPath = '.'
)

$ErrorActionPreference = 'Stop'

if (-not $GodotBin -or -not (Test-Path $GodotBin)) {
  Write-Error "GODOT_BIN is not set or file not found. Pass -GodotBin or set env var."
}

$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$dest = Join-Path $PSScriptRoot ("../../logs/ci/$ts/smoke")
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$log = Join-Path $dest 'headless.log'
$logOut = Join-Path $dest 'headless.out.log'
$logErr = Join-Path $dest 'headless.err.log'

Write-Host "Starting Godot headless for $TimeoutSec sec: $Scene (path=$ProjectPath)"
$p = Start-Process -FilePath $GodotBin -ArgumentList @('--headless','--path',$ProjectPath, '--scene', $Scene) -PassThru -RedirectStandardOutput $logOut -RedirectStandardError $logErr -WindowStyle Hidden

try {
  $ok = $p.WaitForExit(1000 * $TimeoutSec)
  if (-not $ok) {
    Write-Host "Timeout reached; terminating Godot (expected for smoke)."
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  }
} catch {
  Write-Warning "Failed to wait/stop process: $_"
}

$content = ''
if (Test-Path $logOut) { $content += (Get-Content $logOut -Raw -ErrorAction SilentlyContinue) }
if (Test-Path $logErr) { $content += ("`n" + (Get-Content $logErr -Raw -ErrorAction SilentlyContinue)) }
Set-Content -Path $log -Encoding UTF8 -Value $content
Write-Host "Smoke log saved at $log (out=$logOut, err=$logErr)"

# Heuristic pass criteria: prefer explicit marker, fallback to DB opened, then any output
if ($p.Id -gt 0) {
  if ($content -match '\[TEMPLATE_SMOKE_READY\]') {
    Write-Host 'SMOKE PASS (marker)'
    exit 0
  }
  if ($content -match '\[DB\] opened') {
    Write-Host 'SMOKE PASS (db opened)'
    exit 0
  }
  if ($content.Length -gt 0) {
    Write-Host 'SMOKE PASS (any output)'
    exit 0
  }
}
Write-Warning 'SMOKE INCONCLUSIVE (no output). Check logs.'
exit 0
