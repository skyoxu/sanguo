param(
  [switch]$Persist
)

$ErrorActionPreference = 'Stop'
Write-Host 'Setting up local environment for Godot .NET...'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$dotnetDir   = Join-Path $projectRoot '.dotnet'
$dotnetExe   = Join-Path $dotnetDir 'dotnet.exe'

if (-not (Test-Path $dotnetExe)) {
  Write-Host ".NET SDK not found at $dotnetExe. Installing 8.0.401..."
  New-Item -ItemType Directory -Force -Path $dotnetDir | Out-Null
  $dl = Join-Path $env:TEMP 'dotnet-install.ps1'
  Invoke-WebRequest -UseBasicParsing -Uri 'https://dot.net/v1/dotnet-install.ps1' -OutFile $dl
  & $dl -Version '8.0.401' -InstallDir $dotnetDir
  # Ensure required runtime 8.0.21 is present for Godot 4.5.1
  & $dl -Runtime 'dotnet' -Version '8.0.21' -InstallDir $dotnetDir
}

# Locate Godot mono executable (prefer console)
$godot = $null
try {
  $godot = Get-ChildItem 'C:\Godot' -Recurse -Filter '*Godot*_mono*console.exe' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
  if (-not $godot) { $godot = Get-ChildItem 'C:\Godot' -Recurse -Filter '*Godot*_mono*win64*.exe' -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName }
} catch {}
if (-not $godot) { Write-Warning '未在 C:\Godot 找到 Godot .NET 可执行文件，请先解压到 C:\Godot'; }

# Set variables for current session
$env:DOTNET_ROOT      = $dotnetDir
$env:PATH             = "$dotnetDir;" + $env:PATH
if (Test-Path $dotnetExe) { $env:GODOT_DOTNET_CLI = $dotnetExe }
if ($godot)               { $env:GODOT_BIN       = $godot }

if ($Persist) {
  [Environment]::SetEnvironmentVariable('DOTNET_ROOT', $dotnetDir, 'User')
  if (Test-Path $dotnetExe) { [Environment]::SetEnvironmentVariable('GODOT_DOTNET_CLI', $dotnetExe, 'User') }
  if ($godot)               { [Environment]::SetEnvironmentVariable('GODOT_BIN', $godot, 'User') }
  # Append .dotnet to User PATH if needed
  $uPath = [Environment]::GetEnvironmentVariable('Path','User')
  if ($uPath -notmatch [Regex]::Escape($dotnetDir)) {
    [Environment]::SetEnvironmentVariable('Path', ($uPath.TrimEnd(';') + ';' + $dotnetDir), 'User')
  }
  Write-Host 'User-level environment variables updated. 新开一个终端生效.'
}

& $dotnetExe --info | Select-String 'Version|Base Path' | ForEach-Object { $_.ToString() }
$gb = $env:GODOT_BIN; if (-not $gb) { $gb = '' }
$gd = $env:GODOT_DOTNET_CLI; if (-not $gd) { $gd = '' }
Write-Host ('GODOT_BIN=' + $gb)
Write-Host ('GODOT_DOTNET_CLI=' + $gd)
