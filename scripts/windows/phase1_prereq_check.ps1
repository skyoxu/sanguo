Param(
  [string]$ProjectRoot = ".",
  [string]$GodotBin = $env:GODOT_BIN,
  [string]$GodotProject = $env:GODOT_PROJECT,
  [string]$OutDir = ""
)

# English comments and prints only. UTF-8 output. Windows friendly.
$ErrorActionPreference = 'SilentlyContinue'

function New-LogDir {
  Param([string]$BaseOut)
  if ([string]::IsNullOrWhiteSpace($BaseOut)) {
    $date = Get-Date -Format 'yyyy-MM-dd'
    $BaseOut = Join-Path -Path "logs/ci/$date/env" -ChildPath ''
  }
  New-Item -ItemType Directory -Force -Path $BaseOut | Out-Null
  return $BaseOut
}

function Invoke-ExeCapture {
  Param([string]$Exe, [string[]]$Args, [int]$TimeoutMs = 4000)
  try {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.Arguments = [string]::Join(' ', $Args)
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $psi
    $null = $p.Start()
    $outReader = $p.StandardOutput
    $errReader = $p.StandardError
    $waitOk = $p.WaitForExit($TimeoutMs)
    if (-not $waitOk) {
      try { $p.Kill() } catch {}
      return @{ ok = $false; timeout = $true; stdout = $outReader.ReadToEnd(); stderr = $errReader.ReadToEnd() }
    }
    $out = $outReader.ReadToEnd()
    $err = $errReader.ReadToEnd()
    return @{ ok = $true; code = $p.ExitCode; stdout = $out; stderr = $err }
  } catch {
    return @{ ok = $false; error = $_.Exception.Message }
  }
}

function Find-Godot {
  Param([string]$Hint)
  if (-not [string]::IsNullOrWhiteSpace($Hint) -and (Test-Path $Hint)) { return $Hint }
  $candidates = @(
    "Godot_v4.5.1-stable_win64.exe",
    "Godot_v4.5-stable_win64.exe",
    "Godot.exe"
  )
  foreach ($c in $candidates) {
    $p = Join-Path -Path $ProjectRoot -ChildPath $c
    if (Test-Path $p) { return $p }
  }
  return $null
}

$result = @{
  os = $env:OS
  machine = $env:COMPUTERNAME
  projectRoot = (Resolve-Path $ProjectRoot).Path
  checks = @{}
}

$OutDir = New-LogDir -BaseOut $OutDir

# 1) Git
$git = Test-Path (Get-Command git -ErrorAction SilentlyContinue).Path
$gitVer = $null
if ($git) { try { $gitVer = (git --version) } catch {} }
$result.checks.git = @{ present = $git; version = $gitVer }

# 2) .NET SDK 8+
$dotnet = Test-Path (Get-Command dotnet -ErrorAction SilentlyContinue).Path
$dotnetVerRaw = $null; $dotnetOk = $false
if ($dotnet) {
  try { $dotnetVerRaw = (dotnet --version).Trim(); $major = [int]($dotnetVerRaw.Split('.')[0]); $dotnetOk = ($major -ge 8) } catch {}
}
$result.checks.dotnet = @{ present = $dotnet; version = $dotnetVerRaw; ok = $dotnetOk }

# 3) Python (prefer py -3)
$pyLauncher = Test-Path (Get-Command py -ErrorAction SilentlyContinue).Path
$py3Ok = $false; $py3Ver = $null
if ($pyLauncher) {
  try { $py3Ver = (py -3 --version) -join ' '; if ($py3Ver) { $py3Ok = $true } } catch {}
} else {
  try { $py3Ver = (python --version) -join ' '; if ($py3Ver) { $py3Ok = $true } } catch {}
}
$result.checks.python = @{ launcher = $pyLauncher; present = $py3Ok; version = $py3Ver }

# 4) Godot
$godotPath = Find-Godot -Hint $GodotBin
$godotOk = $false; $godotVer = $null; $godotProbe = @{}
if ($godotPath) {
  # Try multiple strategies to discover version
  $probe1 = Invoke-ExeCapture -Exe $godotPath -Args @('--headless','--version','--quit') -TimeoutMs 3000
  if (-not $probe1.ok -and -not $probe1.timeout) {
    $probe2 = Invoke-ExeCapture -Exe $godotPath -Args @('--version','--quit') -TimeoutMs 3000
  } else { $probe2 = @{ ok = $false } }
  $vi = $null; try { $vi = (Get-Item $godotPath).VersionInfo } catch {}
  $fileVer = $null; if ($vi) { if ($vi.ProductVersion) { $fileVer = $vi.ProductVersion } elseif ($vi.FileVersion) { $fileVer = $vi.FileVersion } }
  $nameVer = $null; if ($godotPath -match 'v([0-9]+\.[0-9]+(\.[0-9]+)?)') { $nameVer = $matches[1] }

  $joined = @()
  if ($probe1.ok) { $joined += ($probe1.stdout + ' ' + $probe1.stderr) }
  if ($probe2.ok) { $joined += ($probe2.stdout + ' ' + $probe2.stderr) }
  if ($fileVer) { $joined += $fileVer }
  if ($nameVer) { $joined += $nameVer }
  $godotVer = ($joined -join ' ').Trim()
  if ($godotVer -match '(^|\s)4\.5(\.|\s|$)') { $godotOk = $true }
  $godotProbe = @{ p1 = $probe1; p2 = $probe2; fileVersion = $fileVer; nameVersion = $nameVer }
}
$result.checks.godot = @{ path = $godotPath; version = $godotVer; ok = $godotOk; probe = $godotProbe }

# 5) project.godot
if ([string]::IsNullOrWhiteSpace($GodotProject)) { $GodotProject = Join-Path -Path $ProjectRoot -ChildPath 'project.godot' }
$projExists = Test-Path $GodotProject
$result.checks.project = @{ path = $GodotProject; exists = $projExists }

# 6) Recommended env vars
$result.checks.env = @{
  GODOT_BIN = $env:GODOT_BIN
  GODOT_PROJECT = $env:GODOT_PROJECT
  CI = $env:CI
}

# Status summarization
$issues = @()
if (-not $git) { $issues += "Git not found" }
if (-not $dotnetOk) { $issues += "Dotnet SDK 8+ not found or invalid: $dotnetVerRaw" }
if (-not $py3Ok) { $issues += "Python 3 launcher not found (py -3 / python)" }
if (-not $godotOk) { $issues += "Godot 4.5 not found or version mismatch (path=$godotPath; ver=$godotVer)" }
if (-not $projExists) { $issues += "project.godot not found at $GodotProject" }

$status = if ($issues.Count -eq 0) { 'ok' } elseif ($issues.Count -le 2) { 'warn' } else { 'fail' }
$result.status = $status
$result.issues = $issues
$result.generated = (Get-Date).ToString('o')

# Write outputs
$jsonPath = Join-Path $OutDir 'phase1-env-check.json'
$txtPath  = Join-Path $OutDir 'phase1-env-check.txt'

$result | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 $jsonPath
($result | Out-String) | Out-File -Encoding utf8 $txtPath

Write-Output ("ENV_CHECK status={0} issues={1} out={2}" -f $status, $issues.Count, $OutDir)
if ($status -eq 'fail') { exit 1 } else { exit 0 }
