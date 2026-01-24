"""
Password Hashing - Using Argon2 (more secure than bcrypt, no length limits)
"""

from passlib.context import CryptContext

# Use Argon2 - winner of Password Hashing Competition, no 72-byte limit
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)
