echo off
call %~dp0parameters.bat

if "%1" neq "" set app_label=%1

pushd %base_dir%

python manage.py migrate %app_label% zero

del %app_label%\migrations\0*.py

if "%database%" == "postgres" (
    "%PGPATH%\psql" -h %PGHOST% -U %PGUSER% -d %PGDATABASE% -f %app_label%\sql\drop_app_tables.sql
    "%PGPATH%\psql" -h %PGHOST% -U %PGUSER% -d %PGDATABASE% -c "delete from django_migrations where app = '%app_label%'"
) else (
    sqlcmd -S %MSSQL_DB_HOST% -U %MSSQL_DB_USER% -P %MSSQL_DB_PASSWORD% -d %MSSQL_DB_NAME% -i %app_label%\sql\delete_seikyu_migrations.sql
    sqlcmd -S %MSSQL_DB_HOST% -U %MSSQL_DB_USER% -P %MSSQL_DB_PASSWORD% -d %MSSQL_DB_NAME% -i %app_label%\sql\drop_app_tables.sql
)

popd
