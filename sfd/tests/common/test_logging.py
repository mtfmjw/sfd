# type: ignore
"""
Test cases for the logging module functionality.

This module contains test cases for the logging utilities in sfd.common.logging,
including thread-local user context management and logging filter functionality.
"""

import logging
import threading
import time
from unittest.mock import Mock

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase

from sfd.common.logging import (
    RequestLoggingFilter,
    _thread_local,
    clear_user_info_per_thread,
    set_user_info_per_thread,
)
from sfd.tests.unittest import BaseTestMixin


@pytest.mark.unit
@pytest.mark.common
class SetUserInfoPerThreadTest(BaseTestMixin, TestCase):
    """Test cases for set_user_info_per_thread function."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        # Clear any existing thread-local data
        clear_user_info_per_thread()

    def test_set_user_info_authenticated_user(self):
        """Test setting user info for authenticated user."""
        request = self.factory.get("/", REMOTE_ADDR="192.168.1.100")
        request.user = self.user

        set_user_info_per_thread(request)

        self.assertEqual(_thread_local.username, "testuser")
        self.assertEqual(_thread_local.ip_address, "192.168.1.100")

    def test_set_user_info_anonymous_user(self):
        """Test setting user info for anonymous user."""
        request = self.factory.get("/", REMOTE_ADDR="192.168.1.100")
        request.user = AnonymousUser()

        set_user_info_per_thread(request)

        self.assertIsNone(_thread_local.username)
        self.assertEqual(_thread_local.ip_address, "192.168.1.100")

    def test_set_user_info_with_x_forwarded_for(self):
        """Test IP address extraction from X-Forwarded-For header."""
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="203.0.113.195, 70.41.3.18, 150.172.238.178",
            REMOTE_ADDR="192.168.1.100",
        )
        request.user = self.user

        set_user_info_per_thread(request)

        self.assertEqual(_thread_local.username, "testuser")
        # Should use first IP from X-Forwarded-For
        self.assertEqual(_thread_local.ip_address, "203.0.113.195")

    def test_set_user_info_x_forwarded_for_single_ip(self):
        """Test X-Forwarded-For with single IP address."""
        request = self.factory.get("/", HTTP_X_FORWARDED_FOR="203.0.113.195", REMOTE_ADDR="192.168.1.100")
        request.user = self.user

        set_user_info_per_thread(request)

        self.assertEqual(_thread_local.username, "testuser")
        self.assertEqual(_thread_local.ip_address, "203.0.113.195")

    def test_set_user_info_fallback_to_remote_addr(self):
        """Test fallback to REMOTE_ADDR when X-Forwarded-For is not present."""
        request = self.factory.get("/", REMOTE_ADDR="192.168.1.100")
        request.user = self.user

        set_user_info_per_thread(request)

        self.assertEqual(_thread_local.username, "testuser")
        self.assertEqual(_thread_local.ip_address, "192.168.1.100")

    def test_set_user_info_no_ip_address(self):
        """Test behavior when no IP address information is available."""
        request = self.factory.get("/")
        request.user = self.user
        # Remove all IP-related headers
        if "HTTP_X_FORWARDED_FOR" in request.META:
            del request.META["HTTP_X_FORWARDED_FOR"]
        if "REMOTE_ADDR" in request.META:
            del request.META["REMOTE_ADDR"]

        set_user_info_per_thread(request)

        self.assertEqual(_thread_local.username, "testuser")
        self.assertIsNone(_thread_local.ip_address)

    def test_set_user_info_with_none_values(self):
        """Test behavior with edge case values."""
        request = Mock()
        # Create a mock user with proper is_authenticated property
        mock_user = Mock()
        mock_user.is_authenticated = True
        mock_user.username = "testuser"
        request.user = mock_user
        request.META = {}

        set_user_info_per_thread(request)

        self.assertEqual(_thread_local.username, "testuser")
        self.assertIsNone(_thread_local.ip_address)

    def test_thread_isolation(self):
        """Test that thread-local storage is isolated between threads."""
        results = {}

        def thread_function(thread_id, username, ip_address):
            """Function to run in separate thread."""
            request = self.factory.get("/", REMOTE_ADDR=ip_address)
            request.user = User(username=username, is_active=True)

            set_user_info_per_thread(request)

            # Sleep to ensure timing overlap with other threads
            time.sleep(0.1)

            results[thread_id] = {
                "username": getattr(_thread_local, "username", None),
                "ip_address": getattr(_thread_local, "ip_address", None),
            }

        # Create and start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=thread_function,
                args=(i, f"user{i}", f"192.168.1.{100 + i}"),
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify each thread had its own isolated data
        self.assertEqual(results[0]["username"], "user0")
        self.assertEqual(results[0]["ip_address"], "192.168.1.100")
        self.assertEqual(results[1]["username"], "user1")
        self.assertEqual(results[1]["ip_address"], "192.168.1.101")
        self.assertEqual(results[2]["username"], "user2")
        self.assertEqual(results[2]["ip_address"], "192.168.1.102")

    def test_clear_user_info(self):
        """Test clearing user info from thread-local storage."""
        # First set some user info
        request = self.factory.get("/", REMOTE_ADDR="192.168.1.100")
        request.user = self.user

        set_user_info_per_thread(request)

        # Verify info was set
        self.assertEqual(_thread_local.username, "testuser")
        self.assertEqual(_thread_local.ip_address, "192.168.1.100")

        # Clear the info
        clear_user_info_per_thread()

        # Verify info was cleared
        self.assertIsNone(_thread_local.username)
        self.assertIsNone(_thread_local.ip_address)

    def test_clear_user_info_when_empty(self):
        """Test clearing user info when thread-local storage is already empty."""
        # Ensure thread-local is empty first
        clear_user_info_per_thread()

        # Clearing again should not cause any issues
        clear_user_info_per_thread()

        # Verify still empty
        self.assertIsNone(_thread_local.username)
        self.assertIsNone(_thread_local.ip_address)


@pytest.mark.unit
@pytest.mark.common
class RequestLoggingFilterTest(BaseTestMixin, TestCase):
    """Test cases for RequestLoggingFilter class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.filter = RequestLoggingFilter()
        # Clear any existing thread-local data
        clear_user_info_per_thread()

    def test_filter_with_user_info(self):
        """Test filter adds user info to log record when available."""
        # Set up user info in thread-local storage
        request = self.factory.get("/", REMOTE_ADDR="192.168.1.100")
        request.user = self.user
        set_user_info_per_thread(request)

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Apply the filter
        result = self.filter.filter(record)

        # Verify filter returned True (record should be processed)
        self.assertTrue(result)

        # Verify user info was added to record
        self.assertEqual(record.username, "testuser")
        self.assertEqual(record.ip_address, "192.168.1.100")

    def test_filter_with_anonymous_user(self):
        """Test filter handles anonymous user correctly."""
        # Set up anonymous user info
        request = self.factory.get("/", REMOTE_ADDR="192.168.1.100")
        request.user = AnonymousUser()
        set_user_info_per_thread(request)

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Apply the filter
        result = self.filter.filter(record)

        # Verify filter returned True
        self.assertTrue(result)

        # Verify default values are used for anonymous user (username should be None from thread_local, but filter provides "anonymous" default)
        self.assertEqual(record.username, "anonymous")
        self.assertEqual(record.ip_address, "192.168.1.100")

    def test_filter_with_no_user_info(self):
        """Test filter provides default values when no thread-local data is available."""
        # Ensure no user info is set
        clear_user_info_per_thread()

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Apply the filter
        result = self.filter.filter(record)

        # Verify filter returned True
        self.assertTrue(result)

        # Verify default values are used
        self.assertEqual(record.username, "anonymous")
        self.assertEqual(record.ip_address, "N/A")

    def test_filter_with_no_ip_address(self):
        """Test filter handles missing IP address correctly."""
        # Set up user with no IP address
        _thread_local.username = "testuser"
        _thread_local.ip_address = None

        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=123,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Apply the filter
        result = self.filter.filter(record)

        # Verify filter returned True
        self.assertTrue(result)

        # Verify user info and default IP
        self.assertEqual(record.username, "testuser")
        self.assertEqual(record.ip_address, "N/A")

    def test_filter_preserves_existing_record_attributes(self):
        """Test that filter doesn't interfere with existing log record attributes."""
        # Set up user info
        request = self.factory.get("/", REMOTE_ADDR="192.168.1.100")
        request.user = self.user
        set_user_info_per_thread(request)

        # Create a log record with custom attributes
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="/path/to/test.py",
            lineno=456,
            msg="Warning message with %s",
            args=("parameter",),
            exc_info=None,
        )
        record.custom_attr = "custom_value"

        # Apply the filter
        result = self.filter.filter(record)

        # Verify existing attributes are preserved
        self.assertTrue(result)
        self.assertEqual(record.name, "test.logger")
        self.assertEqual(record.levelno, logging.WARNING)
        self.assertEqual(record.pathname, "/path/to/test.py")
        self.assertEqual(record.lineno, 456)
        self.assertEqual(record.msg, "Warning message with %s")
        self.assertEqual(record.args, ("parameter",))
        self.assertEqual(record.custom_attr, "custom_value")

        # Verify user info was added
        self.assertEqual(record.username, "testuser")
        self.assertEqual(record.ip_address, "192.168.1.100")

    def test_filter_multiple_records(self):
        """Test filter works correctly with multiple log records."""
        # Set up user info
        request = self.factory.get("/", REMOTE_ADDR="192.168.1.100")
        request.user = self.user
        set_user_info_per_thread(request)

        # Process multiple records
        for i in range(5):
            record = logging.LogRecord(
                name=f"test.logger.{i}",
                level=logging.INFO,
                pathname="test.py",
                lineno=100 + i,
                msg=f"Test message {i}",
                args=(),
                exc_info=None,
            )

            result = self.filter.filter(record)

            self.assertTrue(result)
            self.assertEqual(record.username, "testuser")
            self.assertEqual(record.ip_address, "192.168.1.100")
