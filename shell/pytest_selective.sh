#!/bin/bash

# Enable command history for easier arrow-key usage if running interactively
set -o history -o histexpand 2>/dev/null

# Source parameters
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$SCRIPT_DIR/parameters.sh"

echo "specified app_label: $APP_LABEL"

echo ""
echo "================================================================"
echo "                   SELECTIVE PYTEST RUNNER"
echo "================================================================"
echo "Base Directory: $BASE_DIR"
echo "App: $APP_LABEL"
echo ""

# Function to run pytest with common parameters
run_pytest() {
    local args="$1"
    local filename="$2"
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local html_report="tests/$APP_LABEL/${filename}_${timestamp}.html"
    
    echo "Running pytest with args: $args"
    
    cd "$BASE_DIR" || exit
    
    # Run pytest
    python -m pytest "$APP_LABEL/tests/" $args \
        --html="$html_report" \
        --self-contained-html \
        --cov="$APP_LABEL" \
        --cov-report=html:htmlcov \
        --cov-report=term-missing \
        --reuse-db \
        --nomigrations \
        -v
        
    echo ""
    if [ -f "$html_report" ]; then
        echo "HTML Report generated: $html_report"
    fi
    
    if [ -f "htmlcov/index.html" ]; then
        echo "Coverage Report generated: htmlcov/index.html"
    fi
    
    echo "To view reports, open them in your browser or VS Code."
}

# Main loop
while true; do
    echo "----------------------------------------------------------------"
    echo "                     TEST TYPE SELECTION"
    echo "----------------------------------------------------------------"
    echo "[1] Unit Tests         - Fast tests for individual components"
    echo "[2] Integration Tests  - Tests for component interactions"
    echo "[3] Performance Tests  - Speed and efficiency tests"
    echo "[4] All Tests          - Run complete test suite"
    echo "[5] Custom Selection   - Run specific test modules"
    echo "[6] View Test Reports  - List existing HTML reports"
    echo "[Q] Quit"
    echo "----------------------------------------------------------------"
    read -p "Please select an option (1-6 or Q): " choice
    
    case $choice in
        1)
            echo ""
            echo "================================================================"
            echo "                       UNIT TESTS"
            echo "================================================================"
            run_pytest "-m unit" "pytest_unit"
            ;;
        2)
            echo ""
            echo "================================================================"
            echo "                    INTEGRATION TESTS"
            echo "================================================================"
            run_pytest "-m integration" "pytest_integration"
            ;;
        3)
            echo ""
            echo "================================================================"
            echo "                    PERFORMANCE TESTS"
            echo "================================================================"
            run_pytest "-m performance" "pytest_performance"
            ;;
        4)
            echo ""
            echo "================================================================"
            echo "                      ALL TESTS"
            echo "================================================================"
            run_pytest "" "pytest_all"
            ;;
        5)
            # Custom Selection Menu
            echo ""
            echo "================================================================"
            echo "                   CUSTOM TEST SELECTION"
            echo "================================================================"
            echo "Available test modules in $APP_LABEL/tests/:"
            
            cd "$BASE_DIR" || exit
            if [ -d "$APP_LABEL/tests" ]; then
                # List test files, stripping path and extension for display
                for f in "$APP_LABEL"/tests/test_*.py; do
                    [ -e "$f" ] || continue
                    basename "$f" .py
                done
            fi
            
            echo ""
            echo "Select test execution option:"
            echo "[1] Run specific test module (e.g., test_models)"
            echo "[2] Run tests with custom marker (e.g., slow, download, font)"
            echo "[3] Run tests matching pattern (e.g., *download*)"
            echo "[4] Return to main menu"
            echo ""
            read -p "Enter your choice (1-4): " custom_choice
            
            case $custom_choice in
                1)
                    read -p "Enter test module name (without .py extension): " module_name
                    if [ -z "$module_name" ]; then
                        echo "No module specified."
                    else
                         # Run specific module
                         cd "$BASE_DIR" || exit
                         timestamp=$(date +"%Y%m%d_%H%M%S")
                         html_report="tests/$APP_LABEL/pytest_${module_name}_${timestamp}.html"
                         
                         python -m pytest "$APP_LABEL/tests/${module_name}.py" \
                            --html="$html_report" \
                            --self-contained-html \
                            --cov="$APP_LABEL" \
                            --cov-report=term-missing \
                            --reuse-db \
                            --nomigrations \
                            -v
                            
                         echo "Report: $html_report"
                    fi
                    ;;
                2)
                     echo "Available markers: unit, integration, performance, slow, download, font, logging, middleware"
                     read -p "Enter marker name: " marker_name
                     if [ -n "$marker_name" ]; then
                         run_pytest "-m $marker_name" "pytest_marker_$marker_name"
                     fi
                     ;;
                3)
                     read -p "Enter test name pattern (e.g., *download*): " pattern
                     if [ -n "$pattern" ]; then
                         run_pytest "-k \"$pattern\"" "pytest_pattern"
                     fi
                     ;;
                4)
                     continue
                     ;;
                *)
                     echo "Invalid custom choice."
                     ;;
            esac
            ;;
        6)
            echo ""
            echo "================================================================"
            echo "                     VIEW TEST REPORTS"
            echo "================================================================"
            cd "$BASE_DIR" || exit
            if [ -d "tests/$APP_LABEL" ]; then
                echo "Reports location: tests/$APP_LABEL/"
                ls -lh tests/$APP_LABEL/*.html 2>/dev/null || echo "No HTML reports found."
            else
                echo "No test reports directory found at: tests/$APP_LABEL"
            fi
            if [ -f "htmlcov/index.html" ]; then
                echo "Coverage report at: htmlcov/index.html"
            fi
            ;;
        [Qq]*|exit|quit)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid choice. Please try again."
            ;;
    esac
    
    echo ""
    read -p "Return to main menu? (y/n): " continue_choice
    case $continue_choice in
        [Yy]*|yes) continue ;;
        *) exit 0 ;;
    esac
done
