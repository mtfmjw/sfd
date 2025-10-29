# Testing Documentation

This document describes the testing strategy, tools, and practices for the SFD application.

## Testing Framework

The project uses **pytest** with **pytest-django** for testing Django applications.

### Test Configuration

Configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "sfd_prj.settings"
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--tb=short",
    "--reuse-db",
    "-v"
]
testpaths = ["sfd/tests", "tests"]
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest sfd/tests/test_person.py
```

### Run Specific Test Class

```bash
pytest sfd/tests/test_person.py::TestPersonModel
```

### Run Specific Test Method

```bash
pytest sfd/tests/test_person.py::TestPersonModel::test_create_person
```

### Run with Coverage

```bash
pytest --cov=sfd --cov-report=html
```

View coverage report:
```bash
start htmlcov\index.html
```

### Run Tests Matching Pattern

```bash
pytest -k "person"  # Run tests with 'person' in name
pytest -k "not slow"  # Skip tests marked as slow
```

### Using Batch Scripts

```bash
# Run tests for specific module
batch\pytest_module.bat test_person

# Run selective tests
batch\pytest_selective.bat
```

## Test Structure

### Test Organization

```
sfd/tests/
├── __init__.py
├── unittest.py              # Base test classes and utilities
├── common/                  # Common utility tests
│   ├── test_middleware.py
│   ├── test_logging.py
│   └── test_datetime.py
├── test_person.py           # Person model/view tests
├── test_holiday.py          # Holiday model/view tests
├── test_municipality.py     # Municipality tests
├── test_postcode.py         # Postcode tests
├── test_user.py             # User tests
├── test_group.py            # Group tests
└── test_index.py            # Index view tests
```

## Base Test Classes

### SfdTestCase

Base test class with common utilities. Located in `sfd/tests/unittest.py`.

```python
from django.test import TestCase
from django.contrib.auth.models import User

