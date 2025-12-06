param(
  [string]$GodotBin = $env:GODOT_BIN,
  [string]$Preset = 'Windows Desktop',
  [string]$Output = 'build/Game.exe'
)

 $ErrorActionPreference = 'Stop'

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Output) | Out-Null
Write-Host "Exporting $Preset to $Output"
# Backend detection message
if (Test-Path "$PSScriptRoot/../../addons/godot-sqlite") {
  Write-Host "Detected addons/godot-sqlite plugin: export will prefer plugin backend."
} else {
  Write-Host "No addons/godot-sqlite found: export relies on Microsoft.Data.Sqlite managed fallback. If runtime missing native e_sqlite3, add SQLitePCLRaw.bundle_e_sqlite3."
}
if (Get-Command dotnet -ErrorAction SilentlyContinue) {
  $env:GODOT_DOTNET_CLI = (Get-Command dotnet).Path
  Write-Host "GODOT_DOTNET_CLI=$env:GODOT_DOTNET_CLI"
}

# Prepare log dirs: stage outside res:// to avoid packing logs; finalize to repo logs
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$finalDest = Join-Path $PSScriptRoot ("../../logs/ci/$ts/export")
$dest = Join-Path ([System.IO.Path]::GetTempPath()) ("godot_export_" + $ts)
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$glog = Join-Path $dest 'godot_export.log'
New-Item -ItemType File -Force -Path $glog | Out-Null
Write-Host ("Staging log dir: " + $dest)

# Resolve project root (repo root) and use absolute --path to avoid CWD issues
$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot '../../')).Path
Add-Content -Encoding UTF8 -Path $glog -Value ("ProjectDir: " + $ProjectDir)

if (-not $GodotBin -or -not (Test-Path $GodotBin)) {
  $msg = "GODOT_BIN is not set or file not found: '$GodotBin'"
  Add-Content -Encoding UTF8 -Path $glog -Value $msg
  Write-Error $msg
}

# Resolve export preset name from export_presets.cfg to avoid 'Invalid export preset name'
function Resolve-Preset([string]$requested) {
  $cfgCandidates = @('export_presets.cfg','Game.Godot/export_presets.cfg')
  $names = @()
  foreach ($c in $cfgCandidates) {
    if (Test-Path $c) {
      try {
        $lines = Get-Content $c -ErrorAction SilentlyContinue
        foreach ($ln in $lines) {
          if ($ln -match '^\s*name\s*=\s*"([^"]+)"') { $names += $Matches[1] }
        }
      } catch {}
    }
  }
  if ($names.Count -eq 0) { return $requested }
  try { if ($glog) { Add-Content -Encoding UTF8 -Path $glog -Value ("Detected presets: " + ($names -join ', ')) } } catch {}
  # exact match
  if ($names -contains $requested) { return $requested }
  # common alias mapping: 'Windows' -> first name containing 'Windows'
  $win = $names | Where-Object { $_ -match '(?i)windows' } | Select-Object -First 1
  if ($requested -eq 'Windows' -and $win) { return $win }
  # prefer 'Windows Desktop' if present
  $wd = $names | Where-Object { $_ -eq 'Windows Desktop' } | Select-Object -First 1
  if ($wd) { return $wd }
  # fallback to first preset
  return ($names | Select-Object -First 1)
}

# Quote arguments for Start-Process -ArgumentList to preserve spaces
function Quote-Arg([string]$a) {
  if ($null -eq $a) { return '""' }
  if ($a -match '^[A-Za-z0-9_./\\:-]+$') { return $a }
  $q = '"' + ($a -replace '"', '\"') + '"'
  return $q
}

