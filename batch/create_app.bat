echo off
call %~dp0parameters

if "%1" == "" (
    echo "No app name provided"
    exit /b 1
)

pushd %base_dir%
django-admin startapp %1

cd %1
del /q /s models.py tests.py views.py

mkdir models
mkdir forms
mkdir views
mkdir tests
mkdir locale
mkdir templates
mkdir static
mkdir static\css
mkdir static\js
mkdir static\images

echo.> models\__init__.py
echo.> forms\__init__.py
echo.> views\__init__.py
echo.> tests\__init__.py

popd