class SfdTestCase(TestCase):
    """Base test case for SFD tests"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data once for all test methods"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def setUp(self):
        """Set up for each test method"""
        self.client.login(username='testuser', password='testpass123')
```

### Usage Example

```python
from sfd.tests.unittest import SfdTestCase
from sfd.models import Person

class TestPersonModel(SfdTestCase):
    """Test Person model"""
    
    def test_create_person(self):
        """Test creating a person"""
        person = Person.objects.create(
            family_name='Yamada',
            name='Taro',
            created_by=self.user.username
        )
        self.assertEqual(str(person), 'Yamada Taro')
```

## Test Types

### Unit Tests

Test individual functions and methods in isolation.

```python
class TestPersonModel(SfdTestCase):
    """Unit tests for Person model"""
    
    def test_full_name(self):
        """Test full name generation"""
        person = Person(family_name='Yamada', name='Taro')
        self.assertEqual(str(person), 'Yamada Taro')
    
    def test_validation_future_birthday(self):
        """Test birthday cannot be in future"""
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        
        person = Person(
            family_name='Yamada',
            name='Taro',
            birthday=timezone.now().date() + timezone.timedelta(days=1)
        )
        with self.assertRaises(ValidationError):
            person.full_clean()
```

### Integration Tests

Test interactions between multiple components.

```python
class TestPersonCreation(SfdTestCase):
    """Integration tests for person creation"""
    
    def test_create_person_with_address(self):
        """Test creating person with postcode and municipality"""
        postcode = Postcode.objects.create(
            code='123-4567',
            prefecture='Tokyo'
        )
        municipality = Municipality.objects.create(
            name='Shibuya',
            prefecture='Tokyo'
        )
        
        person = Person.objects.create(
            family_name='Yamada',
            name='Taro',
            postcode=postcode,
            municipality=municipality,
            created_by=self.user.username
        )
        
        self.assertEqual(person.postcode.code, '123-4567')
        self.assertEqual(person.municipality.name, 'Shibuya')
```

### View Tests

Test HTTP requests and responses.

```python
from django.urls import reverse

class TestPersonAdmin(SfdTestCase):
    """Test Person admin views"""
    
    def test_person_list_view(self):
        """Test person list view loads"""
        url = reverse('admin:sfd_person_changelist')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Person')
    
    def test_person_create_view(self):
        """Test creating person through admin"""
        url = reverse('admin:sfd_person_add')
        data = {
            'family_name': 'Yamada',
            'name': 'Taro',
            'family_name_kana': 'ヤマダ',
            'name_kana': 'タロウ',
            'valid_from': '2025-01-01',
            'valid_to': '2222-12-31',
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Person.objects.filter(family_name='Yamada').exists())
```

### Form Tests

Test form validation and behavior.

```python
from sfd.forms import PersonForm

class TestPersonForm(SfdTestCase):
    """Test Person form"""
    
    def test_valid_form(self):
        """Test form with valid data"""
        data = {
            'family_name': 'Yamada',
            'name': 'Taro',
            'family_name_kana': 'ヤマダ',
            'name_kana': 'タロウ',
            'email': 'yamada@example.com',
        }
        form = PersonForm(data=data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_email(self):
        """Test form with invalid email"""
        data = {
            'family_name': 'Yamada',
            'name': 'Taro',
            'family_name_kana': 'ヤマダ',
            'name_kana': 'タロウ',
            'email': 'invalid-email',
        }
        form = PersonForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
```

## Testing Best Practices

### 1. Use Fixtures

```python
import pytest
from sfd.models import Person

@pytest.fixture
def sample_person(db):
    """Create a sample person for testing"""
    return Person.objects.create(
        family_name='Yamada',
        name='Taro',
        family_name_kana='ヤマダ',
        name_kana='タロウ'
    )

def test_person_str(sample_person):
    """Test person string representation"""
    assert str(sample_person) == 'Yamada Taro'
```

### 2. Use Factory Pattern

```python
class PersonFactory:
    """Factory for creating test persons"""
    
    @staticmethod
    def create(**kwargs):
        defaults = {
            'family_name': 'Yamada',
            'name': 'Taro',
            'family_name_kana': 'ヤマダ',
            'name_kana': 'タロウ',
        }
        defaults.update(kwargs)
        return Person.objects.create(**defaults)

def test_with_factory():
    person = PersonFactory.create(email='test@example.com')
    assert person.email == 'test@example.com'
```

### 3. Test Edge Cases

```python
class TestPersonValidation(SfdTestCase):
    """Test person validation edge cases"""
    
    def test_empty_name(self):
        """Test that name cannot be empty"""
        person = Person(family_name='')
        with self.assertRaises(ValidationError):
            person.full_clean()
    
    def test_very_long_name(self):
        """Test maximum name length"""
        person = Person(family_name='A' * 101)
        with self.assertRaises(ValidationError):
            person.full_clean()
    
    def test_special_characters_in_name(self):
        """Test special characters in name"""
        person = Person(
            family_name='O\'Brien',
            name='John-Paul',
            family_name_kana='オブライエン',
            name_kana='ジョン'
        )
        person.full_clean()  # Should not raise
        person.save()
```

### 4. Mock External Dependencies

```python
from unittest.mock import patch, Mock

class TestEmailNotification(SfdTestCase):
    """Test email notification"""
    
    @patch('django.core.mail.send_mail')
    def test_send_notification(self, mock_send_mail):
        """Test sending notification email"""
        from sfd.common.email import send_notification_email
        
        send_notification_email(
            'test@example.com',
            'Test Subject',
            'email_template.html',
            {'name': 'Taro'}
        )
        
        mock_send_mail.assert_called_once()
```

### 5. Test Database Transactions

```python
from django.test import TransactionTestCase

class TestPersonTransaction(TransactionTestCase):
    """Test person creation with transactions"""
    
    def test_rollback_on_error(self):
        """Test transaction rollback on error"""
        from django.db import transaction
        
        initial_count = Person.objects.count()
        
        try:
            with transaction.atomic():
                Person.objects.create(
                    family_name='Yamada',
                    name='Taro',
                    family_name_kana='ヤマダ',
                    name_kana='タロウ'
                )
                # Simulate error
                raise Exception('Test error')
        except Exception:
            pass
        
        # Count should be unchanged
        self.assertEqual(Person.objects.count(), initial_count)
```

## Testing MasterModel Behavior

### Temporal Validity Tests

```python
from datetime import date, timedelta

class TestMasterModelValidity(SfdTestCase):
    """Test MasterModel temporal validity"""
    
    def test_overlapping_periods_adjusted(self):
        """Test that overlapping periods are automatically adjusted"""
        # Create initial record
        person1 = Person.objects.create(
            family_name='Yamada',
            name='Taro',
            family_name_kana='ヤマダ',
            name_kana='タロウ',
            valid_from=date(2025, 1, 1),
            valid_to=date(2222, 12, 31)
        )
        
        # Create new record with earlier valid_from
        person2 = Person.objects.create(
            family_name='Yamada',
            name='Taro',
            family_name_kana='ヤマダ',
            name_kana='タロウ',
            valid_from=date(2025, 6, 1),
            valid_to=date(2222, 12, 31)
        )
        
        # Reload first record
        person1.refresh_from_db()
        
        # First record's valid_to should be adjusted
        self.assertEqual(person1.valid_to, date(2025, 5, 31))
    
    def test_no_gap_in_validity(self):
        """Test that there's no gap between validity periods"""
        person1 = Person.objects.create(
            family_name='Yamada',
            name='Taro',
            family_name_kana='ヤマダ',
            name_kana='タロウ',
            valid_from=date(2025, 1, 1),
            valid_to=date(2222, 12, 31)
        )
        
        person2 = Person.objects.create(
            family_name='Yamada',
            name='Taro',
            family_name_kana='ヤマダ',
            name_kana='タロウ',
            valid_from=date(2025, 6, 1),
            valid_to=date(2222, 12, 31)
        )
        
        person1.refresh_from_db()
        
        # Next day after person1 ends should be person2 starts
        self.assertEqual(
            person1.valid_to + timedelta(days=1),
            person2.valid_from
        )
