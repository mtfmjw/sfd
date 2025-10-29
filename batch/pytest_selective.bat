@echo off
setlocal enabledelayedexpansion enableextensions

call %~dp0parameters.bat

REM Create timestamp for unique filename
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,8%_%dt:~8,6%"

if "%1" neq "" set app_label=%1
echo specified app_label: %app_label%

echo.
echo ================================================================
echo                    SELECTIVE PYTEST RUNNER
echo ================================================================
echo Base Directory: %base_dir%
echo App: %app_label%
echo.

:main_menu
echo ----------------------------------------------------------------
echo                      TEST TYPE SELECTION
echo ----------------------------------------------------------------
echo [1] Unit Tests         - Fast tests for individual components
echo [2] Integration Tests  - Tests for component interactions
echo [3] Performance Tests  - Speed and efficiency tests
echo [4] All Tests          - Run complete test suite
echo [5] Custom Selection   - Run specific test modules
echo [6] View Test Reports  - Open existing HTML reports
echo [Q] Quit
echo ----------------------------------------------------------------
set /p choice="Please select an option (1-6 or Q): "

if /i "%choice%"=="1" goto unit_tests
if /i "%choice%"=="2" goto integration_tests
if /i "%choice%"=="3" goto performance_tests
if /i "%choice%"=="4" goto all_tests
if /i "%choice%"=="5" goto custom_selection
if /i "%choice%"=="6" goto view_reports
if /i "%choice%"=="q" goto exit
if /i "%choice%"=="quit" goto exit

echo Invalid choice. Please try again.
echo.
goto main_menu

:unit_tests
echo.
echo ================================================================
echo                        UNIT TESTS
echo ================================================================

pushd %base_dir%
.venv\Scripts\python.exe -m pytest %app_label%/tests/ -m "unit" --html=tests/%app_label%/pytest_unit_%timestamp%.html --self-contained-html --cov=%app_label% --cov-report=html:htmlcov --cov-report=term-missing --reuse-db --nomigrations -v

REM Open the report if it exists
if exist "tests\%app_label%\pytest_unit_%timestamp%.html" (
    start "" "tests\%app_label%\pytest_unit_%timestamp%.html"
)

REM Open coverage report if it exists
if exist "htmlcov\index.html" (
    echo Opening coverage report...
    start "" "htmlcov\index.html"
)
popd
goto continue_prompt

:integration_tests
echo.
echo ================================================================
echo                     INTEGRATION TESTS
echo ================================================================

pushd %base_dir%
.venv\Scripts\python.exe -m pytest %app_label%/tests/ -m "integration" --html=tests/%app_label%/pytest_integration_%timestamp%.html --self-contained-html --cov=%app_label% --cov-report=html:htmlcov --cov-report=term-missing --reuse-db --nomigrations -v

REM Open the report if it exists
if exist "tests\%app_label%\pytest_integration_%timestamp%.html" (
    start "" "tests\%app_label%\pytest_integration_%timestamp%.html"
)
popd
goto continue_prompt

:performance_tests
echo.
echo ================================================================
echo                    PERFORMANCE TESTS
echo ================================================================
pushd %base_dir%
.venv\Scripts\python.exe -m pytest %app_label%/tests/ -m "performance" --html=tests/%app_label%/pytest_performance_%timestamp%.html --self-contained-html --cov=%app_label% --cov-report=html:htmlcov --cov-report=term-missing --reuse-db --nomigrations -v

REM Open the report if it exists
if exist "tests\%app_label%\pytest_performance_%timestamp%.html" (
    start "" "tests\%app_label%\pytest_performance_%timestamp%.html"
)
popd
goto continue_prompt

:all_tests
echo.
echo ================================================================
echo                      ALL TESTS
echo ================================================================
echo Running complete test suite...
pushd %base_dir%

REM Create timestamp for unique filename
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,8%_%dt:~8,6%"

REM Run all tests with HTML output and coverage
.venv\Scripts\python.exe -m pytest %app_label%/tests/ --html=tests/%app_label%/pytest_all_%timestamp%.html --self-contained-html --cov=%app_label% --cov-report=html:htmlcov --cov-report=term-missing --reuse-db --nomigrations -v

REM Open the report if it exists
if exist "tests\%app_label%\pytest_all_%timestamp%.html" (
    start "" "tests\%app_label%\pytest_all_%timestamp%.html"
)

REM Open coverage report if it exists
if exist "htmlcov\index.html" (
    echo Opening coverage report...
    start "" "htmlcov\index.html"
)

popd
goto continue_prompt

