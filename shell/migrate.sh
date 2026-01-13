#!/bin/bash

# Source parameters
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$SCRIPT_DIR/parameters.sh"

# Accepts optional argument to override default app_label
if [ -n "$1" ]; then
    APP_LABEL="$1"
fi

echo "specified app_label: $APP_LABEL"

cd "$BASE_DIR" || exit

# If argument is "all", migrate everything on default database (or all databases if configured differently, but standard django is default)
# However, the batch script seems to imply "all" runs without app label on default DB? 
# Batch script: if "%app_label%" == "all" ( python manage.py migrate ... )
if [ "$APP_LABEL" == "all" ]; then
    echo "Running global migrate..."
    python manage.py migrate
    exit 0
fi

# Migration for specific app/database
if [ "$DATABASE" == "postgres" ]; then
    echo "python manage.py migrate $APP_LABEL --database=postgres"
    python manage.py migrate "$APP_LABEL" --database=postgres
else
    echo "python manage.py migrate $APP_LABEL"
    python manage.py migrate "$APP_LABEL"
fi
