from sfd.common.logging import set_user_info_per_thread


class RequestMiddleware:
    """
    Django middleware for setting user information per thread for logging purposes.

    This middleware extracts user information from each incoming request and stores
    it in thread-local storage, making it available for logging throughout the
    request processing cycle. This enables automatic inclusion of user context
    in log messages without explicitly passing user information to each logging call.

    The middleware integrates with the custom logging system to provide enhanced
    audit trails and debugging capabilities by associating log entries with
    specific users and requests.

    Attributes:
        get_response (callable): The next middleware or view in the Django request chain.

    Usage:
        Add to Django settings MIDDLEWARE list:
        ```python
        MIDDLEWARE = [
            # ... other middleware ...
            'sfd.common.middleware.RequestMiddleware',
            # ... other middleware ...
        ]
        ```

    Note:
        This middleware should be placed early in the middleware stack to ensure
        user information is available for all subsequent middleware and views.
        The middleware automatically cleans up thread-local data after each request.
    """

    def __init__(self, get_response):
        """
        Initialize the middleware with the next callable in the chain.

        Args:
            get_response (callable): The next middleware or view function to call
                                   in the Django request processing chain.
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Process an incoming request and set user information for logging.

        This method is called for each incoming HTTP request. It extracts user
        information from the request and makes it available in thread-local storage
        for use by the logging system throughout the request lifecycle.

        Args:
            request (HttpRequest): The incoming Django HTTP request object containing
                                 user information, session data, and request metadata.

        Returns:
            HttpResponse: The response from the next middleware or view in the chain.

        Process Flow:
            1. Extract user information from the request
            2. Store user info in thread-local storage for logging
            3. Call the next middleware/view in the chain
            4. Return the response (thread-local cleanup handled automatically)
        """
        set_user_info_per_thread(request)
        response = self.get_response(request)
        return response