:custom_selection
echo.
echo ================================================================
echo                    CUSTOM TEST SELECTION
echo ================================================================
echo Available test modules in %app_label%/tests/:
pushd %base_dir%
echo.
for %%f in (%app_label%\tests\test_*.py) do (
    echo - %%~nf
)
echo.
popd

echo Select test execution option:
echo [1] Run specific test module (e.g., test_models.py)
echo [2] Run tests with custom marker (e.g., slow, download, font)
echo [3] Run tests matching pattern (e.g., *download*)
echo [4] Return to main menu
echo.
set /p custom_choice="Enter your choice (1-4): "

if "%custom_choice%"=="1" goto specific_module
if "%custom_choice%"=="2" goto custom_marker
if "%custom_choice%"=="3" goto pattern_match
if "%custom_choice%"=="4" goto main_menu

echo Invalid choice. Returning to main menu.
goto main_menu

:specific_module
echo.
set /p module_name="Enter test module name (without .py extension): "
if "%module_name%"=="" (
    echo No module specified. Returning to main menu.
    goto main_menu
)

echo Running tests for module: %module_name%
pushd %base_dir%

REM Run specific module tests
.venv\Scripts\python.exe -m pytest %app_label%/tests/%module_name%.py --html=tests/%app_label%/pytest_%module_name%_%timestamp%.html --self-contained-html --cov=%app_label% --cov-report=term-missing --reuse-db --nomigrations -v

REM Open the report if it exists
if exist "tests\%app_label%\pytest_%module_name%_%timestamp%.html" (
    start "" "tests\%app_label%\pytest_%module_name%_%timestamp%.html"
)

popd
goto continue_prompt

:custom_marker
echo.
echo Available test markers:
echo - unit: Unit tests
echo - integration: Integration tests  
echo - performance: Performance tests
echo - slow: Slow-running tests
echo - download: Download functionality tests
echo - font: Font-related tests
echo - logging: Logging functionality tests
echo - middleware: Middleware tests
echo.
set /p marker_name="Enter marker name: "
if "%marker_name%"=="" (
    echo No marker specified. Returning to main menu.
    goto main_menu
)

echo Running tests with marker: %marker_name%
pushd %base_dir%

REM Create timestamp for unique filename
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,8%_%dt:~8,6%"

REM Run tests with specific marker
.venv\Scripts\python.exe -m pytest %app_label%/tests/ -m "%marker_name%" --html=tests/%app_label%/pytest_marker_%marker_name%_%timestamp%.html --self-contained-html --cov=%app_label% --cov-report=term-missing --reuse-db --nomigrations -v

REM Open the report if it exists
if exist "tests\%app_label%\pytest_marker_%marker_name%_%timestamp%.html" (
    start "" "tests\%app_label%\pytest_marker_%marker_name%_%timestamp%.html"
)

popd
goto continue_prompt

:pattern_match
echo.
set /p pattern="Enter test name pattern (e.g., *download*, test_model_*): "
if "%pattern%"=="" (
    echo No pattern specified. Returning to main menu.
    goto main_menu
)

echo Running tests matching pattern: %pattern%
pushd %base_dir%

REM Create timestamp for unique filename
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,8%_%dt:~8,6%"

REM Run tests matching pattern
.venv\Scripts\python.exe -m pytest %app_label%/tests/ -k "%pattern%" --html=tests/%app_label%/pytest_pattern_%timestamp%.html --self-contained-html --cov=%app_label% --cov-report=term-missing --reuse-db --nomigrations -v

REM Open the report if it exists
if exist "tests\%app_label%\pytest_pattern_%timestamp%.html" (
    start "" "tests\%app_label%\pytest_pattern_%timestamp%.html"
)

popd
goto continue_prompt

:view_reports
echo.
echo ================================================================
echo                     VIEW TEST REPORTS
echo ================================================================
echo Opening test reports directory...
pushd %base_dir%
if exist "tests\%app_label%" (
    start "" "tests\%app_label%"
    echo Test reports directory opened in file explorer.
) else (
    echo No test reports directory found at: tests\%app_label%
)

if exist "htmlcov\index.html" (
    echo.
    set /p open_coverage="Open coverage report? (y/n): "
    if /i "!open_coverage!"=="y" start "" "htmlcov\index.html"
)
popd
goto continue_prompt

:continue_prompt
echo.
echo ----------------------------------------------------------------
set /p continue_choice="Return to main menu? (y/n): "
if /i "%continue_choice%"=="y" goto main_menu
if /i "%continue_choice%"=="yes" goto main_menu

:exit
echo.
echo ================================================================
echo                    TEST EXECUTION COMPLETE
echo ================================================================
echo Thank you for using the Selective Pytest Runner!
echo.
@REM pause
exit /b 0
