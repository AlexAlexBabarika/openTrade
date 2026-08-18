@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 goto docker_missing
docker compose version >nul 2>&1
if errorlevel 1 goto compose_missing

call :ensure_docker
if errorlevel 1 goto docker_timeout

echo Stopping OpenQuant...
docker compose stop
if errorlevel 1 goto stop_failed
echo.
echo OpenQuant is stopped. Your accounts, settings, and data were preserved.
exit /b 0

:ensure_docker
docker info >nul 2>&1
if not errorlevel 1 exit /b 0
echo Starting Docker Desktop so OpenQuant can be stopped cleanly...
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

:stop_failed
echo OpenQuant could not be stopped. Review the message above.
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
