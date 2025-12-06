$ErrorActionPreference = 'Stop'

function Test-WorkflowFile($path) {
  $errors = @()
  $lines = Get-Content -Encoding UTF8 $path
  $first = ($lines | Where-Object { $_.Trim() -ne '' -and -not ($_.Trim().StartsWith('#')) } | Select-Object -First 1)
  if (-not $first -or ($first -notmatch '^name:')) { $errors += "missing or misplaced 'name:' at file start" }
  if (-not ($lines -match '^on:')) { $errors += "missing 'on:' block" }
  if (-not ($lines -match '^jobs:')) { $errors += "missing 'jobs:' block" }

  for ($i=0; $i -lt $lines.Count; $i++) {
    $l = $lines[$i]
    if ($l -match '^\s+with:\s*$') {
      $hasUses = $false; $usesSetupDotnet = $false
      for ($j=$i-1; $j -ge [Math]::Max(0,$i-6); $j--) {
        $pl = $lines[$j]
        if ($pl -match '^\s+uses:\s*(.+)$') { $hasUses = $true; if ($pl -match 'actions/setup-dotnet') { $usesSetupDotnet = $true }; break }
        if ($pl -match '^\s*-\s+name:') { break }
      }
      if (-not $hasUses) { $errors += "orphan 'with:' not associated to a 'uses:' step (line $($i+1))" }
      if (($i+1) -lt $lines.Count) {
        $next = $lines[$i+1]
        if ($next -match '^\s+dotnet-version:' -and -not $usesSetupDotnet) { $errors += "'dotnet-version' found under non-setup-dotnet step (line $($i+2))" }
      }
    }
  }
  return ,$errors
}

$wfDir = Join-Path (Join-Path $PSScriptRoot '../..') '.github/workflows'
if (-not (Test-Path $wfDir)) { Write-Error "Workflows folder not found: $wfDir" }

$failed = 0
Get-ChildItem $wfDir -Filter *.yml | ForEach-Object {
  $errs = Test-WorkflowFile $_.FullName
  if ($errs.Count -gt 0) {
    Write-Warning "$($_.Name):"; foreach ($e in $errs) { Write-Warning "  - $e" }; $failed++
  } else { Write-Host "OK  $($_.Name)" }
}

if ($failed -gt 0) { Write-Error "Workflow lint found $failed file(s) with issues." } else { Write-Host 'All workflows look sane.' }

