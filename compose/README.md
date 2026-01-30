# Docker/Podman Compose Configuration

This directory contains the compose file for running the development database and tools.

## Services

- **db**: PostgreSQL database (Port 5432)
- **pgadmin**: pgAdmin4 interface (Port 5050)

## Usage

### Using Podman

Windows:
```cmd
..\batch\podman_up.bat
```

Linux:
```bash
../shell/podman_up.sh
```

### Credentials

- **Postgres**: devuser / devpass
- **pgAdmin**: pgadmin@dev.com / devpass
