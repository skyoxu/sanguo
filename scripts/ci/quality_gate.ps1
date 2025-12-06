param(
  [string]$GodotBin = $env:GODOT_BIN,
  [switch]$WithExport = $false,
  [switch]$IncludeDemo = $false,
  [switch]$WithCoverage = $false,
  [int]$PerfP95Ms = 0
)

$ErrorActionPreference = 'Stop'

function Run-Step($name, [ScriptBlock]$block) {
  Write-Host "=== [$name] ==="
  try { & $block; return $LASTEXITCODE } catch { Write-Error $_; return 1 }
}

$fail = 0

# 1) Python quality gates (delegates to ci_pipeline + future gates)
$c = Run-Step 'python quality_gates.py' { py -3 "$PSScriptRoot/../python/quality_gates.py" all --godot-bin $GodotBin --solution 'Game.sln' --configuration 'Debug' --build-solutions }
if ($c -ne 0) { $fail++ }

# 2) Export + EXE smoke (optional)
if ($WithExport) {
  $c = Run-Step 'Export Windows EXE' { & "$PSScriptRoot/export_windows.ps1" -GodotBin $GodotBin -Output 'build/Game.exe' }
  if ($c -ne 0) { $fail++ }
  $c = Run-Step 'Smoke EXE' { & "$PSScriptRoot/smoke_exe.ps1" -ExePath 'build/Game.exe' -TimeoutSec 5 }
  if ($c -ne 0) { $fail++ }
}
# 3) Perf budget (optional)
if ($PerfP95Ms -gt 0) {
  $c = Run-Step "Perf budget <= $PerfP95Ms ms" { & "$PSScriptRoot/check_perf_budget.ps1" -MaxP95Ms $PerfP95Ms }
  if ($c -ne 0) { $fail++ }
}

# Final status and smoke hint (printed last)
if ($fail -gt 0) {
  Write-Host "QUALITY GATE: FAIL ($fail)"
  $exitCode = 1
} else {
  Write-Host 'QUALITY GATE: PASS'
  $exitCode = 0
}
Write-Host 'SMOKE TIP: Prefer [TEMPLATE_SMOKE_READY] (marker), fallback [DB] opened (logs).'
exit $exitCode
