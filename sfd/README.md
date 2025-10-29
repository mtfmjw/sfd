# SFD Core App

Core application for the SFD project containing base models and shared functionality.

## Directory Structure

```
sfd/
├── models/          # Model definitions organized by domain
├── views/           # View classes organized by functionality
├── forms/           # Form classes organized by model/domain
├── tests/           # Test classes organized by type
├── templates/       # HTML templates specific to sfd
├── static/          # Static files (CSS, JS, images)
├── locale/          # Internationalization files for this app
│   ├── ja/         # Japanese translations
│   │   └── LC_MESSAGES/
│   │       └── django.po
│   └── en/         # English translations
│       └── LC_MESSAGES/
│           └── django.po
├── common/          # Common utilities and helpers
├── management/      # Custom Django management commands
│   └── commands/
├── migrations/      # Database migrations
├── admin.py         # Admin interface configuration
├── apps.py          # App configuration
├── db_routers.py    # Database routing configuration
└── urls.py          # URL routing configuration
```

## Core Components

### BaseModel

The `BaseModel` class in `models/base.py` provides common fields for all models:

- `created_at`: Timestamp when record was created
- `updated_at`: Timestamp when record was last updated  
- `created_by`: Username who created the record
- `updated_by`: Username who last updated the record
- `delete_flg`: Soft delete flag

All app models should inherit from `BaseModel` to ensure consistent audit fields.

## Internationalization

This app supports multiple languages with app-specific translation files:

- **Japanese (ja)**: `locale/ja/LC_MESSAGES/django.po`
- **English (en)**: `locale/en/LC_MESSAGES/django.po`

To update translations:

1. Mark strings for translation using `gettext_lazy()` or `_()` in your code
2. Run `python manage.py makemessages -l ja -l en` from the app directory
3. Edit the `.po` files to add translations
4. Run `python manage.py compilemessages` to generate `.mo` files

## Development

When adding new functionality:

1. Create model files in `models/` and import them in `models/__init__.py`
2. Create view files in `views/` and import them in `views/__init__.py`
3. Create form files in `forms/` and import them in `forms/__init__.py`
4. Create test files in `tests/` and import them in `tests/__init__.py`
5. Add URL patterns to `urls.py`
6. Register models in `admin.py` if needed
