param(
  [string]$GodotBin = $env:GODOT_BIN,
  [string]$ProjectPath = 'Tests.Godot',
  [switch]$IgnoreHeadless = $true
)

$ErrorActionPreference = 'Stop'

if (-not $GodotBin -or -not (Test-Path $GodotBin)) {
  Write-Error "GODOT_BIN is not set or file not found. Pass -GodotBin or set env var."
}

# Ensure dotnet CLI is in PATH for Godot .NET builds
$dotnetPath = Join-Path $env:USERPROFILE '.dotnet'
if (Test-Path $dotnetPath) {
  $env:Path = "$dotnetPath;" + $env:Path
}

$argsList = @('-a', 'res://tests')
if ($IgnoreHeadless) { $argsList += '--ignoreHeadlessMode' }

Write-Host "Running GdUnit4 tests at '$ProjectPath' with: $GodotBin $argsList"
# Backend detection (plugin vs managed)
if (Test-Path "$PSScriptRoot/../../$ProjectPath/addons/godot-sqlite") {
  Write-Host "Detected addons/godot-sqlite plugin: tests will prefer plugin backend."
} else {
  Write-Host "No addons/godot-sqlite found: tests will use Microsoft.Data.Sqlite managed fallback if available."
}
if ($env:TEMPLATE_DEMO -eq '1') {
  Write-Host "Demo tests enabled (TEMPLATE_DEMO=1)."
} else {
  Write-Host "Demo tests disabled (set TEMPLATE_DEMO=1 to enable example UI tests)."
}

# Ensure test project path exists; pass --path
$runner = Join-Path $PSScriptRoot ("../../$ProjectPath/addons/gdUnit4/runtest.cmd")
if (-not (Test-Path $runner)) { Write-Error "GdUnit4 runner not found at $runner" }
Push-Location $ProjectPath
try {
  & $runner --godot_binary "$GodotBin" @argsList
  $exitCode = $LASTEXITCODE
} finally {
  Pop-Location
}
$exitCode = $LASTEXITCODE
Write-Host "GdUnit4 finished with exit code $exitCode"

# Collect reports to logs/ci/<timestamp>/gdunit4-reports
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$dest = Join-Path $PSScriptRoot ("../../logs/ci/$ts/gdunit4-reports")
$reports = Join-Path $PSScriptRoot ("../../$ProjectPath/reports")
if (Test-Path $reports) {
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  Copy-Item -Recurse -Force "$reports/*" $dest 2>$null
  Write-Host "Reports copied to $dest"
} else {
  Write-Host "No reports directory found to collect."
}

exit $exitCode
