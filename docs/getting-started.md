# Getting Started with SFD

This guide will help you set up the SFD project for local development.

## Development Options

You can set up the project using either **Dev Containers** (recommended) or a **Local Windows Environment**.

## Option 1: Dev Container (Recommended)

The project is configured for VS Code Dev Containers, providing a pre-configured environment with Python, PostgreSQL, and tools.

### Prerequisites

- Docker Desktop (or equivalent)
- VS Code
- [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Setup

1. Open the project in VS Code.
2. Click **Reopen in Container** when prompted, or use the Command Palette (`Ctrl+Shift+P`) > `Dev Containers: Reopen in Container`.
3. The container will build and install dependencies automatically.

### Database Access

A PostgreSQL instance runs alongside the app container.

- **Host (Code/Internal):** `db`
- **Host (External/Tools):** `localhost`
- **Port:** `5432`
- **Database:** `devdb`
- **User:** `devuser`
- **Password:** `devpass`

> **Important:** The database uses the PostgreSQL protocol. It is **not** accessible via a web browser at `http://localhost:5432`. Use the pre-installed **SQLTools** extension in VS Code or a client like DBeaver.

---

## Option 2: Local Windows Installation

### Prerequisites

- Python 3.13 or higher
- Git
- Windows OS (batch scripts are Windows-specific)
- Basic knowledge of Django

## Installation

### 1. Clone the Repository

```bash
git clone [repository-url]
cd base
```

### 2. Set Up Virtual Environment

The project includes batch scripts to simplify environment setup.

```bash
# Activate the virtual environment
activate_env.bat
```

Or manually:

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (optional, defaults to SQLite)
# DATABASE_URL=postgresql://user:password@localhost:5432/sfd_db

# Logging
LOG_LEVEL=INFO
```

### 5. Create Database

Use the provided batch script:

```bash
batch\create_database.bat
```

This script will:

- Run migrations to create database tables
- Set up initial schema

### 6. Create Superuser

Create an admin user to access the Django admin interface:

```bash
batch\create_superuser.bat
```

Follow the prompts to set username, email, and password.

### 7. Run the Development Server

```bash
batch\run_server.bat
```

Or manually:

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000/`

Admin interface: `http://localhost:8000/admin/`

## Batch Scripts

The project includes several batch scripts in the `batch/` folder for common tasks:

### Database Operations

- `create_database.bat` - Initialize database with migrations
- `makemigrations.bat` - Create new migration files
- `migrate.bat` - Apply migrations to database

### Development

- `run_server.bat` - Start development server
- `create_app.bat` - Create a new Django app
- `create_superuser.bat` - Create admin user

### Testing

- `pytest_module.bat` - Run tests for a specific module
- `pytest_selective.bat` - Run specific tests

### Internationalization

- `makemessages.bat` - Extract translation strings
- `compilemessages.bat` - Compile translation files

### Utilities

- `inspectdb.bat` - Generate models from existing database
- `clear_migrations.bat` - Remove all migration files (use with caution!)

See [batch/README.md](../batch/README.md) for detailed documentation on batch scripts.

## Project Configuration

### Django Settings

Main settings are in `sfd_prj/settings.py`:

- `INSTALLED_APPS` - Registered Django applications
- `MIDDLEWARE` - Request/response processing pipeline
- `DATABASES` - Database configuration
- `LANGUAGE_CODE` - Default language (Japanese: 'ja', English: 'en')

Logging configuration is separated in `sfd_prj/settings_log.py`.

### App Configuration

The SFD app configuration is in `sfd/apps.py`:

- Registers Japanese font support for PDF generation
- Sets up app-specific initialization

## Development Workflow

### 1. Creating a New Model

```python
# sfd/models/your_model.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from sfd.models.base import BaseModel

class YourModel(BaseModel):
    name = models.CharField(_("Name"), max_length=100)
    
    class Meta:
        verbose_name = _("Your Model")
        verbose_name_plural = _("Your Models")
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                name='unique_yourmodel_name'
            )
        ]
```

### 2. Register in Models **init**.py

```python
# sfd/models/__init__.py
from sfd.models.your_model import YourModel

__all__ = ['YourModel']
```

### 3. Create Admin View

```python
# sfd/views/your_model.py
from sfd.views.base import BaseModelAdmin
from sfd.models import YourModel

class YourModelAdmin(BaseModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name']
```

### 4. Register in Admin

```python
# sfd/admin.py
from sfd.models import YourModel
from sfd.views.your_model import YourModelAdmin

admin_site.register(YourModel, YourModelAdmin)
```

### 5. Create and Apply Migrations

```bash
batch\makemigrations.bat
batch\migrate.bat
```

### 6. Add Translations

```bash
# Extract translatable strings
batch\makemessages.bat

# Edit locale files: sfd/locale/ja/LC_MESSAGES/django.po

# Compile translations
batch\compilemessages.bat
```

## Testing

Run all tests:

```bash
pytest
```

Run specific test file:

```bash
pytest sfd/tests/test_person.py
```

Run with coverage:

```bash
pytest --cov=sfd --cov-report=html
```

View coverage report: `htmlcov/index.html`

## Code Quality

The project uses Ruff for linting and formatting:

```bash
# Check code
ruff check .

# Format code
ruff format .
```

Configuration is in `pyproject.toml`.

## Common Issues

### Migration Conflicts

If you have migration conflicts:

```bash
python manage.py migrate --fake-initial
```

### Translation Not Showing

Make sure to compile messages after editing .po files:

```bash
batch\compilemessages.bat
```

### Static Files Not Loading

Collect static files:

```bash
python manage.py collectstatic
```

## Next Steps

- Read the [Architecture](architecture.md) documentation
- Explore the [Models](models.md) documentation
- Check out [Views & Admin](views-admin.md) documentation
- Review existing code and tests for examples

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django Admin Cookbook](https://books.agiliq.com/projects/django-admin-cookbook/)
- [Pytest Django](https://pytest-django.readthedocs.io/)
