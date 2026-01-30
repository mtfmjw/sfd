@echo off
cd /d "%~dp0\.."
echo Starting Podman containers...
podman compose -f compose/docker-compose.yml up -d
if errorlevel 1 (
    echo "podman compose" failed. Trying "podman-compose"...
    podman-compose -f compose/docker-compose.yml up -d
)
if errorlevel 1 (
    echo "podman-compose" failed. Please ensure you have podman and a compose provider installed.
    pause
    exit /b 1
)
echo Containers started.
pause
