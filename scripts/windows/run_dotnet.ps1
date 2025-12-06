Param(
  [string]$Solution = "Game.sln",
  [string]$Configuration = "Debug",
  [string]$OutDir = ""
)

# English comments/prints only. UTF-8 output. Windows friendly.
$ErrorActionPreference = 'Continue'

if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $date = Get-Date -Format 'yyyy-MM-dd'
  $OutDir = Join-Path -Path "logs/unit/$date" -ChildPath ''
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$restoreLog = Join-Path $OutDir 'dotnet-restore.log'
& dotnet restore $Solution 2>&1 | Tee-Object -FilePath $restoreLog | Out-Null
$restoreExit = $LASTEXITCODE

$testLog = Join-Path $OutDir 'dotnet-test-output.txt'
& dotnet test $Solution --collect:"XPlat Code Coverage" --logger "trx;LogFileName=tests.trx" -c $Configuration 2>&1 | Tee-Object -FilePath $testLog | Out-Null
$testExit = $LASTEXITCODE

$trx = Get-ChildItem -Recurse -File -Filter *.trx -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notlike "$OutDir*" } | Select-Object -ExpandProperty FullName
$cov = Get-ChildItem -Recurse -File -Filter coverage.cobertura.xml -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notlike "$OutDir*" } | Select-Object -ExpandProperty FullName
foreach ($f in $trx) { try { Copy-Item -Force -LiteralPath $f -Destination $OutDir } catch {} }
foreach ($f in $cov) { try { Copy-Item -Force -LiteralPath $f -Destination $OutDir } catch {} }

# Quick coverage summary
$covFiles = Get-ChildItem -File -Path $OutDir -Filter coverage.cobertura.xml -ErrorAction SilentlyContinue
$linePct = 0; $branchPct = 0
if ($covFiles) {
  $sumLines=0; $sumCovered=0; $sumBranches=0; $sumBranchesCovered=0
  foreach ($f in $covFiles) {
    try {
      [xml]$x = Get-Content -Raw $f.FullName
      $covNode = $x.coverage
      if ($covNode -ne $null) {
        $sumCovered += [int]$covNode.'lines-covered'
        $sumLines += [int]$covNode.'lines-valid'
        $sumBranchesCovered += [int]$covNode.'branches-covered'
        $sumBranches += [int]$covNode.'branches-valid'
      }
    } catch {}
  }
  if ($sumLines -gt 0) { $linePct = [math]::Round(($sumCovered*100.0)/$sumLines,2) }
  if ($sumBranches -gt 0) { $branchPct = [math]::Round(($sumBranchesCovered*100.0)/$sumBranches,2) }
}

$summary = [pscustomobject]@{
  restoreExit = $restoreExit
  testExit = $testExit
  trxCount = if ($trx) { $trx.Count } else { 0 }
  coberturaCount = if ($cov) { $cov.Count } else { 0 }
  linePct = $linePct
  branchPct = $branchPct
  generated = (Get-Date).ToString('o')
}
$summary | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 (Join-Path $OutDir 'summary.json')
$status = if ($testExit -eq 0) { 'ok' } else { 'fail' }
Write-Output ("RUN_DOTNET status={0} line={1}% branch={2}% out={3}" -f $status, $linePct, $branchPct, $OutDir)
if ($testExit -ne 0) { exit $testExit } else { exit 0 }
