@echo off
REM Enhanced batch script for git commits with multi-line message support
REM Usage: git-commit-multiline.bat "Title" "Description line 1" "Description line 2" ...
REM Or: git-commit-multiline.bat "Single line message"

setlocal enabledelayedexpansion

REM Check if at least one argument is provided
if "%~1"=="" (
    echo Error: Please provide a commit message
    echo Usage: git-commit-multiline.bat "Title" ["Description line 1"] ["Description line 2"] ...
    echo Example: git-commit-multiline.bat "Add feature" "- Implement new functionality" "- Add tests" "- Update documentation"
    exit /b 1
)

echo Adding all changes to git...
git add -A

REM Create temporary file for commit message
set "temp_file=%TEMP%\commit_msg_%RANDOM%.tmp"

REM Write first argument (title) to temp file
echo %~1 > "%temp_file%"

REM Add additional arguments as separate lines
shift
:loop
if "%~1"=="" goto :done
echo. >> "%temp_file%"
echo %~1 >> "%temp_file%"
shift
goto :loop
:done

echo Committing changes...
echo Message preview:
type "%temp_file%"
echo.

REM Commit using the temporary file
git commit -F "%temp_file%"

REM Clean up
del "%temp_file%"

if %errorlevel% equ 0 (
    echo Successfully committed changes!
) else (
    echo Failed to commit changes. Check if there are any changes to commit.
)
