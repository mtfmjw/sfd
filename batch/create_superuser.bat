echo off
setlocal enabledelayedexpansion
call %~dp0parameters

pushd %base_dir%
set DJANGO_SUPERUSER_PASSWORD=P09olp09ol
python manage.py createsuperuser --no-input --username admin --email admin@example.com

popd
