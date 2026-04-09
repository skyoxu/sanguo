param(
  [string]$Solution = 'auto',
  [switch]$CollectTrx = $true
)

$ErrorActionPreference = 'Stop'
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
  Write-Error 'dotnet CLI not found in PATH.'
}

function Resolve-SolutionPath {
  param(
    [string]$RequestedSolution
  )

  if (-not [string]::IsNullOrWhiteSpace($RequestedSolution) -and $RequestedSolution -ne 'auto') {
    return $RequestedSolution
  }

  $repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..\')
  $repoName = Split-Path -Leaf $repoRoot
  $preferred = @('Game.sln', "$repoName.sln", 'GodotGame.sln')
  foreach ($name in $preferred) {
    $candidate = Join-Path $repoRoot $name
    if (Test-Path -LiteralPath $candidate) {
      return $candidate
    }
  }
  $first = Get-ChildItem -Path $repoRoot -Filter *.sln -File -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -First 1
  if ($first) {
    return $first.FullName
  }
  return $RequestedSolution
}

$Solution = Resolve-SolutionPath -RequestedSolution $Solution

$argsList = @('test', $Solution, '-v', 'minimal')
if ($CollectTrx) {
  $argsList += @('--logger','trx;LogFileName=TestResults.trx')
}

Write-Host "Running dotnet $($argsList -join ' ')"
dotnet @argsList
$exitCode = $LASTEXITCODE
Write-Host "dotnet test finished with exit code $exitCode"

# Collect TRX
if ($CollectTrx) {
  $trx = Get-ChildItem -Recurse -Filter TestResults.trx -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($trx) {
    $ts = Get-Date -Format 'yyyyMMdd-HHmmss'
    $dest = Join-Path $PSScriptRoot ("../../logs/ci/$ts/dotnet-tests")
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item $trx.FullName $dest -Force
    Write-Host "TRX copied to $dest"
  } else {
    Write-Host 'No TRX file found to collect.'
  }
}

exit $exitCode
