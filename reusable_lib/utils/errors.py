"""
Custom Error Classes for AI Applications

A three-tier error hierarchy for robust error handling:
- Retryable: Should be automatically retried (rate limits, server errors)
- UserFixable: User can fix (auth errors, invalid requests)
- Fatal: Cannot continue (unexpected errors)

Usage:
    from reusable_lib.utils import RetryableError, UserFixableError, FatalError

    try:
        call_api()
    except SomeAPIError as e:
        if is_rate_limit(e):
            raise RetryableError("Rate limited", retry_after=60, original_error=e)
        elif is_auth_error(e):
            raise UserFixableError("Invalid API key", help_text="Check your .env file")
        else:
            raise FatalError("Unexpected error", original_error=e)
"""

from typing import Optional


class ApexAurumError(Exception):
    """Base exception for all application errors"""
    pass


class RetryableError(ApexAurumError):
    """
    Error that should be automatically retried with exponential backoff.

    Examples:
    - Rate limit errors
    - Server overload (5xx errors)
    - Temporary network issues

    Attributes:
        retry_after: Seconds to wait before retry (from API headers)
        original_error: The original exception that was caught
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.original_error = original_error


class UserFixableError(ApexAurumError):
    """
    Error that the user can fix by taking action.

    Examples:
    - Invalid API key
    - Insufficient permissions
    - Malformed request
    - Missing required files

    Attributes:
        help_text: Specific guidance on how to fix the issue
        original_error: The original exception that was caught
    """

    def __init__(
        self,
        message: str,
        help_text: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.help_text = help_text
        self.original_error = original_error


class FatalError(ApexAurumError):
    """
    Fatal error that cannot be recovered from.

    Examples:
    - Unexpected exceptions
    - System-level errors
    - Invalid configuration
    - Data corruption

    Attributes:
        original_error: The original exception that was caught
    """

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None
    ):
        super().__init__(message)
        self.original_error = original_error
