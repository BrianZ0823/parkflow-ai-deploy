@echo off
setlocal

cd /d "%~dp0"

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env from .env.example.
  echo Please edit .env and set DASHSCOPE_API_KEY before exposing this service.
  notepad ".env"
)

docker compose up -d --build

echo.
echo ParkFlow frontend: http://localhost:8080
echo ParkFlow backend:  http://localhost:8765/api/health
echo.
