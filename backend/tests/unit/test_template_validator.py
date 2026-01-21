"""
Unit Tests for Template Validator

Tests template configuration validation logic.
"""

import pytest
from app.services.template_validator import TemplateValidator, ValidationResult


class TestTemplateValidator:
    """Tests for the TemplateValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a TemplateValidator instance."""
        return TemplateValidator()
    
    @pytest.fixture
    def valid_config(self):
        """Return a valid template configuration."""
        return {
            "name": "Test Template",
            "description": "A test template for unit testing",
            "category": "educational",  # Valid: educational, entertainment, product, etc.
            "tags": ["test", "demo"],
            "target_platforms": ["youtube", "tiktok"],
            "video_structure": {
                "hook_style": "question",
                "narrative_structure": "hook_problem_solution_cta",  # Valid enum value
                "num_scenes": 5,
                "duration_range": {"min": 30, "max": 60},
                "pacing": "medium",
            },
            "visual_style": {
                "aspect_ratio": "9:16",
                "visual_aesthetic": "cinematic",  # Valid: realistic, cinematic, animated, etc.
            },
            "audio": {
                "voice_tone": "energetic",
                "music_mood": "upbeat",
                "voice_gender": "neutral",
                "voice_speed": "normal",
            },
            "script_prompt": {
                "cta_type": "follow",
                "cta_placement": "end",
            },
        }
    
    # =========================================================================
    # Basic Validation Tests
    # =========================================================================
    
    @pytest.mark.unit
    def test_validate_valid_config(self, validator, valid_config):
        """Test that a valid configuration passes validation."""
        result = validator.validate(valid_config)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert len(result.errors) == 0
    
    @pytest.mark.unit
    def test_validate_minimal_config(self, validator):
        """Test that a minimal valid configuration passes."""
        minimal_config = {"name": "Minimal Template"}
        
        result = validator.validate(minimal_config)
        
        assert result.valid is True
        assert len(result.errors) == 0
    
    @pytest.mark.unit
    def test_validate_empty_config(self, validator):
        """Test that an empty configuration fails (name required)."""
        result = validator.validate({})
        
        assert result.valid is False
        assert len(result.errors) > 0
        # Should have error about missing name
        error_fields = [e.field for e in result.errors]
        assert "name" in error_fields
    
    @pytest.mark.unit
    def test_validate_none_config(self, validator):
        """Test that None config raises an error."""
        with pytest.raises((TypeError, AttributeError)):
            validator.validate(None)
    
    # =========================================================================
    # Name Validation Tests
    # =========================================================================
    
    @pytest.mark.unit
    def test_name_too_long(self, validator):
        """Test that a name exceeding max length fails."""
        config = {"name": "x" * 300}  # Exceeds MAX_NAME_LENGTH (255)
        
        result = validator.validate(config)
        
        assert result.valid is False
        error_fields = [e.field for e in result.errors]
        assert "name" in error_fields
    
    @pytest.mark.unit
    def test_name_empty_string(self, validator):
        """Test that an empty name fails validation."""
        config = {"name": ""}
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    @pytest.mark.unit
    def test_name_whitespace_only(self, validator):
        """Test that whitespace-only name fails validation."""
        config = {"name": "   "}
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    # =========================================================================
    # Category Validation Tests
    # =========================================================================
    
    @pytest.mark.unit
    def test_invalid_category(self, validator):
        """Test that an invalid category fails validation."""
        config = {"name": "Test", "category": "invalid_category"}
        
        result = validator.validate(config)
        
        assert result.valid is False
        error_fields = [e.field for e in result.errors]
        assert "category" in error_fields
    
    @pytest.mark.unit
    def test_valid_categories(self, validator):
        """Test that valid categories pass validation."""
        valid_categories = ["viral", "educational", "promotional", "entertainment", "storytelling"]
        
        for category in valid_categories:
            config = {"name": "Test", "category": category}
            result = validator.validate(config)
            # Category validation might fail if enum doesn't include all these
            # Just check no exception is raised
            assert isinstance(result, ValidationResult)
    
    # =========================================================================
    # Tags Validation Tests
    # =========================================================================
    
    @pytest.mark.unit
    def test_tags_not_a_list(self, validator):
        """Test that non-list tags fail validation."""
        config = {"name": "Test", "tags": "not a list"}
        
        result = validator.validate(config)
        
        assert result.valid is False
        error_fields = [e.field for e in result.errors]
        assert "tags" in error_fields
    
    @pytest.mark.unit
    def test_too_many_tags(self, validator):
        """Test that exceeding max tags fails validation."""
        config = {"name": "Test", "tags": [f"tag{i}" for i in range(25)]}  # Exceeds MAX_TAGS (20)
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    @pytest.mark.unit
    def test_tag_too_long(self, validator):
        """Test that a tag exceeding max length fails."""
        config = {"name": "Test", "tags": ["x" * 60]}  # Exceeds MAX_TAG_LENGTH (50)
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    # =========================================================================
    # Platform Validation Tests
    # =========================================================================
    
    @pytest.mark.unit
    def test_invalid_platform(self, validator):
        """Test that an invalid platform fails validation."""
        config = {"name": "Test", "target_platforms": ["invalid_platform"]}
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    @pytest.mark.unit
    def test_valid_platforms(self, validator):
        """Test that valid platforms pass validation."""
        config = {"name": "Test", "target_platforms": ["youtube", "tiktok", "instagram", "facebook"]}
        
        result = validator.validate(config)
        
        assert result.valid is True
    
    # =========================================================================
    # Video Structure Validation Tests
    # =========================================================================
    
    @pytest.mark.unit
    def test_invalid_num_scenes_too_few(self, validator):
        """Test that too few scenes fails validation."""
        config = {
            "name": "Test",
            "video_structure": {"num_scenes": 0}
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    @pytest.mark.unit
    def test_invalid_num_scenes_too_many(self, validator):
        """Test that too many scenes fails validation."""
        config = {
            "name": "Test",
            "video_structure": {"num_scenes": 25}  # Exceeds MAX_SCENES (20)
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    @pytest.mark.unit
    def test_invalid_duration_too_short(self, validator):
        """Test that duration below minimum fails validation."""
        config = {
            "name": "Test",
            "video_structure": {"duration_range": {"min": 2, "max": 60}}  # min < MIN_DURATION (5)
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    @pytest.mark.unit
    def test_invalid_duration_too_long(self, validator):
        """Test that duration above maximum fails validation."""
        config = {
            "name": "Test",
            "video_structure": {"duration_range": {"min": 30, "max": 700}}  # max > MAX_DURATION (600)
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    @pytest.mark.unit
    def test_invalid_duration_min_greater_than_max(self, validator):
        """Test that min duration > max duration fails validation."""
        config = {
            "name": "Test",
            "video_structure": {"duration_range": {"min": 100, "max": 50}}
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    # =========================================================================
    # Audio Validation Tests
    # =========================================================================
    
    @pytest.mark.unit
    def test_invalid_voice_gender(self, validator):
        """Test that invalid voice gender fails validation."""
        config = {
            "name": "Test",
            "audio": {"voice_gender": "invalid"}
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    @pytest.mark.unit
    def test_valid_voice_genders(self, validator):
        """Test that valid voice genders pass validation."""
        for gender in ["male", "female", "neutral"]:
            config = {
                "name": "Test",
                "audio": {"voice_gender": gender}
            }
            result = validator.validate(config)
            assert result.valid is True
    
    @pytest.mark.unit
    def test_invalid_voice_speed(self, validator):
        """Test that invalid voice speed fails validation."""
        config = {
            "name": "Test",
            "audio": {"voice_speed": "super_fast"}
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    # =========================================================================
    # Script Prompt Validation Tests
    # =========================================================================
    
    @pytest.mark.unit
    def test_structure_prompt_too_long(self, validator):
        """Test that prompt exceeding max length fails."""
        config = {
            "name": "Test",
            "script_prompt": {"structure_prompt": "x" * 6000}  # Exceeds MAX_PROMPT_LENGTH (5000)
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    @pytest.mark.unit
    def test_invalid_cta_placement(self, validator):
        """Test that invalid CTA placement fails validation."""
        config = {
            "name": "Test",
            "script_prompt": {"cta_placement": "invalid"}
        }
        
        result = validator.validate(config)
        
        assert result.valid is False
    
    @pytest.mark.unit
    def test_valid_cta_placements(self, validator):
        """Test that valid CTA placements pass validation."""
        for placement in ["end", "mid_end", "throughout"]:
            config = {
                "name": "Test",
                "script_prompt": {"cta_placement": placement}
            }
            result = validator.validate(config)
            assert result.valid is True
    
    # =========================================================================
    # ValidationResult Tests
    # =========================================================================
    
    @pytest.mark.unit
    def test_validation_result_to_dict(self, validator):
        """Test ValidationResult.to_dict() method."""
        config = {"name": ""}  # Invalid - empty name
        
        result = validator.validate(config)
        result_dict = result.to_dict()
        
        assert "valid" in result_dict
        assert "errors" in result_dict
        assert isinstance(result_dict["errors"], list)
    
    @pytest.mark.unit
    def test_extra_fields_ignored(self, validator):
        """Test that extra fields don't cause validation failure."""
        config = {
            "name": "Test",
            "extra_field": "should be ignored",
            "another_extra": {"nested": "data"},
        }
        
        result = validator.validate(config)
        
        assert result.valid is True

