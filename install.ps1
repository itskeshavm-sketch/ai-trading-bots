# One-line installer for ai-trading-bots (PowerShell).
#
#   irm https://raw.githubusercontent.com/itskeshavm-sketch/ai-trading-bots/main/install.ps1 | iex
#
# Downloads the project, creates a virtualenv, installs dependencies and asks
# which AI provider to use. No git needed. Safe to re-run: an existing folder
# is updated instead of overwritten.

param(
  [string]$Dir = "",
  [string]$BaseUrl = "",
  [string]$ApiKey = "",
  [string]$Model = "",
  [switch]$SkipDeps,
  [switch]$SkipProvider,
  [switch]$NoVenv
)

$ErrorActionPreference = "Stop"

$Repo = "itskeshavm-sketch/ai-trading-bots"
$Zip = "https://codeload.github.com/$Repo/zip/refs/heads/main"
$Target = if ($Dir) { $Dir } elseif ($env:AI_TRADING_DIR) { $env:AI_TRADING_DIR } else { Join-Path (Get-Location) "ai-trading-bots" }

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    $msg" -ForegroundColor Yellow }

Write-Step "Installing ai-trading-bots into $Target"

if (Test-Path (Join-Path $Target ".git")) {
  Write-Step "Existing git checkout found - updating"
  try {
    git -C $Target pull --ff-only | Out-Null
    Write-Ok "updated to latest"
  } catch {
    Write-Warn "git pull failed, continuing with the copy on disk"
  }
} elseif (Test-Path $Target) {
  Write-Step "Folder exists but is not a git checkout - refreshing it"
  Remove-Item $Target -Recurse -Force
  New-Item -ItemType Directory -Path $Target -Force | Out-Null
} else {
  New-Item -ItemType Directory -Path $Target -Force | Out-Null
}

if (-not (Test-Path (Join-Path $Target ".git"))) {
  $git = Get-Command git -ErrorAction SilentlyContinue
  if ($git) {
    Write-Step "Cloning with git"
    git clone --depth 1 "https://github.com/$Repo.git" $Target | Out-Null
    Write-Ok "cloned"
  } else {
    Write-Step "git not found - downloading the zip instead"
    $tmp = Join-Path $env:TEMP ("aitb_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $zipPath = Join-Path $tmp "repo.zip"
    Invoke-WebRequest -Uri $Zip -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $tmp -Force
    $inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
    Copy-Item -Path (Join-Path $inner.FullName "*") -Destination $Target -Recurse -Force
    Remove-Item $tmp -Recurse -Force
    Write-Ok "downloaded"
  }
}

# ---------------------------------------------------------------- setup
$setup = Join-Path $Target "setup.ps1"
if (-not (Test-Path $setup)) {
  Write-Warn "setup.ps1 not found in the download - stopping here"
  Write-Host "Manual step: cd `"$Target`" and run  powershell -ExecutionPolicy Bypass -File setup.ps1" -ForegroundColor Yellow
  exit 1
}

Write-Step "Running setup (virtualenv + dependencies + provider wizard)"
$setupArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $setup)
if ($SkipDeps)   { $setupArgs += "-SkipDeps" }
if ($SkipProvider) { $setupArgs += "-SkipProvider" }
if ($NoVenv)     { $setupArgs += "-NoVenv" }
if ($BaseUrl)    { $setupArgs += @("-BaseUrl", $BaseUrl) }
if ($ApiKey)     { $setupArgs += @("-ApiKey", $ApiKey) }
if ($Model)      { $setupArgs += @("-Model", $Model) }
& powershell @setupArgs

Write-Host ""
Write-Host "Installed at: $Target" -ForegroundColor Green
Write-Host "cd `"$Target`"   then   .\.venv\Scripts\activate   then   python main.py --ai --market nse" -ForegroundColor Green
