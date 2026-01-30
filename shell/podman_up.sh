#!/bin/bash
set -e

# Get the root directory
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

echo "Starting Podman containers..."
if command -v podman-compose &> /dev/null; then
    podman-compose -f "$PROJECT_ROOT/compose/docker-compose.yml" up -d
else
    # Fallback to podman compose (requires docker-compose or similar backend usually, or newer podman versions)
    podman compose -f "$PROJECT_ROOT/compose/docker-compose.yml" up -d
fi

echo "Containers started."
