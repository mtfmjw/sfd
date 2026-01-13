# SFD Project Documentation

Welcome to the SFD (Simplified Framework for Django) project documentation. This comprehensive guide provides all the information you need to understand, develop, and deploy the SFD application.

## Documentation Structure

### Getting Started

- **[Getting Started](getting-started.md)** - Installation, setup, and first steps for new developers
  - Prerequisites and installation
  - Environment configuration
  - Database setup
  - Running the development server
  - Development workflow

### Core Documentation

- **[Architecture](architecture.md)** - System architecture, design patterns, and data flow
  - Layered architecture overview
  - Design patterns (inheritance, mixins, temporal data)
  - Component architecture
  - Security and performance

- **[Models](models.md)** - Database models, fields, and relationships
  - BaseModel and MasterModel
  - Domain models (Person, Holiday, etc.)
  - Temporal validity management
  - Querying and migrations

- **[Views & Admin](views-admin.md)** - Views, admin interface, and URL routing
  - Custom admin site
  - Admin base classes and mixins
  - Regular views and AJAX endpoints
  - Templates and permissions

- **[Forms](forms.md)** - Form handling, validation, and widgets
  - ModelForm and custom forms
  - Form validation
  - Dynamic forms and formsets
  - AJAX form submission

- **[Common Utilities](common-utilities.md)** - Shared utilities, middleware, and helpers
  - Logging with user context
  - Date/time utilities
  - Font utilities for PDF
  - Email and caching helpers

### Development

- **[Testing](testing.md)** - Testing strategy, tools, and best practices
  - Running tests with pytest
  - Unit, integration, and view tests
  - Test coverage
  - Testing patterns

- **[API Reference](api-reference.md)** - Quick reference for classes, methods, and utilities
  - Models API
  - Admin classes
  - Utility functions
  - Common imports and examples

### Deployment

- **[Deployment](deployment.md)** - Production deployment and configuration
  - Environment setup
  - Web server configuration
  - Database setup
  - Monitoring and backups

## Project Overview

The SFD project is a Django-based web application that provides a comprehensive framework for managing master data with temporal validity periods, user authentication, and multi-language support.

### Key Features

- **Temporal Master Data Management**: Models support validity periods (valid_from/valid_to)
- **Audit Trail**: Automatic tracking of who created/updated records and when
- **Soft Deletion**: Records are never physically deleted, only marked as deleted
- **Optimistic Locking**: Prevents concurrent update conflicts
- **Multi-language Support**: Full internationalization (i18n) with Japanese and English
- **Custom Admin Interface**: Enhanced Django admin with permission controls
- **CSV Import/Export**: Built-in support for bulk data operations
- **PDF Generation**: Support for generating PDF reports
- **Advanced Search**: Postcode and municipality search functionality

### Technology Stack

- **Python**: 3.13+
- **Django**: 5.2.4+
- **Database**: SQLite (development), PostgreSQL/MySQL (production ready)
- **Testing**: pytest with django-pytest
- **Code Quality**: Ruff (linting and formatting)

## Quick Links

- [SFD App README](../sfd/README.md)
- [Project Settings](../sfd_prj/settings.py)
- [Batch Scripts](../batch/README.md)

## Project Structure

```
base/
├── docs/                    # Project documentation (this folder)
├── sfd/                     # Main Django application
│   ├── models/              # Database models
│   ├── views/               # View classes and admin
│   ├── forms/               # Form classes
│   ├── templates/           # HTML templates
│   ├── static/              # Static files (CSS, JS, images)
│   ├── locale/              # Translation files
│   ├── tests/               # Test files
│   ├── common/              # Shared utilities
│   ├── admin.py             # Admin site configuration
│   ├── urls.py              # URL routing
│   └── apps.py              # App configuration
├── sfd_prj/                 # Django project settings
│   ├── settings.py          # Main settings
│   ├── settings_log.py      # Logging configuration
│   ├── urls.py              # Project URL configuration
│   └── wsgi.py              # WSGI application
├── batch/                   # Utility batch scripts
├── logs/                    # Application logs
├── manage.py                # Django management script
├── pyproject.toml           # Python project configuration
└── requirements.txt         # Python dependencies
```

## Getting Help

- Check the relevant documentation section for detailed information
- Review the inline code documentation (docstrings)
- Run tests to see examples of usage: `pytest`
- Check the batch scripts for common operations

## Contributing

When contributing to this project:

1. Follow the existing code style (enforced by Ruff)
2. Add tests for new functionality
3. Update documentation as needed
4. Add docstrings to all classes and functions
5. Use type hints where appropriate
6. Support both Japanese and English translations

## License

[Add your license information here]
