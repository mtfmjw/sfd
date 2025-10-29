echo off
call %~dp0parameters

:: create role
echo "%PGPATH%\psql" -h %PGHOST% -U postgres -d postgres -c "CREATE ROLE %PGUSER% with CREATEDB CREATEROLE LOGIN PASSWORD '%PGPASSWORD%';"
"%PGPATH%\psql" -h %PGHOST% -U postgres -d postgres -c "CREATE ROLE %PGUSER% with CREATEDB CREATEROLE LOGIN PASSWORD '%PGPASSWORD%';"

:: create database
echo "%PGPATH%\psql" -h %PGHOST% -U %PGUSER% -d postgres -c "create database %PGDATABASE% encoding='utf8';"
"%PGPATH%\psql" -h %PGHOST% -U %PGUSER% -d postgres -c "create database %PGDATABASE% encoding='utf8';"
