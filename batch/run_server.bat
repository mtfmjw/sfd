call %~dp0parameters.bat

pushd %base_dir%
python manage.py runserver
popd
