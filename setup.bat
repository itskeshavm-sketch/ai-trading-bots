@echo off
REM One-shot setup for ai-trading-bots (CMD).
REM   setup.bat
REM Creates a virtualenv, installs requirements, then walks you through picking
REM an AI provider (base URL + key + model). Any OpenAI-compatible endpoint works.
setlocal
cd /d "%~dp0"

where powershell >nul 2>nul
if errorlevel 1 (
  echo Windows PowerShell is required. Install Python 3 from https://www.python.org/downloads/ ^(tick "Add to PATH"^).
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
exit /b %errorlevel%
