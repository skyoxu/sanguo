param(
  [string]$RepoRoot = '.'
)

$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if(-not (Test-Path $p)){ New-Item -ItemType Directory -Force -Path $p | Out-Null } }

$root = (Resolve-Path $RepoRoot).Path
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$logDir = Join-Path $root ("logs/ci/$ts/base-clean")
Ensure-Dir $logDir
$report = Join-Path $logDir 'summary.json'

$violations = @()

function Add-Violation([string]$file,[string]$rule,[string]$message){
  $vi = [pscustomobject]@{ file=$file; rule=$rule; message=$message }
  $script:violations = $script:violations + $vi
}

# 1) Base: no concrete 08 content or PRD-ID
$baseDir = Join-Path $root 'docs/architecture/base'
if (Test-Path $baseDir) {
  $files = Get-ChildItem -Recurse -File $baseDir
  foreach($f in $files){
    $name = $f.Name
    if ($name -match '^08-.*' -and $name -notmatch 'template' -and $name -notmatch '\.base\.') {
      Add-Violation $f.FullName 'BASE_08_CONCRETE' 'Base forbids concrete 08 (only template allowed)'
    }
    $content = Get-Content -Raw -LiteralPath $f.FullName
    if ($content -match 'PRD-\w+') {
      Add-Violation $f.FullName 'BASE_PRD_ID' 'PRD-ID found in Base document'
    }
  }
}

# 2) Overlay 08: must reference CH01/CH03 (at least one) and avoid hard-coded thresholds (heuristic)
$ovRoot = Join-Path $root 'docs/architecture/overlays'
if (Test-Path $ovRoot) {
  $ovPrds = Get-ChildItem -Directory $ovRoot
  foreach($prd in $ovPrds){
    $ov08 = Join-Path $prd.FullName '08'
    if (Test-Path $ov08) {
      $ovFiles = Get-ChildItem -File $ov08
      foreach($f in $ovFiles){
        $c = Get-Content -Raw -LiteralPath $f.FullName
        if ($c -notmatch 'CH0?1' -and $c -notmatch 'CH0?3' -and $c -notmatch 'Chapter\s*0?1' -and $c -notmatch 'Chapter\s*0?3'){
          Add-Violation $f.FullName 'OVERLAY_08_NO_CH' 'Overlay 08 missing CH01/CH03 reference'
        }
        if ($c -match '(?i)(p95|99\.5%|coverage\s*>=|crash[- ]free)'){
          Add-Violation $f.FullName 'OVERLAY_08_DUP_THRESHOLD' 'Overlay 08 appears to duplicate thresholds; should reference 01/02/03'
        }
      }
    }
  }
}

# 3) ADR directory exists and has at least one ADR-xxxx-*.md
$adrDir = Join-Path $root 'docs/adr'
if (-not (Test-Path $adrDir)) { Add-Violation $adrDir 'ADR_DIR_MISSING' 'docs/adr directory missing' }
else {
  $adrCount = (Get-ChildItem -File $adrDir | Where-Object { $_.Name -match '^ADR-\d{4}-' }).Count
  if ($adrCount -lt 1) { Add-Violation $adrDir 'ADR_EMPTY' 'No ADR files found (ADR-xxxx-*.md)' }
}

$result = [pscustomobject]@{
  ts = (Get-Date).ToString('o')
  violations = $violations
  passed = ($violations.Count -eq 0)
}

$result | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -Path $report
if ($violations.Count -gt 0) {
  Write-Host "Base-Clean violations found: $($violations.Count). Summary: $report"
  $violations | ForEach-Object { Write-Host (" - [" + $_.rule + "] " + $_.file + " :: " + $_.message) }
  exit 2
} else {
  Write-Host "Base-Clean passed. Summary: $report"
}
