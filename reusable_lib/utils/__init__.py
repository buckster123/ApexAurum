# Utils - Foundation utilities for AI applications
# Extracted from ApexAurum - Claude Edition

from .errors import (
    ApexAurumError,
    RetryableError,
    UserFixableError,
    FatalError
)

__all__ = [
    'ApexAurumError',
    'RetryableError',
    'UserFixableError',
    'FatalError'
]
