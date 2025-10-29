echo off
call %~dp0parameters.bat

if "%1" neq "" set app_label=%1
echo specified app_label: %app_label%


pushd %base_dir%

@REM python manage.py migrate

if "%database%" == "postgres" (
    echo python manage.py migrate %app_label% --database=postgres   
    python manage.py migrate %app_label% --database=postgres   
) else (
    echo python manage.py migrate %app_label% --database=default   
    python manage.py migrate %app_label% --database=default   
)

popd
