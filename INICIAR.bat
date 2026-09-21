@echo off
setlocal
cd /d "%~dp0"

if not exist ".env" (
  echo Falta el archivo .env. Copia .env.example como .env.
  pause
  exit /b 1
)

findstr /B /C:"TELEGRAM_BOT_TOKEN=" .env | findstr /V /R /C:"^TELEGRAM_BOT_TOKEN=$" >nul
if errorlevel 1 (
  echo Completa TELEGRAM_BOT_TOKEN en el archivo .env.
  pause
  exit /b 1
)

docker compose up --build
pause
