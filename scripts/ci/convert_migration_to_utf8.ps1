param(
  [string]$SourceDir = 'docs/migration',
  [string]$BackupRoot = 'backup',
  [string]$LogsRoot = 'logs/ci'
)

$ErrorActionPreference = 'Stop'

function Ensure-Dir([string]$p){ if(-not (Test-Path $p)){ New-Item -ItemType Directory -Force -Path $p | Out-Null } }

$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$src = Join-Path (Get-Location).Path $SourceDir
if (-not (Test-Path $src)) { Write-Error "SourceDir not found: $src" }

$backupDir = Join-Path (Get-Location).Path (Join-Path $BackupRoot ("docs_migration_" + $ts))
$logDir = Join-Path (Get-Location).Path (Join-Path $LogsRoot (Join-Path $ts 'doc-encoding'))
Ensure-Dir $backupDir
Ensure-Dir $logDir

$summary = @()

function Get-MD5([byte[]]$bytes){
  $md5 = [System.Security.Cryptography.MD5]::Create()
  try { return ([System.BitConverter]::ToString($md5.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
  finally { $md5.Dispose() }
}

$files = Get-ChildItem -Recurse -File $src | Where-Object { $_.Extension -in @('.md','.txt') }
foreach($f in $files){
  $full = (Resolve-Path $f.FullName).Path
  $rel = $full.Substring($src.Length).TrimStart([char]'\',[char]'/')
  $destBackup = Join-Path $backupDir $rel
  Ensure-Dir (Split-Path -Parent $destBackup)
  Copy-Item -Force $f.FullName $destBackup

  # Read original bytes and compute MD5/size
  $origBytes = [System.IO.File]::ReadAllBytes($f.FullName)
  $origSize = $origBytes.Length
  $origMD5 = Get-MD5 $origBytes

  # Read as text using PowerShell default decoding, then write back as UTF8
  $text = Get-Content -Raw -LiteralPath $f.FullName
  $repBefore = ([regex]::Matches($text, "\uFFFD")).Count
  Set-Content -LiteralPath $f.FullName -Value $text -Encoding UTF8

  # After
  $newBytes = [System.IO.File]::ReadAllBytes($f.FullName)
  $newSize = $newBytes.Length
  $newMD5 = Get-MD5 $newBytes
  $repAfter = ([regex]::Matches((Get-Content -Raw -LiteralPath $f.FullName), "\uFFFD")).Count

  $summary += [pscustomobject]@{
    file = $f.FullName
    backup = $destBackup
    original_bytes = $origSize
    new_bytes = $newSize
    original_md5 = $origMD5
    new_md5 = $newMD5
    replacement_char_before = $repBefore
    replacement_char_after = $repAfter
    changed = ($origMD5 -ne $newMD5)
  }
}

$sumPath = Join-Path $logDir 'migration-docs-encoding-summary.json'
$summary | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -Path $sumPath
Write-Host "UTF-8 conversion completed. Summary: $sumPath; Backup: $backupDir"