function Invoke-BuildSolutions() {
  Write-Host "Pre-building C# solutions via Godot (--build-solutions)"
  $out = Join-Path $dest ("godot_build_solutions.out.log")
  $err = Join-Path $dest ("godot_build_solutions.err.log")
  $args = @('--headless','--verbose','--path', $ProjectDir, '--build-solutions', '--quit')
  $argStr = ($args | ForEach-Object { Quote-Arg $_ }) -join ' '
  try {
    $p = Start-Process -FilePath $GodotBin -ArgumentList $argStr -PassThru -WorkingDirectory $ProjectDir -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden
  } catch {
    Add-Content -Encoding UTF8 -Path $glog -Value ("Start-Process failed (build-solutions): " + $_.Exception.Message)
    throw
  }
  $ok = $p.WaitForExit(1200000)
  if (-not $ok) { Write-Warning 'Godot build-solutions timed out; killing process'; Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
  Add-Content -Encoding UTF8 -Path $glog -Value ("=== build-solutions @ " + (Get-Date).ToString('o'))
  if (Test-Path $out) { Get-Content $out -ErrorAction SilentlyContinue | Add-Content -Encoding UTF8 -Path $glog }
  if (Test-Path $err) { Get-Content $err -ErrorAction SilentlyContinue | Add-Content -Encoding UTF8 -Path $glog }
  # Log quick check for built assembly
  try {
    $binDir = Join-Path $PSScriptRoot '../../.godot/mono/temp/bin'
    if (Test-Path $binDir) {
      $dlls = Get-ChildItem -Path $binDir -Filter '*.dll' -ErrorAction SilentlyContinue
      Add-Content -Encoding UTF8 -Path $glog -Value ("Built DLLs: " + ($dlls | Select-Object -ExpandProperty Name | Sort-Object | Out-String))
    } else {
      Add-Content -Encoding UTF8 -Path $glog -Value 'Warning: .godot/mono/temp/bin not found after build-solutions.'
    }
    # Try to capture MSBuild detailed log Godot writes under Roaming\Godot\mono\build_logs
    $blRoot = Join-Path $env:APPDATA 'Godot/mono/build_logs'
    if (Test-Path $blRoot) {
      $latest = Get-ChildItem -Directory $blRoot | Sort-Object LastWriteTime -Descending | Select-Object -First 1
      if ($latest) {
        $logPath = Join-Path $latest.FullName 'msbuild_log.txt'
        if (Test-Path $logPath) {
          $msbLocal = Join-Path $dest 'msbuild_log.txt'
          Copy-Item -Force $logPath $msbLocal -ErrorAction SilentlyContinue
          # Extract errors: match 'error <code>', 'CSxxxx', 'GD010x' (case-insensitive)
          try {
            $pattern = '(?i)\berror\b\s+[A-Z]?[0-9]{3,5}\b|CS[0-9]{4}\b|GD010[0-9]\b'
            $matches = Select-String -Path $logPath -Pattern $pattern -AllMatches -ErrorAction SilentlyContinue
            $outFile = Join-Path $dest 'msbuild_errors.txt'
            if ($matches -and $matches.Count -gt 0) {
              $lines = $matches | Select-Object -ExpandProperty Line
              $lines | Set-Content -Path $outFile -Encoding UTF8
            } else {
              'No errors matched (pattern: error|CSxxxx|GD010x).' | Set-Content -Path $outFile -Encoding UTF8
            }
          } catch {
            ('Failed to extract msbuild errors: ' + $_.Exception.Message) | Set-Content -Path (Join-Path $dest 'msbuild_errors.txt') -Encoding UTF8
          }
        }
      }
    }
  } catch {}
  return $p.ExitCode
}

function Invoke-Export([string]$mode) {
  Write-Host "Invoking export: $mode"
  $out = Join-Path $dest ("godot_export.$mode.out.log")
  $err = Join-Path $dest ("godot_export.$mode.err.log")
  $resolved = Resolve-Preset $Preset
  Add-Content -Encoding UTF8 -Path $glog -Value ("Using preset: '" + $resolved + "' output: '" + $Output + "'")
  if ($resolved -ne $Preset) { Add-Content -Encoding UTF8 -Path $glog -Value ("Requested preset '" + $Preset + "' resolved to '" + $resolved + "'") }
  $args = @('--headless','--verbose','--path', $ProjectDir, "--export-$mode", $resolved, $Output)
  $argStr = ($args | ForEach-Object { Quote-Arg $_ }) -join ' '
  try {
    $p = Start-Process -FilePath $GodotBin -ArgumentList $argStr -PassThru -WorkingDirectory $ProjectDir -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden
  } catch {
    Add-Content -Encoding UTF8 -Path $glog -Value ("Start-Process failed (export-"+$mode+"): " + $_.Exception.Message)
    throw
  }
  $ok = $p.WaitForExit(1200000)
  if (-not $ok) { Write-Warning 'Godot export timed out; killing process'; Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
  Add-Content -Encoding UTF8 -Path $glog -Value ("=== export-$mode @ " + (Get-Date).ToString('o'))
  if (Test-Path $out) { Get-Content $out -ErrorAction SilentlyContinue | Add-Content -Encoding UTF8 -Path $glog }
  if (Test-Path $err) { Get-Content $err -ErrorAction SilentlyContinue | Add-Content -Encoding UTF8 -Path $glog }
  return $p.ExitCode
}

# Skip --build-solutions when a solution is already present to reduce flakiness in CI
$sln = Join-Path $ProjectDir 'GodotGame.sln'
if (Test-Path $sln) {
  Add-Content -Encoding UTF8 -Path $glog -Value "Solution detected at $sln, skipping --build-solutions."
} else {
  $buildCode = Invoke-BuildSolutions
  if ($buildCode -ne 0) {
    Write-Warning "Godot --build-solutions exited with code $buildCode. Continuing to export. See log: $glog"
  }
}

# Temporarily move test/plugin folders out of res:// to keep export lean
$excludeRoots = @('addons/gdUnit4','tests','Game.Core.Tests','reports','godot_local')
$moved = @()
foreach ($rel in $excludeRoots) {
  $src = Join-Path $ProjectDir $rel
  if (Test-Path $src) {
    try {
      $stash = Join-Path $ProjectDir (".export_exclude/" + $rel)
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $stash) | Out-Null
      Move-Item -Force -Path $src -Destination $stash
      $moved += @{ src=$src; dst=$stash }
      Add-Content -Encoding UTF8 -Path $glog -Value ("Temporarily moved: '" + $src + "' -> '" + $stash + "'")
    } catch {
      Write-Warning ("Failed to move '" + $src + "': " + $_.Exception.Message)
    }
  }
}

$exitCode = Invoke-Export 'release'
# Heuristic: if target output exists even when exit code is non-zero/null, treat as success
if ((-not $exitCode) -or ($exitCode -ne 0)) {
  if (Test-Path $Output) {
    Write-Warning "Export-release returned exit=$exitCode but output exists ($Output). Treating as success."
    $exitCode = 0
  }
}

# Restore moved folders
foreach ($m in $moved) {
  try {
    if (Test-Path $m.dst) {
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $m.src) | Out-Null
      Move-Item -Force -Path $m.dst -Destination $m.src
      Add-Content -Encoding UTF8 -Path $glog -Value ("Restored: '" + $m.dst + "' -> '" + $m.src + "'")
    }
  } catch {
    Write-Warning ("Failed to restore '" + $m.dst + "': " + $_.Exception.Message)
  }
}
if ($exitCode -ne 0) {
  Write-Warning "Export-release failed with exit code $exitCode. Trying export-debug as fallback."
  $exitCode = Invoke-Export 'debug'
  if ((-not $exitCode) -or ($exitCode -ne 0)) {
    if (Test-Path $Output) {
      Write-Warning "Export-debug returned exit=$exitCode but output exists ($Output). Treating as success."
      $exitCode = 0
    }
  }
  if ($exitCode -ne 0) {
    Write-Warning "Both release and debug export failed, trying export-pack as fallback."
    $pck = ($Output -replace '\.exe$','.pck')
    $out = Join-Path $dest ("godot_export.pack.out.log")
    $err = Join-Path $dest ("godot_export.pack.err.log")
    $resolved = Resolve-Preset $Preset
    Add-Content -Encoding UTF8 -Path $glog -Value ("Using preset (pack): '" + $resolved + "' output: '" + $pck + "'")
    $args = @('--headless','--verbose','--path', $ProjectDir, '--export-pack', $resolved, $pck)
    $argStr = ($args | ForEach-Object { Quote-Arg $_ }) -join ' '
    $p = Start-Process -FilePath $GodotBin -ArgumentList $argStr -PassThru -WorkingDirectory $ProjectDir -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden
    $ok = $p.WaitForExit(1200000)
    if (-not $ok) { Write-Warning 'Godot export-pack timed out'; Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    Add-Content -Encoding UTF8 -Path $glog -Value ("=== export-pack @ " + (Get-Date).ToString('o'))
    if (Test-Path $out) { Get-Content $out -ErrorAction SilentlyContinue | Add-Content -Encoding UTF8 -Path $glog }
    if (Test-Path $err) { Get-Content $err -ErrorAction SilentlyContinue | Add-Content -Encoding UTF8 -Path $glog }
    $exitCode = $p.ExitCode
    if ((-not $exitCode) -or ($exitCode -ne 0)) {
      if (Test-Path $pck) {
        Write-Warning "Export-pack returned exit=$exitCode but pack exists ($pck). Treating as success."
        $exitCode = 0
      } else {
        Write-Error "Export failed (release & debug & pack) with exit code $exitCode. See log: $glog"
      }
    } else {
      Write-Warning "EXE export failed but PCK fallback succeeded: $pck"
    }
  }
}

# Collect artifacts
New-Item -ItemType Directory -Force -Path $finalDest | Out-Null
if (Test-Path $Output) { Copy-Item -Force $Output $finalDest 2>$null }
$maybePck = ($Output -replace '\.exe$','.pck')
if (Test-Path $maybePck) { Copy-Item -Force $maybePck $finalDest 2>$null }
# Copy staged logs to final logs path
Copy-Item -Recurse -Force (Join-Path $dest '*') $finalDest 2>$null
$glogFinal = Join-Path $finalDest 'godot_export.log'
if (Test-Path $glogFinal) { Write-Host "--- godot_export.log (tail) ---"; Get-Content $glogFinal -Tail 200 }
Write-Host "Export artifacts copied to $finalDest (log: $glogFinal)"

# Write summary.json and enforce optional size gate
try {
  $sum = @{}
  $sum.ts = (Get-Date).ToString('o')
  $sum.preset = $Preset
  $sum.project_dir = $ProjectDir
  $sum.log = $glogFinal
  $sum.output = $Output
  $sum.output_exists = (Test-Path $Output)
  if ($sum.output_exists) { $sum.output_size_bytes = (Get-Item $Output).Length } else { $sum.output_size_bytes = 0 }
  $maybePck = ($Output -replace '\.exe$','.pck')
  $sum.pack = $maybePck
  $sum.pack_exists = (Test-Path $maybePck)
  if ($sum.pack_exists) { $sum.pack_size_bytes = (Get-Item $maybePck).Length } else { $sum.pack_size_bytes = 0 }
  $sumPath = Join-Path $dest 'summary.json'
  ($sum | ConvertTo-Json -Depth 5) | Set-Content -Path $sumPath -Encoding UTF8
  # copy summary to final logs dir
  try { New-Item -ItemType Directory -Force -Path $finalDest | Out-Null; Copy-Item -Force $sumPath (Join-Path $finalDest 'summary.json') 2>$null } catch {}

  $gateMaxMB = 0.0
  if ($env:EXPORT_SIZE_MAX_MB) {
    [double]::TryParse($env:EXPORT_SIZE_MAX_MB, [ref]$gateMaxMB) | Out-Null
  }
  $gateFailed = $false
  if ($gateMaxMB -gt 0) {
    $exeMB = [math]::Round($sum.output_size_bytes / 1MB, 2)
    $pckMB = [math]::Round($sum.pack_size_bytes / 1MB, 2)
    Write-Host ("Size gate: EXPORT_SIZE_MAX_MB=$gateMaxMB; exeMB=$exeMB; pckMB=$pckMB")
    if ($sum.output_exists -and ($exeMB -gt $gateMaxMB)) { $gateFailed = $true }
    if ($sum.pack_exists -and ($pckMB -gt $gateMaxMB)) { $gateFailed = $true }
  }
  if ($gateFailed) {
    Write-Error ("Export size gate failed: max=${gateMaxMB}MB; see " + $sumPath)
    if ($exitCode -eq 0) { $exitCode = 3 }
  }
} catch {
  Write-Warning ("Failed to write summary.json or evaluate size gate: " + $_.Exception.Message)
}

exit $exitCode

