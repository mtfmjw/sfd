echo off
call %~dp0parameters.bat

if "%1" neq "" set app_label=%1
echo specified app_label: %app_label%

pushd %base_dir%


echo python manage.py makemigrations %app_label%
python manage.py makemigrations %app_label%

popd
