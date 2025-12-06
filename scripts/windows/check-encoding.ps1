Param(
  [string]$Path = "docs",
  [string]$OutDir
)

# Scripts must use English comments/prints. Windows-friendly, UTF-8 output.
$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Path)) {
  Write-Output "INPUT_PATH_NOT_FOUND: $Path"
  exit 0
}

$date = Get-Date -Format 'yyyy-MM-dd'
if (-not $OutDir -or [string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Join-Path -Path "logs/ci/$date/encoding" -ChildPath ''
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Gather files (docs-like)
$exts = @('*.md','*.txt','*.json','*.yml','*.yaml','*.xml')
$files = @()
foreach ($e in $exts) {
  $files += Get-ChildItem -Path $Path -Recurse -File -Filter $e -ErrorAction SilentlyContinue
}

$results = @()
$badFiles = @()
# Keep pattern simple and robust across consoles
# Typical mojibake fragments when UTF-8 is decoded as ANSI: "Ã" and "Â"
$pattern = 'Ã|Â'

foreach ($f in $files) {
  try {
    # Read raw text as UTF-8 (no BOM requirement)
    $content = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
  } catch {
    $results += [pscustomobject]@{ path=$f.FullName; error=$_.Exception.Message }
    continue
  }

  $hasFFFD = ($content.IndexOf([char]0xFFFD) -ge 0)
  $mojibake = Select-String -InputObject $content -Pattern $pattern -AllMatches
  $mojiHits = @()
  if ($mojibake) { $mojiHits = $mojibake.Matches | ForEach-Object { $_.Value } | Select-Object -First 5 }

  # EOL detection
  $crlf = ([regex]::Matches($content, "\r\n")).Count
  $lf   = ([regex]::Matches($content, "(?<!\r)\n")).Count
  $eol  = if ($crlf -gt 0 -and $lf -eq 0) { 'CRLF' } elseif ($crlf -eq 0 -and $lf -gt 0) { 'LF' } elseif ($crlf -eq 0 -and $lf -eq 0) { 'NONE' } else { 'MIXED' }

  $item = [pscustomobject]@{
    path     = $f.FullName
    eol      = $eol
    crlf     = $crlf
    lf       = $lf
    hasFFFD  = $hasFFFD
    mojiHits = $mojiHits
  }
  $results += $item
  if ($hasFFFD -or ($mojiHits.Count -gt 0) -or $eol -eq 'MIXED') { $badFiles += $item }
}

$summary = [pscustomobject]@{
  scanned   = $results.Count
  badCount  = $badFiles.Count
  badSample = ($badFiles | Select-Object -First 10)
  generated = (Get-Date).ToString('o')
}

$summaryPath = Join-Path $OutDir 'summary.json'
$detailsPath = Join-Path $OutDir 'details.json'
$badPath     = Join-Path $OutDir 'bad.json'

$summary | ConvertTo-Json -Depth 8 | Out-File -FilePath $summaryPath -Encoding utf8
$results | ConvertTo-Json -Depth 8 | Out-File -FilePath $detailsPath -Encoding utf8
$badFiles | ConvertTo-Json -Depth 8 | Out-File -FilePath $badPath -Encoding utf8

Write-Output ("ENCODING_SCAN_DONE: scanned={0} bad={1} out={2}" -f $results.Count, $badFiles.Count, $OutDir)
