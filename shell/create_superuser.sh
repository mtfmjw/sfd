#!/bin/bash

# Source parameters
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$SCRIPT_DIR/parameters.sh"

cd "$BASE_DIR" || exit

export DJANGO_SUPERUSER_PASSWORD=P09olp09ol

echo "Creating superuser 'admin'..."
python manage.py createsuperuser --no-input --username admin --email admin@example.com

if [ $? -eq 0 ]; then
    echo "Superuser created successfully."
else
    echo "Failed to create superuser (it might already exist)."
fi
