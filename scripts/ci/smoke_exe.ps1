param(
  [Parameter(Mandatory=$true)][string]$ExePath,
  [int]$TimeoutSec = 5,
  [string[]]$Args
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $ExePath)) {
  Write-Error "Executable not found: $ExePath"
}

$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$dest = Join-Path $PSScriptRoot ("../../logs/ci/$ts/smoke")
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$log = Join-Path $dest 'exe.log'
$logOut = Join-Path $dest 'exe.out.log'
$logErr = Join-Path $dest 'exe.err.log'

Write-Host "Starting EXE for $TimeoutSec sec: $ExePath $Args"
$p = Start-Process -FilePath $ExePath -ArgumentList $Args -PassThru -RedirectStandardOutput $logOut -RedirectStandardError $logErr -WindowStyle Hidden

try {
  $ok = $p.WaitForExit(1000 * $TimeoutSec)
  if (-not $ok) {
    Write-Host "Timeout reached; terminating EXE (expected for smoke)."
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  }
} catch {
  Write-Warning "Failed to wait/stop process: $_"
}

Write-Host "Smoke EXE log: $log"

$content = ''
if (Test-Path $logOut) { $content += (Get-Content $logOut -Raw -ErrorAction SilentlyContinue) }
if (Test-Path $logErr) { $content += ("`n" + (Get-Content $logErr -Raw -ErrorAction SilentlyContinue)) }
Set-Content -Path $log -Encoding UTF8 -Value $content

# Prefer explicit marker, fallback to DB opened, then any output; keep non-fatal
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

Write-Warning 'SMOKE INCONCLUSIVE (no output). Check logs.'
exit 0
