FROM mcr.microsoft.com/devcontainers/python:3.14

# Prevent Python from buffering logs or writing .pyc files
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies (needed for Postgres and general Django tools)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    postgresql-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# The workspace will be mounted here automatically by VS Code
WORKDIR /workspaces/${localWorkspaceFolderBasename}
