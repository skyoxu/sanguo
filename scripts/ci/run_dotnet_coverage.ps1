param(
  [string]$Solution = 'Game.sln',
  [string]$Format = 'cobertura'
)

$ErrorActionPreference = 'Stop'
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
  Write-Error 'dotnet CLI not found in PATH.'
}

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
