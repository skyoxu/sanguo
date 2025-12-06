$ErrorActionPreference = 'Stop'
param(
  [string]$GodotBin = $env:GODOT_BIN,
  [switch]$IncludeDemo = $false
)

if ($IncludeDemo) { $env:TEMPLATE_DEMO = '1' }

Write-Host '=== Running .NET tests ==='
& "$PSScriptRoot/ci/run_dotnet_tests.ps1" -Solution 'Game.sln'
$dotnetExit = $LASTEXITCODE

Write-Host '=== Running GdUnit4 tests ==='
& "$PSScriptRoot/ci/run_gdunit_tests.ps1" -GodotBin $GodotBin
$gdunitExit = $LASTEXITCODE

if ($IncludeDemo) { Remove-Item Env:TEMPLATE_DEMO -ErrorAction SilentlyContinue }

if ($dotnetExit -ne 0 -or $gdunitExit -ne 0) { exit 1 } else { exit 0 }

