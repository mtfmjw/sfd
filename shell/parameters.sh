#!/bin/bash

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Go to parent directory (workspace root)
export BASE_DIR="$(dirname "$SCRIPT_DIR")"
# echo "Base Directory: $BASE_DIR"

export PROJECT="sfd_prj"
export APP_LABEL="sfd"
export DATABASE="postgres"

# echo "Current app: $APP_LABEL"
