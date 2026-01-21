"""
Synthora Security Utilities

This module provides encryption, hashing, and token utilities for secure
handling of sensitive data like API keys, tokens, and passwords.

Security Features:
- Fernet symmetric encryption for API keys and tokens
- Secure key masking for display
- Token generation utilities
"""

import secrets
import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""
    pass


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data using Fernet.
    
    Fernet guarantees that a message encrypted using it cannot be manipulated
    or read without the key. It uses AES-128-CBC with PKCS7 padding and HMAC
    using SHA256 for authentication.
    
    Usage:
        encryption = EncryptionService()
        
        # Encrypt an API key
        encrypted = encryption.encrypt("sk-my-api-key")
        
        # Decrypt it back
        decrypted = encryption.decrypt(encrypted)
        
        # Mask for display
        masked = encryption.mask_key("sk-my-api-key")  # "sk-...key"
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the encryption service.
        
        Args:
            encryption_key: Optional Fernet key. If not provided, uses ENCRYPTION_KEY from settings.
        """
        if encryption_key is None:
            settings = get_settings()
            encryption_key = settings.ENCRYPTION_KEY
        
        # Ensure the key is properly formatted for Fernet
        try:
            # Try to use the key directly (if it's already a valid Fernet key)
            self._fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except (ValueError, TypeError):
            # If not a valid Fernet key, derive one from the provided key
            # This allows using any string as the encryption key
            key_bytes = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
            # Pad or truncate to 32 bytes, then base64 encode for Fernet
            key_bytes = key_bytes[:32].ljust(32, b'\0')
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            self._fernet = Fernet(fernet_key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64-encoded encrypted string
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not plaintext:
            raise EncryptionError("Cannot encrypt empty string")
        
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {str(e)}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            ciphertext: The encrypted string to decrypt
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            EncryptionError: If decryption fails (wrong key, corrupted data, etc.)
        """
        if not ciphertext:
            raise EncryptionError("Cannot decrypt empty string")
        
        try:
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            raise EncryptionError("Decryption failed: Invalid token (wrong key or corrupted data)")
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {str(e)}")
    
    @staticmethod
    def mask_key(key: str, visible_chars: int = 4) -> str:
        """
        Mask an API key for safe display, showing only the last N characters.
        
        Args:
            key: The API key to mask
            visible_chars: Number of characters to show at the end (default: 4)
            
        Returns:
            Masked key string (e.g., "sk-...xxxx")
            
        Example:
            >>> EncryptionService.mask_key("sk-abc123xyz789")
            "sk-...789"
        """
        if not key:
            return ""
        
        if len(key) <= visible_chars:
            return "*" * len(key)
        
        # Try to preserve prefix (like "sk-" for OpenAI keys)
        prefix = ""
        if "-" in key[:5]:
            prefix_end = key.index("-") + 1
            prefix = key[:prefix_end]
            key_without_prefix = key[prefix_end:]
        else:
            key_without_prefix = key
        
        if len(key_without_prefix) <= visible_chars:
            return prefix + "*" * len(key_without_prefix)
        
        return f"{prefix}...{key_without_prefix[-visible_chars:]}"
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.
        
        Returns:
            A new Fernet-compatible encryption key
            
        Usage:
            new_key = EncryptionService.generate_key()
            # Store this key securely as ENCRYPTION_KEY
        """
        return Fernet.generate_key().decode('utf-8')


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Length of the token in bytes (default: 32)
        
    Returns:
        URL-safe base64-encoded token string
        
    Usage:
        token = generate_secure_token()
        # Use for session tokens, CSRF tokens, etc.
    """
    return secrets.token_urlsafe(length)


def generate_api_key(prefix: str = "syn") -> str:
    """
    Generate an API key with a prefix.
    
    Args:
        prefix: Prefix for the API key (default: "syn" for Synthora)
        
    Returns:
        API key string in format "prefix_randomstring"
        
    Example:
        >>> generate_api_key()
        "syn_a1b2c3d4e5f6g7h8i9j0..."
    """
    random_part = secrets.token_urlsafe(24)
    return f"{prefix}_{random_part}"


def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        True if strings are equal, False otherwise
    """
    return secrets.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get the global encryption service instance.
    
    Returns:
        EncryptionService: Global encryption service
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_value(plaintext: str) -> str:
    """
    Convenience function to encrypt a value using the global encryption service.
    
    Args:
        plaintext: The string to encrypt
        
    Returns:
        Encrypted string
    """
    return get_encryption_service().encrypt(plaintext)


def decrypt_value(ciphertext: str) -> str:
    """
    Convenience function to decrypt a value using the global encryption service.
    
    Args:
        ciphertext: The encrypted string
        
    Returns:
        Decrypted string
    """
    return get_encryption_service().decrypt(ciphertext)


def mask_api_key(key: str) -> str:
    """
    Convenience function to mask an API key.
    
    Args:
        key: The API key to mask
        
    Returns:
        Masked key string
    """
    return EncryptionService.mask_key(key)

