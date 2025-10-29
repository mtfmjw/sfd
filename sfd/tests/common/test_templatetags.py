# type: ignore
"""
Test cases for template tags and filters.

This module contains comprehensive tests for custom template tags and filters
used throughout the SFD application, ensuring proper functionality and
error handling.
"""

import pytest
from django.template import Context, Template
from django.test import TestCase

from sfd.templatetags.common_filters import get_attr


@pytest.mark.unit
@pytest.mark.common
class GetAttrFilterTest(TestCase):
    """Test the get_attr template filter functionality.

    The get_attr filter allows dynamic attribute access in Django templates,
    providing safe attribute retrieval with fallback to None for missing
    or inaccessible attributes.

    Features:
        - Dynamic attribute access by name
        - Safe error handling for missing attributes
        - Type error protection
        - None fallback for failed access

    Test Coverage:
        - Successful attribute access
        - Missing attribute handling
        - Type error handling
        - None and empty value handling
        - Complex object attribute access
    """

    def setUp(self):
        """Set up test fixtures for get_attr filter tests.

        Creates mock objects with various attribute types and structures
        to test different scenarios of attribute access.
        """

        # Create test objects with various attributes using a simple class
        class TestObject:
            def __init__(self):
                self.name = "Test Name"
                self.value = 42
                self.is_active = True
                self.nullable_field = None
                self.empty_string = ""

        self.test_obj = TestObject()

        # Create nested object for complex attribute testing
        class NestedObject:
            def __init__(self):
                self.nested_value = "Nested Content"

        self.nested_obj = NestedObject()
        self.test_obj.nested = self.nested_obj

    def test_get_attr_success_string_attribute(self):
        """Test successful retrieval of string attribute.

        Verifies that the get_attr filter correctly retrieves
        string attributes from objects.
        """
        template = Template("{% load common_filters %}{{ obj|get_attr:'name' }}")
        context = Context({"obj": self.test_obj})
        result = template.render(context)

        self.assertEqual(result, "Test Name")

    def test_get_attr_success_integer_attribute(self):
        """Test successful retrieval of integer attribute.

        Verifies that the get_attr filter correctly retrieves
        numeric attributes from objects.
        """
        template = Template("{% load common_filters %}{{ obj|get_attr:'value' }}")
        context = Context({"obj": self.test_obj})
        result = template.render(context)

        self.assertEqual(result, "42")

    def test_get_attr_success_boolean_attribute(self):
        """Test successful retrieval of boolean attribute.

        Verifies that the get_attr filter correctly retrieves
        boolean attributes from objects.
        """
        template = Template("{% load common_filters %}{{ obj|get_attr:'is_active' }}")
        context = Context({"obj": self.test_obj})
        result = template.render(context)

        self.assertEqual(result, "True")

    def test_get_attr_none_attribute(self):
        """Test retrieval of None attribute value.

        Verifies that the get_attr filter correctly handles
        attributes that have None values.
        """
        template = Template("{% load common_filters %}{{ obj|get_attr:'nullable_field' }}")
        context = Context({"obj": self.test_obj})
        result = template.render(context)

        self.assertEqual(result, "None")

    def test_get_attr_empty_string_attribute(self):
        """Test retrieval of empty string attribute.

        Verifies that the get_attr filter correctly handles
        attributes that have empty string values.
        """
        template = Template("{% load common_filters %}{{ obj|get_attr:'empty_string' }}")
        context = Context({"obj": self.test_obj})
        result = template.render(context)

        self.assertEqual(result, "")

    def test_get_attr_missing_attribute(self):
        """Test handling of missing attribute.

        Verifies that the get_attr filter returns None (renders as empty)
        when attempting to access a non-existent attribute.
        """
        # Test direct function call - should return None
        result = get_attr(self.test_obj, "nonexistent")
        self.assertIsNone(result)

        # Test template rendering - None should render as "None" string
        template = Template("{% load common_filters %}{{ obj|get_attr:'nonexistent' }}")
        context = Context({"obj": self.test_obj})
        template_result = template.render(context)
        self.assertEqual(template_result, "None")

    def test_get_attr_none_object(self):
        """Test handling of None object.

        Verifies that the get_attr filter safely handles None objects
        without raising exceptions.
        """
        # Test direct function call - should return None
        result = get_attr(None, "name")
        self.assertIsNone(result)

        # Test template rendering - None should render as "None" string
        template = Template("{% load common_filters %}{{ obj|get_attr:'name' }}")
        context = Context({"obj": None})
        template_result = template.render(context)
        self.assertEqual(template_result, "None")

    def test_get_attr_invalid_object_type(self):
        """Test handling of invalid object types.

        Verifies that the get_attr filter safely handles objects
        that don't support attribute access (like integers, strings).
        """
        # Test direct function call to verify it returns None
        result = get_attr(123, "name")  # Integer doesn't have 'name' attribute

        # Invalid object type should return None
        self.assertIsNone(result)

    def test_get_attr_with_django_model_object(self):
        """Test get_attr with Django model-like object.

        Verifies that the get_attr filter works correctly with
        Django model instances or similar objects.
        """

        # Create a more realistic Django-like object
        class MockModel:
            def __init__(self):
                self.id = 1
                self.title = "Test Title"
                self.created_at = "2025-07-29"

        model_obj = MockModel()

        template = Template("{% load common_filters %}{{ obj|get_attr:'title' }}")
        context = Context({"obj": model_obj})
        result = template.render(context)

        self.assertEqual(result, "Test Title")

    def test_get_attr_with_method_call(self):
        """Test get_attr with method names (should return method object).

        Verifies that the get_attr filter returns method objects
        when accessing methods, but doesn't call them.
        """

        class MockObject:
            def get_display_name(self):
                return "Display Name"

        obj = MockObject()

        # Test direct function call - should return the method object
        result = get_attr(obj, "get_display_name")
        self.assertIsNotNone(result)
        self.assertTrue(callable(result))
        self.assertEqual(result(), "Display Name")  # Verify it's the correct method

        # Test template rendering - method object should be rendered as string
        template = Template("{% load common_filters %}{{ obj|get_attr:'get_display_name' }}")
        context = Context({"obj": obj})
        template_result = template.render(context)

        # Should not be the actual method result
        self.assertNotEqual(template_result, "Display Name")
        # Should contain some indication it's a method (though exact format may vary)
        self.assertTrue(len(template_result) > 0)

    def test_get_attr_dynamic_attribute_name(self):
        """Test get_attr with dynamic attribute names from context.

        Verifies that the get_attr filter works when the attribute name
        comes from a template variable.
        """
        template = Template("{% load common_filters %}{{ obj|get_attr:attr_name }}")
        context = Context({"obj": self.test_obj, "attr_name": "name"})
        result = template.render(context)

        self.assertEqual(result, "Test Name")

    def test_get_attr_empty_attribute_name(self):
        """Test get_attr with empty attribute name.

        Verifies that the get_attr filter safely handles empty
        or None attribute names.
        """
        # Test direct function call with empty string - should return None
        result = get_attr(self.test_obj, "")
        self.assertIsNone(result)

        # Test template rendering - None should render as "None" string
        template = Template("{% load common_filters %}{{ obj|get_attr:'' }}")
        context = Context({"obj": self.test_obj})
        template_result = template.render(context)
        self.assertEqual(template_result, "None")

    def test_get_attr_none_attribute_name(self):
        """Test get_attr with None attribute name.

        Verifies that the get_attr filter safely handles None
        attribute names without raising exceptions.
        """
        # Test direct function call with None attribute name - should return None
        result = get_attr(self.test_obj, None)
        self.assertIsNone(result)

    def test_get_attr_with_special_characters(self):
        """Test get_attr with attribute names containing special characters.

        Verifies that the get_attr filter handles attribute names
        that might contain underscores or other valid Python identifiers.
        """
        # Add attribute with underscores
        self.test_obj.long_attribute_name = "Special Value"

        template = Template("{% load common_filters %}{{ obj|get_attr:'long_attribute_name' }}")
        context = Context({"obj": self.test_obj})
        result = template.render(context)

        self.assertEqual(result, "Special Value")

    def test_get_attr_in_conditional_template(self):
        """Test get_attr filter within template conditionals.

        Verifies that the get_attr filter works correctly within
        Django template conditional statements.
        """
        template = Template("""
            {% load common_filters %}
            {% if obj|get_attr:'is_active' %}
                Active
            {% else %}
                Inactive
            {% endif %}
        """)
        context = Context({"obj": self.test_obj})
        result = template.render(context).strip()

        self.assertEqual(result, "Active")

    def test_get_attr_in_loop_template(self):
        """Test get_attr filter within template loops.

        Verifies that the get_attr filter works correctly when
        used within Django template for loops.
        """
        # Create multiple objects
        objects = []
        for i in range(3):

            class TestObject:
                def __init__(self, name):
                    self.name = name

            objects.append(TestObject(f"Object {i}"))

        template = Template(
            """{% load common_filters %}{% for item in objects %}{{ item|get_attr:'name' }}{% if not forloop.last %}, {% endif %}{% endfor %}"""
        )
        context = Context({"objects": objects})
        result = template.render(context)

        self.assertEqual(result, "Object 0, Object 1, Object 2")

    def test_get_attr_filter_import(self):
        """Test that the get_attr filter is properly registered.

        Verifies that the filter can be imported and used in templates
        without registration errors.
        """
        # Test direct function call
        result = get_attr(self.test_obj, "name")
        self.assertEqual(result, "Test Name")

        # Test with missing attribute
        result = get_attr(self.test_obj, "nonexistent")
        self.assertIsNone(result)

        # Test with None object
        result = get_attr(None, "name")
        self.assertIsNone(result)

    def test_common_filters_template_loading(self):
        """Test that common_filters can be loaded in templates.

        Verifies that the template tag library loads without errors
        and filters are available for use.
        """
        template = Template("{% load common_filters %}Template loaded successfully")
        context = Context({})
        result = template.render(context)

        self.assertEqual(result, "Template loaded successfully")

    def test_multiple_filter_usage(self):
        """Test using multiple instances of get_attr in same template.

        Verifies that multiple get_attr filter calls work correctly
        within the same template context.
        """

        class TestObject:
            def __init__(self):
                self.title = "Test Title"
                self.description = "Test Description"
                self.status = "active"

        obj = TestObject()

        template = Template("""
            {% load common_filters %}
            Title: {{ obj|get_attr:'title' }}
            Description: {{ obj|get_attr:'description' }}
            Status: {{ obj|get_attr:'status' }}
        """)
        context = Context({"obj": obj})
        result = template.render(context).strip()

        expected = "Title: Test Title\n            Description: Test Description\n            Status: active"
        self.assertEqual(result, expected)

    def test_get_attr_performance_with_many_calls(self):
        """Test performance of get_attr with multiple calls.

        Verifies that the get_attr filter performs adequately
        when used frequently in template rendering.

        Note:
            This is a basic performance test. For production applications,
            consider more sophisticated performance testing tools.
        """
        import time

        class TestObject:
            def __init__(self):
                self.value = "Test Value"

        obj = TestObject()

        template = Template("""{% load common_filters %}{% for i in range %}{{ obj|get_attr:'value' }}{% endfor %}""")

        # Test with moderate number of calls
        context = Context({"obj": obj, "range": range(100)})

        start_time = time.time()
        result = template.render(context)
        end_time = time.time()

        # Verify result correctness
        self.assertEqual(result, "Test Value" * 100)

        # Basic performance check (should complete reasonably quickly)
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1.0, "Filter execution took too long")
