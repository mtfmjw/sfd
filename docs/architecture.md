# SFD Architecture

This document describes the overall architecture and design patterns used in the SFD project.

## Overview

The SFD project follows a layered architecture pattern with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│   (Templates, Admin Interface)          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Application Layer               │
│    (Views, Forms, URL Routing)          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Business Logic Layer            │
│   (Models, Validators, Utilities)       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Data Access Layer               │
│    (ORM, Database Connections)          │
└─────────────────────────────────────────┘
```

## Design Patterns

### 1. Model Inheritance Hierarchy

The project uses abstract base models to provide common functionality:

```
BaseModel (Abstract)
├── Provides: created_at, created_by, updated_at, updated_by, deleted_flg
├── Features: Soft deletion, audit trail, optimistic locking
│
└── MasterModel (Abstract)
    ├── Extends: BaseModel
    ├── Provides: valid_from, valid_to
    └── Features: Temporal validity, automatic period adjustment
        │
        ├── Person
        ├── Holiday
        ├── Postcode
        └── Municipality
```

**Benefits:**

- DRY (Don't Repeat Yourself) principle
- Consistent audit trail across all models
- Centralized business logic for temporal data

### 2. Admin Mixin Pattern

The project uses mixins to compose admin functionality:

```python
ModelAdmin (Django)
    │
    ├── ModelAdminMixin
    │   └── Common admin functionality
    │
    ├── UploadMixin
    │   └── CSV upload capability
    │
    ├── DownloadMixin
    │   └── CSV download capability
    │
    └── SfdModelAdmin
        │
        ├── BaseModelAdmin
        │   ├── BaseModelUploadMixin
        │   ├── BaseModelDownloadMixin
        │   └── BaseModelAdminMixin
        │
        └── MasterModelAdmin
            ├── MasterModelUploadMixin
            ├── MasterModelDownloadMixin
            └── MasterModelAdminMixin
```

**Benefits:**

- Composable functionality
- Easy to add new features
- Consistent behavior across different models

### 3. Thread-Local Storage Pattern

User information is stored in thread-local storage for logging:

```python
Request → RequestMiddleware → set_user_info_per_thread()
                                      ↓
                              Thread-Local Storage
                                      ↓
                              Custom Log Filter
                                      ↓
                              Log with User Context
```

**Benefits:**

- Automatic user context in all logs
- No need to pass user info through function calls
- Clean separation of concerns

### 4. Soft Delete Pattern

Records are never physically deleted:

```python
# Instead of: instance.delete()
instance.deleted_flg = True
instance.save()

# Queries automatically exclude deleted records
Model.objects.filter(deleted_flg=False)
```

**Benefits:**

- Data recovery capability
- Complete audit trail
- Compliance with data retention policies

### 5. Temporal Data Pattern (Bi-Temporal)

Master data uses validity periods:

```python
# Data is valid for a specific time period
valid_from = date(2025, 1, 1)
valid_to = date(2025, 12, 31)

# Automatic period adjustment when overlapping
new_record = Person(valid_from=date(2025, 6, 1))
# Previous record's valid_to automatically adjusted to 2025-05-31
```

**Benefits:**

- Historical data tracking
- Point-in-time queries
- Regulatory compliance

## Component Architecture

### Models Layer

**Responsibilities:**

- Define data structure
- Implement business rules
- Provide data validation
- Manage relationships

**Key Components:**

- `BaseModel`: Audit fields and soft deletion
- `MasterModel`: Temporal validity management
- Domain models: Person, Holiday, Postcode, Municipality

### Views Layer

**Responsibilities:**

- Handle HTTP requests
- Process form data
- Coordinate between models and templates
- Manage user permissions

**Key Components:**

- Admin views with custom mixins
- Search views (postcode, municipality)
- Index/landing pages

### Forms Layer

**Responsibilities:**

- User input validation
- Data cleaning and transformation
- Dynamic form generation
- Custom widget handling

**Key Components:**

- Model forms for CRUD operations
- Search forms
- Upload/download forms

### Common Utilities

**Responsibilities:**

- Shared functionality across app
- Cross-cutting concerns
- Helper functions

**Key Components:**

- `middleware.py`: Request processing
- `logging.py`: Enhanced logging with user context
- `font.py`: Font registration for PDF
- `datetime.py`: Date/time utilities
- `forms.py`: Form helpers

## Data Flow

### Create/Update Flow

```
1. User submits form in Admin Interface
   ↓
2. Django Form Validation
   ↓
3. ModelAdmin.save_model()
   ↓
4. Model.clean() - Business validation
   ↓
5. Model.save() - Automatic adjustments
   ↓
6. Database transaction
   ↓
7. Success/Error message to user
```

### Temporal Data Update Flow

```
1. User updates record with valid_from in future
   ↓
