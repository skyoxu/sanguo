param(
  [Parameter(Mandatory = $true)][string]$Version,
  [string]$OutputDir = 'godot',
  [switch]$PreferConsole,
  [int]$MaxAttempts = 5
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Test-ZipMagic {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  $item = Get-Item -LiteralPath $Path -ErrorAction Stop
  if ($item.Length -lt 4) { return $false }
  $stream = [System.IO.File]::OpenRead($item.FullName)
  try {
    $bytes = New-Object byte[] 4
    $read = $stream.Read($bytes, 0, 4)
    if ($read -lt 4) { return $false }
    return (
      ($bytes[0] -eq 0x50) -and
      ($bytes[1] -eq 0x4B) -and
      (
        (($bytes[2] -eq 0x03) -and ($bytes[3] -eq 0x04)) -or
        (($bytes[2] -eq 0x05) -and ($bytes[3] -eq 0x06)) -or
        (($bytes[2] -eq 0x07) -and ($bytes[3] -eq 0x08))
      )
    )
  }
  finally {
    $stream.Dispose()
  }
}

function Get-InvalidDownloadPreview {
  param([Parameter(Mandatory = $true)][string]$Path)
  try {
    $raw = Get-Content -LiteralPath $Path -Encoding UTF8 -TotalCount 8 -ErrorAction Stop
    return ($raw -join "`n")
  }
  catch {
    return '<binary-or-unreadable>'
  }
}

function Invoke-DownloadWithRetry {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$TargetPath,
    [int]$Attempts = 5
  )

  for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    if (Test-Path -LiteralPath $TargetPath) {
      Remove-Item -LiteralPath $TargetPath -Force -ErrorAction SilentlyContinue
    }

    Write-Host "Downloading Godot archive (attempt $attempt/$Attempts): $Url"
    & curl.exe -fL --retry 3 --retry-all-errors --connect-timeout 30 --max-time 1200 `
      -o $TargetPath $Url
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "curl.exe failed with exit code $LASTEXITCODE"
    }
    elseif (Test-ZipMagic -Path $TargetPath) {
      return
    }
    else {
      $preview = Get-InvalidDownloadPreview -Path $TargetPath
      Write-Warning "Downloaded file is not a valid zip. preview=$preview"
    }

    if ($attempt -lt $Attempts) {
      Start-Sleep -Seconds ([Math]::Min(30, 5 * $attempt))
    }
  }

  throw "Failed to download a valid Godot archive after $Attempts attempts: $Url"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$zip = Join-Path $OutputDir 'godot.zip'
$extractDir = Join-Path $OutputDir 'mono'
$url = "https://github.com/godotengine/godot/releases/download/${Version}-stable/Godot_v${Version}-stable_mono_win64.zip"

if (-not (Test-ZipMagic -Path $zip)) {
  if (Test-Path -LiteralPath $zip) {
    Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
  }
  Invoke-DownloadWithRetry -Url $url -TargetPath $zip -Attempts $MaxAttempts
}
else {
  Write-Host "Reusing cached Godot archive: $zip"
}

if (Test-Path -LiteralPath $extractDir) {
  Remove-Item -LiteralPath $extractDir -Recurse -Force -ErrorAction SilentlyContinue
}
Expand-Archive -LiteralPath $zip -DestinationPath $extractDir -Force

$filter = if ($PreferConsole.IsPresent) { '*win64*console*.exe' } else { '*win64*.exe' }
$exe = Get-ChildItem -Path $extractDir -Recurse -Filter $filter -File | Select-Object -First 1
if (-not $exe -and $PreferConsole.IsPresent) {
  $exe = Get-ChildItem -Path $extractDir -Recurse -Filter '*win64*.exe' -File | Select-Object -First 1
}
if (-not $exe) {
  throw "Godot executable not found after extraction: $extractDir"
}

"GODOT_BIN=$($exe.FullName)" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
Write-Host "GODOT_BIN=$($exe.FullName)"
