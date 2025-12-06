param(
  [string]$Output
)

$ErrorActionPreference = 'Stop'
if (-not $Output) {
  $Output = "docs/release/RELEASE_NOTES-" + (Get-Date -Format 'yyyy-MM-dd') + ".md"
}

$lines = @()
$lines += "# Release Notes"
$lines += ""
$lines += "- Version: <v>"
$lines += "- Date: " + (Get-Date -Format 'yyyy-MM-dd')
$lines += ""
$lines += "## Overview"
$lines += "- Summary of changes/features"
$lines += ""
$lines += "## Quality Gate"
$lines += "- dotnet tests: (see logs/ci)"
$lines += "- GdUnit tests: (see logs/ci)"
$lines += "- Headless smoke: (see logs/ci)"
$lines += "- EXE smoke: (see logs/ci)"
$lines += "- Perf P95 (ms): <parse from logs>"
$lines += ""
$lines += "## Known Issues"
$lines += "- ..."
$lines += ""
$lines += "## Artifacts"
$lines += "- EXE: build/Game.exe"
$lines += "- Logs: logs/ci/YYYYMMDD-HHMMSS/**"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Output) | Out-Null
Set-Content -Path $Output -Encoding UTF8 -Value $lines
Write-Host "Release notes scaffolded: $Output"

exit 0
