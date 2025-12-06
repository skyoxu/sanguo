param(
  [string]$Version = '4.5.1.stable.mono'
)

$ErrorActionPreference = 'Stop'
Write-Host ("Installing Godot export templates for version: $Version")

$root = Join-Path $env:APPDATA 'Godot'
$tpl1 = Join-Path $root ("templates/" + $Version)
$tpl2 = Join-Path $root ("export_templates/" + $Version)
New-Item -ItemType Directory -Force -Path $tpl1, $tpl2 | Out-Null

$tmp   = Join-Path $env:TEMP ("godot_templates_" + $Version + '.tpz')
$tmpUn = Join-Path $env:TEMP ("godot_templates_" + $Version + '_unpacked')
$urls = @(
  ('https://github.com/godotengine/godot/releases/download/' + ($Version -replace '\.stable\.mono$','-stable') + '/Godot_v' + ($Version -replace '\.stable\.mono$','') + '-stable_export_templates.tpz'),
  ('https://downloads.tuxfamily.org/godotengine/' + ($Version -replace '\.stable\.mono$','') + '/Godot_v' + ($Version -replace '\.stable\.mono$','') + '-stable_export_templates.tpz')
)
$downloaded = $false
foreach ($u in $urls) {
  try {
    Write-Host "Downloading: $u"
    Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $tmp -TimeoutSec 600
    $downloaded = $true
    break
  } catch { Write-Warning "Download failed: $($_.Exception.Message)" }
}
if (-not $downloaded) { throw 'Unable to download export templates from known URLs.' }

if (Test-Path $tmpUn) { Remove-Item -Recurse -Force $tmpUn }
Expand-Archive -LiteralPath $tmp -DestinationPath $tmpUn -Force
$src = if (Test-Path (Join-Path $tmpUn 'templates')) { Join-Path $tmpUn 'templates' } else { $tmpUn }
Copy-Item -Recurse -Force (Join-Path $src '*') $tpl1
Copy-Item -Recurse -Force (Join-Path $src '*') $tpl2

Write-Host "Templates installed to:"
Write-Host "  $tpl1"
Write-Host "  $tpl2"

