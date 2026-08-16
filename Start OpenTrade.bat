@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 goto docker_missing
docker compose version >nul 2>&1
if errorlevel 1 goto compose_missing

call :ensure_docker
if errorlevel 1 goto docker_timeout

echo Starting OpenTrade...
docker compose up -d --wait --wait-timeout 180
if errorlevel 1 goto start_failed

set "OPENTRADE_PORT=8000"
for /f "tokens=2 delims=:" %%P in ('docker compose port opentrade 8000 2^>nul') do set "OPENTRADE_PORT=%%P"
echo.
echo OpenTrade is ready at http://localhost:%OPENTRADE_PORT%
start "" "http://localhost:%OPENTRADE_PORT%"
exit /b 0

:ensure_docker
docker info >nul 2>&1
if not errorlevel 1 exit /b 0
echo Starting Docker Desktop...
docker desktop start >nul 2>&1
if errorlevel 1 (
  if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
)
for /l %%I in (1,1,60) do (
  docker info >nul 2>&1
  if not errorlevel 1 exit /b 0
  timeout /t 2 /nobreak >nul
)
exit /b 1

:start_failed
echo.
echo Recent container logs:
docker compose logs --tail=100
echo.
echo OpenTrade startup failed. Review the messages above for the cause.
pause
exit /b 1

:docker_missing
echo Docker was not found. Install Docker Desktop, then try again.
pause
exit /b 1

:compose_missing
echo Docker Compose v2 was not found. Update Docker Desktop, then try again.
pause
exit /b 1

:docker_timeout
echo Docker did not become ready within two minutes.
pause
exit /b 1