```

## Performance Testing

### Database Query Optimization

```python
from django.test.utils import override_settings
from django.test import TestCase
import time

class TestPersonQueryPerformance(TestCase):
    """Test query performance"""
    
    @classmethod
    def setUpTestData(cls):
        """Create test data"""
        # Create 100 persons
        Person.objects.bulk_create([
            Person(
                family_name=f'Family{i}',
                name=f'Name{i}',
                family_name_kana=f'ファミリー{i}',
                name_kana=f'ネーム{i}'
            )
            for i in range(100)
        ])
    
    def test_query_count(self):
        """Test number of queries"""
        with self.assertNumQueries(1):
            list(Person.objects.all())
    
    def test_select_related_performance(self):
        """Test select_related performance"""
        # Without select_related
        start = time.time()
        persons = Person.objects.all()
        for person in persons[:10]:
            _ = person.postcode  # N+1 queries
        time_without = time.time() - start
        
        # With select_related
        start = time.time()
        persons = Person.objects.select_related('postcode')
        for person in persons[:10]:
            _ = person.postcode  # Single query
        time_with = time.time() - start
        
        # With select_related should be faster
        self.assertLess(time_with, time_without)
```

## Test Coverage

### Measuring Coverage

```bash
pytest --cov=sfd --cov-report=html --cov-report=term
```

### Coverage Goals

- **Overall**: > 80%
- **Models**: > 90%
- **Views**: > 75%
- **Utilities**: > 90%

### Viewing Coverage Report

```bash
# Open in browser
start htmlcov\index.html
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.13
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest --cov=sfd --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Common Testing Patterns

### Testing Soft Delete

```python
def test_soft_delete(self):
    """Test that records are soft deleted, not hard deleted"""
    person = PersonFactory.create()
    person_id = person.id
    
    # Soft delete
    person.deleted_flg = True
    person.save()
    
    # Record still exists in database
    self.assertTrue(
        Person.objects.filter(id=person_id).exists()
    )
    
    # But not in default queryset
    self.assertFalse(
        Person.objects.filter(id=person_id, deleted_flg=False).exists()
    )
```

### Testing Audit Trail

```python
def test_audit_trail(self):
    """Test that audit fields are set correctly"""
    person = Person.objects.create(
        family_name='Yamada',
        name='Taro',
        family_name_kana='ヤマダ',
        name_kana='タロウ',
        created_by='testuser'
    )
    
    # Check created fields
    self.assertEqual(person.created_by, 'testuser')
    self.assertIsNotNone(person.created_at)
    
    # Update
    person.email = 'new@example.com'
    person.updated_by = 'admin'
    person.save()
    
    # Check updated fields
    self.assertEqual(person.updated_by, 'admin')
    self.assertIsNotNone(person.updated_at)
    self.assertGreater(person.updated_at, person.created_at)
```

### Testing AJAX Views

```python
def test_ajax_search(self):
    """Test AJAX postcode search"""
    PersonFactory.create(family_name='Yamada')
    
    response = self.client.get(
        reverse('sfd:search_postcode'),
        {'postcode': '123-4567'},
        HTTP_X_REQUESTED_WITH='XMLHttpRequest'
    )
    
    self.assertEqual(response.status_code, 200)
    data = response.json()
    self.assertIn('results', data)
```

## Debugging Tests

### Print Debugging

```python
def test_with_debugging(self):
    """Test with print statements"""
    person = PersonFactory.create()
    print(f"Created person: {person}")
    print(f"ID: {person.id}")
    
    # Run with: pytest -s
```

### Using PDB

```python
def test_with_pdb(self):
    """Test with debugger"""
    import pdb
    
    person = PersonFactory.create()
    pdb.set_trace()  # Debugger stops here
    
    # Run with: pytest -s
```

### Using pytest flags

```bash
# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l

# Verbose output
pytest -vv
```

## Best Practices Summary

1. **Write tests first** (TDD when appropriate)
2. **Test one thing per test** method
3. **Use descriptive test names** that explain what is being tested
4. **Keep tests independent** - no test should depend on another
5. **Use fixtures and factories** for test data
6. **Mock external dependencies** (email, APIs, etc.)
7. **Test edge cases** and error conditions
8. **Aim for high coverage** but focus on important code
9. **Run tests frequently** during development
10. **Keep tests fast** - slow tests won't be run
