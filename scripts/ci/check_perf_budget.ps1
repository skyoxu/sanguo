param(
  [int]$MaxP95Ms = 20,
  [string]$LogPath
)

$ErrorActionPreference = 'Stop'
function Find-LatestHeadlessLog {
  $logs = Get-ChildItem -Recurse -Filter headless.log -Path "$PSScriptRoot/../../logs/ci" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
  return $logs | Select-Object -First 1
}

if (-not $LogPath) {
  $l = Find-LatestHeadlessLog
  if (-not $l) { Write-Error 'No headless.log found under logs/ci'; exit 1 }
  $LogPath = $l.FullName
}

if (-not (Test-Path $LogPath)) { Write-Error "Log not found: $LogPath"; exit 1 }

$content = Get-Content $LogPath -Raw
$m = [regex]::Matches($content, '\[PERF\][^\n]*p95_ms=([0-9]+(?:\.[0-9]+)?)')
if ($m.Count -eq 0) { Write-Error 'No PERF markers found'; exit 1 }
$last = $m[$m.Count-1].Groups[1].Value
$p95 = [double]$last
Write-Host "Found p95_ms=$p95 ms (budget $MaxP95Ms ms)"
if ($p95 -le $MaxP95Ms) { Write-Host 'PERF BUDGET PASS'; exit 0 } else { Write-Error 'PERF BUDGET FAIL'; exit 1 }
