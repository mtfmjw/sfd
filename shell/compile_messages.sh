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

python manage.py compilemessages --locale=ja
