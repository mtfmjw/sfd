@echo off
setlocal enabledelayedexpansion enableextensions

call %~dp0parameters.bat
pushd %base_dir%
REM Use the virtual environment python with pytest and same settings as pyproject.toml
.venv\Scripts\python.exe -m pytest %app_label%/tests/%1.py --self-contained-html --reuse-db --nomigrations -v
popd