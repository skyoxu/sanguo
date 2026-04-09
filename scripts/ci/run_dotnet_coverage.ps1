param(
  [string]$Solution = 'auto',
  [string]$Format = 'cobertura'
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

# Use coverlet collector
$argsList = @('test', $Solution, '-v', 'minimal', '--collect:"XPlat Code Coverage"',
  '--', "DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Format=$Format")

Write-Host "Running coverage: dotnet $($argsList -join ' ')"
dotnet @argsList
$exitCode = $LASTEXITCODE
Write-Host "dotnet test (coverage) finished with exit code $exitCode"

# Collect coverage report
$reports = Get-ChildItem -Recurse -Filter "coverage.$Format.xml" -ErrorAction SilentlyContinue
if (-not $reports) { $reports = Get-ChildItem -Recurse -Filter "coverage.$Format*" -ErrorAction SilentlyContinue }
if ($reports) {
  $ts = Get-Date -Format 'yyyyMMdd-HHmmss'
  $dest = Join-Path $PSScriptRoot ("../../logs/ci/$ts/dotnet-coverage")
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  foreach($r in $reports){ Copy-Item $r.FullName $dest -Force }
  Write-Host "Coverage reports copied to $dest"
} else {
  Write-Host 'No coverage report found to collect.'
}

exit $exitCode