2. Check if valid_from is past date
   ├─ Yes: Create copy with new valid_from (future date)
   │       Adjust previous record's valid_to
   └─ No:  Allow direct update
   ↓
3. Check for overlapping periods
   ↓
4. Automatic adjustment of adjacent records
   ↓
5. Save to database
```

### CSV Import Flow

```
1. User uploads CSV file
   ↓
2. UploadMixin.process_upload()
   ↓
3. Validate CSV structure
   ↓
4. Parse CSV rows
   ↓
5. For each row:
   ├─ Validate data
   ├─ Create/Update model instance
   └─ Handle errors
   ↓
6. Transaction commit/rollback
   ↓
7. Report results to user
```

## Security Architecture

### Authentication & Authorization

- Django's built-in authentication system
- Custom `SfdAdminSite` allows any authenticated user
- Permission checks at view level
- CSRF protection enabled

### Data Protection

- Soft deletion prevents data loss
- Audit trail for all changes
- Optimistic locking prevents concurrent updates
- No sensitive data in logs

### Input Validation

- Form-level validation
- Model-level validation (clean methods)
- Database constraints
- XSS protection via Django templates

## Internationalization (i18n)

### Translation Architecture

```
Source Code
    ↓
gettext_lazy(_("String"))
    ↓
locale/ja/LC_MESSAGES/django.po
locale/en/LC_MESSAGES/django.po
    ↓
compilemessages
    ↓
locale/*/LC_MESSAGES/django.mo
    ↓
Runtime translation based on LANGUAGE_CODE
```

**Supported Languages:**

- Japanese (ja) - Primary
- English (en) - Secondary

## Logging Architecture

### Log Flow

```
Application Code
    ↓
Python Logger
    ↓
RequestMiddleware (adds user context)
    ↓
CustomLogFilter (injects user info)
    ↓
Log Formatter
    ↓
Log Handlers (console, file, rotating file)
    ↓
logs/ directory
```

### Log Levels

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: General informational messages
- **WARNING**: Warning messages for potentially harmful situations
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical messages for severe errors

## Performance Considerations

### Database Optimization

- Proper indexing via model constraints
- Select/prefetch related to minimize queries
- Database connection pooling
- Query optimization with Django ORM

### Caching Strategy

- Template fragment caching
- Database query result caching
- Static file caching with cache busting

### Scalability

- Stateless application design
- Horizontal scaling capability
- Database read replicas support (via db_routers.py)
- CDN for static files in production

## Testing Architecture

### Test Organization

```
tests/
├── common/          # Utility and middleware tests
├── test_person.py   # Person model/view tests
├── test_holiday.py  # Holiday model/view tests
└── unittest.py      # Base test utilities
```

### Test Types

1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test model interactions and database
3. **Admin Tests**: Test admin interface functionality
4. **View Tests**: Test HTTP requests and responses

### Testing Tools

- pytest: Test runner
- pytest-django: Django-specific fixtures
- pytest-cov: Code coverage
- Factory patterns for test data

## Configuration Management

### Settings Organization

```
sfd_prj/
├── settings.py       # Main configuration
└── settings_log.py   # Logging configuration
```

### Environment-Specific Settings

- Development: DEBUG=True, SQLite database
- Production: DEBUG=False, PostgreSQL/MySQL
- Configuration via environment variables (.env file)

## Deployment Architecture

### Production Setup

```
Internet
    ↓
Load Balancer / Reverse Proxy (Nginx)
    ↓
WSGI Server (Gunicorn/uWSGI)
    ↓
Django Application
    ↓
Database (PostgreSQL/MySQL)
```

### Static Files

```
Development: Django serves static files
Production: Nginx/CDN serves static files
           Django only handles dynamic content
```

## Extension Points

The architecture supports easy extension:

1. **New Models**: Inherit from BaseModel or MasterModel
2. **Custom Admin**: Use existing mixins or create new ones
3. **New Views**: Follow existing patterns
4. **Middleware**: Add to MIDDLEWARE list
5. **Custom Commands**: Add to management/commands/
6. **Signal Handlers**: Use Django signals for decoupled logic

## Best Practices

1. **Always inherit from BaseModel or MasterModel**
2. **Use mixins for reusable admin functionality**
3. **Add type hints to improve code clarity**
4. **Write docstrings for all classes and functions**
5. **Use gettext_lazy for all user-facing strings**
6. **Follow the single responsibility principle**
7. **Keep views thin, models fat**
8. **Write tests for new functionality**
9. **Use transactions for data consistency**
10. **Log important operations with appropriate levels**

## Future Enhancements

Potential architectural improvements:

- REST API layer (Django REST Framework)
- Async views for improved performance
- Celery for background tasks
- Redis for caching and session storage
- Elasticsearch for advanced search
- WebSocket support for real-time updates
