@echo off
REM This script must be run with: call activate_env.bat
REM or it won't persist the virtual environment activation
set "DJANGO_SETTINGS_MODULE=sfd_prj.settings"
.venv\Scripts\activate.bat
