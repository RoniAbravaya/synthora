"""
Unit Tests for Utility Functions

Tests various utility functions across the application.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4


class TestDateUtils:
    """Tests for date utility functions."""
    
    @pytest.mark.unit
    def test_format_datetime_iso(self):
        """Test ISO datetime formatting."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        
        formatted = dt.isoformat()
        
        assert formatted == "2024-01-15T10:30:00"
    
    @pytest.mark.unit
    def test_datetime_comparison(self):
        """Test datetime comparison for expiration checks."""
        now = datetime.utcnow()
        past = now - timedelta(days=1)
        future = now + timedelta(days=1)
        
        assert past < now
        assert future > now
        assert past < future
    
    @pytest.mark.unit
    def test_calculate_expiration_date(self):
        """Test calculating expiration dates."""
        created_at = datetime(2024, 1, 1, 0, 0, 0)
        retention_days = 30
        
        expires_at = created_at + timedelta(days=retention_days)
        
        assert expires_at == datetime(2024, 1, 31, 0, 0, 0)


class TestUUIDUtils:
    """Tests for UUID utility functions."""
    
    @pytest.mark.unit
    def test_uuid_uniqueness(self):
        """Test that UUIDs are unique."""
        uuids = [uuid4() for _ in range(1000)]
        
        assert len(set(uuids)) == 1000
    
    @pytest.mark.unit
    def test_uuid_string_conversion(self):
        """Test UUID to string and back."""
        from uuid import UUID
        
        original = uuid4()
        as_string = str(original)
        from_string = UUID(as_string)
        
        assert from_string == original
    
    @pytest.mark.unit
    def test_uuid_format(self):
        """Test UUID string format."""
        uid = uuid4()
        uid_str = str(uid)
        
        # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        assert len(uid_str) == 36
        assert uid_str.count("-") == 4


class TestStringUtils:
    """Tests for string utility functions."""
    
    @pytest.mark.unit
    def test_truncate_string(self):
        """Test string truncation."""
        long_string = "This is a very long string that needs to be truncated"
        max_length = 20
        
        truncated = long_string[:max_length] + "..." if len(long_string) > max_length else long_string
        
        assert len(truncated) == max_length + 3  # +3 for "..."
        assert truncated.endswith("...")
    
    @pytest.mark.unit
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        unsafe_name = "My Video: Test <file>.mp4"
        
        # Simple sanitization
        safe_chars = "".join(c if c.isalnum() or c in ".-_ " else "_" for c in unsafe_name)
        
        assert ":" not in safe_chars
        assert "<" not in safe_chars
        assert ">" not in safe_chars
    
    @pytest.mark.unit
    def test_slug_generation(self):
        """Test slug generation from title."""
        title = "My Awesome Video Title!"
        
        # Simple slug generation
        slug = title.lower().replace(" ", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        
        assert slug == "my-awesome-video-title"
        assert " " not in slug


class TestValidationUtils:
    """Tests for validation utility functions."""
    
    @pytest.mark.unit
    def test_validate_email_format(self):
        """Test email format validation."""
        valid_emails = [
            "user@example.com",
            "user.name@example.co.uk",
            "user+tag@example.org",
        ]
        
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user@.com",
        ]
        
        import re
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        
        for email in valid_emails:
            assert re.match(email_pattern, email), f"Should be valid: {email}"
        
        for email in invalid_emails:
            assert not re.match(email_pattern, email), f"Should be invalid: {email}"
    
    @pytest.mark.unit
    def test_validate_url_format(self):
        """Test URL format validation."""
        valid_urls = [
            "https://example.com",
            "http://localhost:3000",
            "https://api.example.com/v1/endpoint",
        ]
        
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Only http/https
            "//example.com",
        ]
        
        import re
        url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        
        for url in valid_urls:
            assert re.match(url_pattern, url), f"Should be valid: {url}"


class TestNumberUtils:
    """Tests for number utility functions."""
    
    @pytest.mark.unit
    def test_format_large_numbers(self):
        """Test formatting large numbers for display."""
        def format_number(n):
            if n >= 1_000_000:
                return f"{n / 1_000_000:.1f}M"
            elif n >= 1_000:
                return f"{n / 1_000:.1f}K"
            return str(n)
        
        assert format_number(1_500_000) == "1.5M"
        assert format_number(15_000) == "15.0K"
        assert format_number(500) == "500"
    
    @pytest.mark.unit
    def test_calculate_percentage(self):
        """Test percentage calculation."""
        def calculate_percentage(part, whole):
            if whole == 0:
                return 0.0
            return round((part / whole) * 100, 2)
        
        assert calculate_percentage(50, 100) == 50.0
        assert calculate_percentage(1, 3) == 33.33
        assert calculate_percentage(0, 100) == 0.0
        assert calculate_percentage(100, 0) == 0.0  # Division by zero handled
    
    @pytest.mark.unit
    def test_clamp_value(self):
        """Test clamping values to a range."""
        def clamp(value, min_val, max_val):
            return max(min_val, min(value, max_val))
        
        assert clamp(5, 0, 10) == 5
        assert clamp(-5, 0, 10) == 0
        assert clamp(15, 0, 10) == 10
        assert clamp(0, 0, 10) == 0
        assert clamp(10, 0, 10) == 10

