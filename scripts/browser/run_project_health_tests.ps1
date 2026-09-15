param(
    [string]$ProjectHealthUrl = "http://127.0.0.1:8767",
    [string]$Reporter = "line"
)

$ErrorActionPreference = "Stop"
$cacheRoot = Join-Path $env:LOCALAPPDATA "npm-cache\_npx"
$runnerRoot = Get-ChildItem -LiteralPath $cacheRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName "node_modules\@playwright\test\cli.js") } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $runnerRoot) {
    throw "Playwright test runner is not available in the npm npx cache."
}

$env:NODE_PATH = Join-Path $runnerRoot.FullName "node_modules"
$env:PROJECT_HEALTH_URL = $ProjectHealthUrl
$cli = Join-Path $runnerRoot.FullName "node_modules\@playwright\test\cli.js"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Push-Location $repoRoot
try {
    & node $cli test "scripts/browser/project_health.spec.js" --reporter=$Reporter
} finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
