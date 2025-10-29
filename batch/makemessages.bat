echo off
call %~dp0parameters.bat

if "%1" neq "" set app_label=%1
echo specified app_label: %app_label%

pushd %base_dir%\%app_label%
python ..\manage.py makemessages -l ja --no-obsolete --ignore=.venv --ignore=staticfiles --ignore=media

popd