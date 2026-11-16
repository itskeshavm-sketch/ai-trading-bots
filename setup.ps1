# One-shot setup for ai-trading-bots (Windows PowerShell 5.1+).
#
#   powershell -ExecutionPolicy Bypass -File setup.ps1
#
# Creates a virtualenv, installs requirements, then walks you through picking
# an AI provider (base URL + key + model). Any OpenAI-compatible endpoint works.

param(
  [string]$Python = "",
  [string]$BaseUrl = "",
  [string]$ApiKey = "",
  [string]$Model = "",
  [switch]$NoVenv,
  [switch]$SkipProvider,
  [switch]$SkipDeps
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    $msg" -ForegroundColor Yellow }

# ---------------------------------------------------------------- python
function Find-Python {
  param([string]$Preferred)
  if ($Preferred) { return $Preferred }
  foreach ($cmd in @("python", "py", "python3")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
      try {
        if ($cmd -eq "py") { & py -3 --version *> $null; if ($LASTEXITCODE -eq 0) { return "py -3" } }
        else { & $cmd --version *> $null; if ($LASTEXITCODE -eq 0) { return $cmd } }
      } catch { }
    }
  }
  return $null
}

$pyCmd = Find-Python -Preferred $Python
if (-not $pyCmd) {
  Write-Host "Python 3 not found. Install it from https://www.python.org/downloads/ (tick 'Add to PATH')." -ForegroundColor Red
  exit 1
}
Write-Step "Python: $pyCmd"

# ---------------------------------------------------------------- venv
$pythonExe = "python"
if ($NoVenv) {
  Write-Step "Skipping virtualenv (using system Python)"
} else {
  if (-not (Test-Path ".venv")) {
    Write-Step "Creating virtualenv .venv"
    Invoke-Expression "$pyCmd -m venv .venv"
    if ($LASTEXITCODE -ne 0) { Write-Warn "venv creation failed, falling back to system Python"; $NoVenv = $true }
  }
  if (-not $NoVenv) {
    $pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    Write-Ok ".venv ready"
  }
}

# ---------------------------------------------------------------- deps
if (-not $SkipDeps) {
  Write-Step "Installing dependencies (this can take a minute)"
  & $pythonExe -m pip install --upgrade pip --quiet
  & $pythonExe -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) {
    Write-Warn "pip install reported errors - the provider wizard still works, but the bot needs these packages"
  } else {
    Write-Ok "requirements installed"
  }
}

# ---------------------------------------------------------------- provider
if (-not $SkipProvider) {
  Write-Step "AI provider setup (base URL + key + model)"
  if ($BaseUrl -and $ApiKey -and $Model) {
    & $pythonExe setup_provider.py --base-url $BaseUrl --api-key $ApiKey --model $Model
  } else {
    & $pythonExe setup_provider.py
  }
}

Write-Host ""
Write-Host "Done. Next:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\activate            # CMD: .venv\Scripts\activate"
Write-Host "  python main.py --ai --market nse    # paper trade, no real money"
Write-Host "  python main.py --ai --market crypto"
Write-Host "  python dashboard_server.py           # then open http://localhost:8000/dashboard2.html"
Write-Host ""
Write-Host "Paper mode is the default. Real orders need --live plus broker keys."
Write-Host "Change provider any time:  python setup_provider.py"
