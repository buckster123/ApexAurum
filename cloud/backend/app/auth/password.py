"""
Password Hashing
"""

from passlib.context import CryptContext

# Use bcrypt for password hashing
# truncate_error=False allows handling of long passwords gracefully
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # bcrypt has a 72-byte limit - truncate if needed
    password_bytes = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password_bytes)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Apply same truncation for verification
    password_bytes = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.verify(password_bytes, hashed_password)
# Build: 1769286090
