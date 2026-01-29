# SFD Project Copilot Instructions

## Big Picture Architecture
- **Core Framework**: `sfd` (Simplified Framework for Django) provides base models, utilities, and admin patterns.
- **Layered Design**:
  - **Presentation**: Django Admin (heavily customized via mixins), Templates.
  - **Application**: Views, Forms, URL Routing.
  - **Business Logic**: Models (`sfd/models/`), Services, Utilities.
  - **Data Access**: Django ORM.
- **Base Models** (`sfd/models/base.py`):
  - **`BaseModel`**: All models MUST inherit this. Provides `created_by`, `updated_by`, `created_at`, `updated_at`, `deleted_flg` (soft delete).
  - **`MasterModel`**: For temporal data. Adds `valid_from`, `valid_to`. Handles automatic effective period adjustment on save.
- **Admin System**: Uses a composition pattern over inheritance.
  - Key Mixins: `UploadMixin` (CSV upload), `DownloadMixin` (CSV download), `SfdModelAdmin`.
  - See `sfd/admin.py` (or admin package) and `docs/views-admin.md`.
- **Context**: User info is guarded in thread-local storage for audit logging (see `RequestMiddleware`).

## Critical Developer Workflows

### 1. Environment & Scripts
- **Linux / Dev Container**: Use scripts in `shell/`.
  - **Test**: `shell/pytest_selective.sh [path]` or `pytest`.
  - **Migrate**: `shell/migrate.sh`.
  - **Messages**: `shell/make_messages.sh` / `shell/compile_messages.sh`.
- **Windows**: Use scripts in `batch/`.
  - **Commit**: `batch/git-commit-multiline.bat` (CRITICAL for multi-line messages on Windows).
  - **Run Server**: `batch/run_server.bat`.

### 2. Development Tasks
- **Server**: `python manage.py runserver 0.0.0.0:8000` (Dev Container).
- **Database**: PostgreSQL is available as service `db` (port 5432) within container, or `localhost` externally.
  - User/Pass: `devuser`/`devpass`, DB: `devdb`.
  - **Note**: Not accessible via browser HTTP, use SQL client.

### 3. Testing
- Framework: `pytest` with `pytest-django`.
- Location: `sfd/tests/` and `tests/`.
- Base Classes: `sfd/tests/unittest.py`.
- Run specific test: `pytest sfd/tests/test_models.py`.

## Project Conventions & Patterns
- **Language**: Docstrings and comments frequently use Japanese.
- **Code Style**:
  - Line Length: **149 characters** (strict).
  - Quotes: Double quotes.
  - Imports: Sorted via `isort`.
- **Directory Structure**:
  - Functional modules (e.g., `models/`, `views/`) are packages, not single files.
  - `sfd_prj/`: Project settings and main configuration.
- **Model Rules**:
  - optimistic locking implementation via `updated_at`.
  - unique constraints must be strictly defined for `MasterModel` logic to work.

## Integration & Dependencies
- **Dependencies**: `requirements.txt` / `pyproject.toml`.
- **Environment**: `.env` file required for local settings (see `docs/getting-started.md`).
- **Data Flow**: CSV Upload -> Validation -> Model Update (with history adjustment if MasterModel).
