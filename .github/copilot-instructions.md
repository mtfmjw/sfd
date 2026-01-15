# SFD Project Copilot Instructions

## Big Picture Architecture
- **Core Framework**: `sfd` (Simplified Framework for Django) serves as the core foundation, providing base models, utilities, and patterns. `fx` is a domain-specific application (Foreign Exchange).
- **Layered Design**: Strict separation into Presentation (Templates/Admin), Application (Views/Forms), Business Logic (Models/Services), and Data Access.
- **Base Models**:
  - All models MUST inherit from `BaseModel` (provides `created_at`, `updated_at`, `created_by`, `updated_by`, `delete_flg` for soft deletes).
  - Temporal models MUST inherit from `MasterModel` (adds `valid_from`, `valid_to` for history).
  - See `sfd/models/base.py` for implementation details.
- **Admin System**: Heavily uses Mixin pattern (`UploadMixin`, `DownloadMixin`, `SfdModelAdmin`) for consistent functionality. See `sfd/admin.py` and `docs/views-admin.md`.
- **Context**: User info is stored in thread-local storage for logging/auditing.

## Critical Developer Workflows (Windows)
- **Batch Scripts**: Primary interface for development tasks. Located in `batch/`.
  - **Commits**: MUST use `batch/git-commit-multiline.bat` (or `.ps1`) to handle multi-line messages correctly on Windows.
    - Example: `batch\git-commit-multiline.bat "Title" "Line 1" "Line 2"`
  - **Testing**: Use `batch/pytest_module.bat` or `batch/pytest_selective.bat`.
  - **Server**: Run via `batch/run_server.bat`.
  - **Migrations**: `batch/makemigrations.bat` and `batch/migrate.bat`.

## Critical Developer Workflows (Dev Container / Linux)
- **Shell Scripts**: Located in `shell/`.
  - **Testing**: Use `shell/pytest_selective.sh` or run `pytest` directly.
  - **Migrations**: Use `shell/migrate.sh`.
  - **Superuser**: Use `shell/create_superuser.sh`.
- **Common Tasks**:
  - **Server**: Run `python manage.py runserver 0.0.0.0:8000`.
  - **Commits**: Standard `git commit` commands work correctly in this environment (no need for special scripts).
  - **Migrations**: Run `python manage.py makemigrations` directly.

## Project Conventions & Patterns
- **Directory Structure**: Modules are split into packages (e.g., `models/`, `views/`, `forms/`) rather than monolithic files.
- **Code Style**:
  - **Line Length**: 149 characters (configured in `pyproject.toml`).
  - **Quotes**: Double quotes.
  - **Imports**: Sorted via `isort` (configured in `ruff`).
- **Testing**:
  - Framework: `pytest` + `pytest-django`.
  - Location: `sfd/tests/` and `tests/`.
  - Base classes: Defined in `sfd/tests/unittest.py`.
- **Internationalization**:
  - Locale files in `locale/ja/LC_MESSAGES/django.po`.

## Integration & Dependencies
- **Dependencies**: Managed via `requirements.txt` and `pyproject.toml`.
- **Cross-App**: `fx` likely depends on `sfd` core components. Ensure `sfd` is in the python path or installed in the environment.
