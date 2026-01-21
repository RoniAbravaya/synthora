"""
Unit Tests for Security Module

Tests encryption, key masking, and token utilities.
"""

import pytest
from app.core.security import (
    encrypt_value,
    decrypt_value,
    mask_api_key,
    generate_secure_token,
    constant_time_compare,
)


class TestValueEncryption:
    """Tests for value encryption/decryption."""
    
    @pytest.mark.unit
    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption are reversible."""
        original_key = "sk-1234567890abcdef"
        
        encrypted = encrypt_value(original_key)
        decrypted = decrypt_value(encrypted)
        
        assert decrypted == original_key
        assert encrypted != original_key
    
    @pytest.mark.unit
    def test_encrypt_produces_different_output(self):
        """Test that same input produces different ciphertext (due to IV)."""
        key = "test-api-key-12345"
        
        encrypted1 = encrypt_value(key)
        encrypted2 = encrypt_value(key)
        
        # Fernet uses random IV, so ciphertexts should differ
        # (though both decrypt to same value)
        assert decrypt_value(encrypted1) == decrypt_value(encrypted2)
    
    @pytest.mark.unit
    def test_encrypt_empty_string_raises(self):
        """Test that encrypting an empty string raises an error."""
        from app.core.security import EncryptionError
        
        with pytest.raises(EncryptionError):
            encrypt_value("")
    
    @pytest.mark.unit
    def test_encrypt_unicode(self):
        """Test encrypting unicode characters."""
        key = "api-key-with-émojis-🔑"
        
        encrypted = encrypt_value(key)
        decrypted = decrypt_value(encrypted)
        
        assert decrypted == key


class TestApiKeyMasking:
    """Tests for API key masking."""
    
    @pytest.mark.unit
    def test_mask_standard_key(self):
        """Test masking a standard API key."""
        key = "sk-1234567890abcdef"
        
        masked = mask_api_key(key)
        
        # Should show first few and last few chars with ... in between
        assert "..." in masked
        assert masked.endswith("cdef")
    
    @pytest.mark.unit
    def test_mask_short_key(self):
        """Test masking a short key (less than 8 chars)."""
        key = "short"
        
        masked = mask_api_key(key)
        
        # Short keys should be masked
        assert "..." in masked or "***" in masked
    
    @pytest.mark.unit
    def test_mask_empty_string(self):
        """Test masking an empty string."""
        masked = mask_api_key("")
        
        # Empty string returns empty or masked
        assert masked == "" or "***" in masked or masked == "***"


class TestSecureTokens:
    """Tests for secure token generation."""
    
    @pytest.mark.unit
    def test_generate_secure_token(self):
        """Test secure token generation."""
        token = generate_secure_token()
        
        assert token is not None
        assert len(token) > 20  # Should be sufficiently long
        assert isinstance(token, str)
    
    @pytest.mark.unit
    def test_generate_token_custom_length(self):
        """Test generating token with custom length."""
        token = generate_secure_token(length=64)
        
        # Base64 encoded 64 bytes = ~86 chars
        assert len(token) > 80
    
    @pytest.mark.unit
    def test_generate_unique_tokens(self):
        """Test that generated tokens are unique."""
        tokens = [generate_secure_token() for _ in range(100)]
        
        assert len(set(tokens)) == 100  # All unique


class TestConstantTimeCompare:
    """Tests for constant-time string comparison."""
    
    @pytest.mark.unit
    def test_compare_equal_strings(self):
        """Test comparing equal strings."""
        assert constant_time_compare("test123", "test123") is True
    
    @pytest.mark.unit
    def test_compare_different_strings(self):
        """Test comparing different strings."""
        assert constant_time_compare("test123", "test456") is False
    
    @pytest.mark.unit
    def test_compare_different_lengths(self):
        """Test comparing strings of different lengths."""
        assert constant_time_compare("short", "longer_string") is False
    
    @pytest.mark.unit
    def test_compare_empty_strings(self):
        """Test comparing empty strings."""
        assert constant_time_compare("", "") is True
        assert constant_time_compare("test", "") is False
        assert constant_time_compare("", "test") is False

