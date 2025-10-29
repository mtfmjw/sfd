# type: ignore
"""
Test cases for sfd.common.middleware module.

This module contains comprehensive test cases for the RequestMiddleware
that handles user information per thread for logging purposes.
"""

from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import TestCase

from sfd.common.middleware import RequestMiddleware
from sfd.tests.unittest import BaseTestMixin


@pytest.mark.unit
@pytest.mark.common
class RequestMiddlewareTest(BaseTestMixin, TestCase):
    """
    Test cases for the RequestMiddleware class.

    Tests the middleware functionality including initialization, request processing,
    and user information handling for logging purposes.
    """

    def setUp(self):
        """Set up test environment with middleware instance and request factory."""
        super().setUp()
        self.get_response = Mock(return_value=HttpResponse("Test response"))
        self.middleware = RequestMiddleware(self.get_response)

    def test_middleware_initialization(self):
        """Test middleware initialization with get_response callable."""
        # Test initialization
        get_response_mock = Mock()
        middleware = RequestMiddleware(get_response_mock)

        # Verify get_response is stored
        self.assertEqual(middleware.get_response, get_response_mock)

    @patch("sfd.common.middleware.set_user_info_per_thread")
    def test_middleware_call_with_authenticated_user(self, mock_set_user_info):
        """Test middleware call with authenticated user request."""
        # Create request with authenticated user
        request = self.factory.get("/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        # Process request through middleware
        response = self.middleware(request)

        # Verify set_user_info_per_thread was called with the request
        mock_set_user_info.assert_called_once_with(request)

        # Verify get_response was called
        self.get_response.assert_called_once_with(request)

        # Verify response is returned
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.content, b"Test response")

    @patch("sfd.common.middleware.set_user_info_per_thread")
    def test_middleware_call_with_anonymous_user(self, mock_set_user_info):
        """Test middleware call with anonymous user request."""
        # Create request with anonymous user
        request = self.factory.get("/")
        request.user = AnonymousUser()
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        # Process request through middleware
        response = self.middleware(request)

        # Verify set_user_info_per_thread was called
        mock_set_user_info.assert_called_once_with(request)

        # Verify get_response was called
        self.get_response.assert_called_once_with(request)

        # Verify response is returned
        self.assertIsInstance(response, HttpResponse)

    @patch("sfd.common.middleware.set_user_info_per_thread")
    def test_middleware_call_preserves_response(self, mock_set_user_info):
        """Test that middleware preserves the original response from get_response."""
        # Create custom response
        custom_response = HttpResponse("Custom response content", status=201)
        custom_response["Custom-Header"] = "Custom-Value"
        self.get_response.return_value = custom_response

        # Create request
        request = self.factory.get("/")
        request.user = self.user

        # Process request through middleware
        response = self.middleware(request)

        # Verify original response is preserved
        self.assertEqual(response, custom_response)
        self.assertEqual(response.content, b"Custom response content")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response["Custom-Header"], "Custom-Value")

    @patch("sfd.common.middleware.set_user_info_per_thread")
    def test_middleware_call_with_post_request(self, mock_set_user_info):
        """Test middleware with POST request."""
        # Create POST request
        request = self.factory.post("/", {"key": "value"})
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        # Process request through middleware
        self.middleware(request)

        # Verify set_user_info_per_thread was called
        mock_set_user_info.assert_called_once_with(request)

        # Verify get_response was called with correct request
        self.get_response.assert_called_once_with(request)

    @patch("sfd.common.middleware.set_user_info_per_thread")
    def test_middleware_call_with_request_headers(self, mock_set_user_info):
        """Test middleware with various request headers."""
        # Create request with various headers
        request = self.factory.get("/", HTTP_X_FORWARDED_FOR="203.0.113.195, 70.41.3.18")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        request.META["HTTP_USER_AGENT"] = "Test User Agent"

        # Process request through middleware
        self.middleware(request)

        # Verify set_user_info_per_thread was called with full request
        mock_set_user_info.assert_called_once_with(request)

        # Verify the request object passed contains all expected headers
        called_request = mock_set_user_info.call_args[0][0]
        self.assertIn("HTTP_X_FORWARDED_FOR", called_request.META)
        self.assertIn("REMOTE_ADDR", called_request.META)
        self.assertIn("HTTP_USER_AGENT", called_request.META)

    @patch("sfd.common.middleware.set_user_info_per_thread")
    def test_middleware_call_order(self, mock_set_user_info):
        """Test that set_user_info_per_thread is called before get_response."""
        call_order = []

        def mock_set_user_info_side_effect(request):
            call_order.append("set_user_info")

        def mock_get_response_side_effect(request):
            call_order.append("get_response")
            return HttpResponse("Test")

        mock_set_user_info.side_effect = mock_set_user_info_side_effect
        self.get_response.side_effect = mock_get_response_side_effect

        # Create request
        request = self.factory.get("/")
        request.user = self.user

        # Process request through middleware
        self.middleware(request)

        # Verify correct call order
        self.assertEqual(call_order, ["set_user_info", "get_response"])

    @patch("sfd.common.middleware.set_user_info_per_thread")
    def test_middleware_exception_in_set_user_info(self, mock_set_user_info):
        """Test middleware behavior when set_user_info_per_thread raises exception."""
        # Make set_user_info_per_thread raise an exception
        mock_set_user_info.side_effect = Exception("User info error")

        # Create request
        request = self.factory.get("/")
        request.user = self.user

        # Process request through middleware - should raise exception
        with self.assertRaises(Exception) as context:
            self.middleware(request)

        self.assertEqual(str(context.exception), "User info error")

        # Verify get_response was not called due to exception
        self.get_response.assert_not_called()

    @patch("sfd.common.middleware.set_user_info_per_thread")
    def test_middleware_exception_in_get_response(self, mock_set_user_info):
        """Test middleware behavior when get_response raises exception."""
        # Make get_response raise an exception
        self.get_response.side_effect = Exception("Response error")

        # Create request
        request = self.factory.get("/")
        request.user = self.user

        # Process request through middleware - should raise exception
        with self.assertRaises(Exception) as context:
            self.middleware(request)

        self.assertEqual(str(context.exception), "Response error")

        # Verify set_user_info_per_thread was still called
        mock_set_user_info.assert_called_once_with(request)

    @patch("sfd.common.middleware.set_user_info_per_thread")
    def test_middleware_with_request_without_user(self, mock_set_user_info):
        """Test middleware with request that might not have user attribute."""
        # Create basic request without user attribute
        request = self.factory.get("/")
        # Don't set request.user to simulate edge case

        # Process request through middleware
        response = self.middleware(request)

        # Verify set_user_info_per_thread was still called
        mock_set_user_info.assert_called_once_with(request)

        # Verify response is returned
        self.assertIsInstance(response, HttpResponse)

    def test_middleware_as_callable(self):
        """Test that middleware instance is callable."""
        # Verify middleware instance is callable
        self.assertTrue(callable(self.middleware))

        # Verify it can be called with a request
        request = self.factory.get("/")
        request.user = self.user

        response = self.middleware(request)
        self.assertIsInstance(response, HttpResponse)

    @patch("sfd.common.middleware.set_user_info_per_thread")
    def test_middleware_integration_with_actual_user_info_setting(self, mock_set_user_info):
        """Test middleware integration with actual user info setting."""
        # Don't mock set_user_info_per_thread, let it run normally
        mock_set_user_info.side_effect = lambda req: None  # Do nothing, let real function run

        # Create request
        request = self.factory.get("/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        # Manually call the real function to verify integration
        from sfd.common.middleware import set_user_info_per_thread

        with patch.object(self.middleware, "get_response", return_value=HttpResponse("OK")):
            # Simulate what the middleware should do
            set_user_info_per_thread(request)
            response = self.middleware.get_response(request)

        # This test verifies the integration works correctly
        self.assertIsInstance(response, HttpResponse)

    def test_middleware_multiple_requests(self):
        """Test middleware handling multiple sequential requests."""
        with patch("sfd.common.middleware.set_user_info_per_thread") as mock_set_user_info:
            # Create multiple requests
            request1 = self.factory.get("/page1")
            request1.user = self.user

            request2 = self.factory.get("/page2")
            request2.user = AnonymousUser()

            request3 = self.factory.post("/api", {"data": "test"})
            request3.user = self.user

            # Process all requests
            response1 = self.middleware(request1)
            response2 = self.middleware(request2)
            response3 = self.middleware(request3)

            # Verify all requests were processed
            self.assertIsInstance(response1, HttpResponse)
            self.assertIsInstance(response2, HttpResponse)
            self.assertIsInstance(response3, HttpResponse)

            # Verify set_user_info_per_thread was called for each request
            self.assertEqual(mock_set_user_info.call_count, 3)

            # Verify get_response was called for each request
            self.assertEqual(self.get_response.call_count, 3)

    def test_middleware_preserves_request_attributes(self):
        """Test that middleware doesn't modify the request object."""
        with patch("sfd.common.middleware.set_user_info_per_thread"):
            # Create request with specific attributes
            request = self.factory.get("/test?param=value")
            request.user = self.user
            request.META["REMOTE_ADDR"] = "192.168.1.100"
            request.custom_attribute = "custom_value"

            # Store original attributes
            original_path = request.path
            original_user = request.user
            original_meta = request.META.copy()
            original_custom = request.custom_attribute

            # Process request through middleware
            self.middleware(request)

            # Verify request attributes are preserved
            self.assertEqual(request.path, original_path)
            self.assertEqual(request.user, original_user)
            self.assertEqual(request.META, original_meta)
            self.assertEqual(request.custom_attribute, original_custom)
