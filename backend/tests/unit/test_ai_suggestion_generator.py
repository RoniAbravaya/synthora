"""
Tests for AI Suggestion Generator Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.services.ai_suggestion_generator import AISuggestionGenerator
from app.schemas.ai_suggestion_data import AISuggestionData


class TestAISuggestionGenerator:
    """Test cases for AISuggestionGenerator."""

    def test_data_sufficiency_check_sufficient(self):
        """Test data sufficiency check with sufficient data."""
        mock_db = Mock()
        
        # Mock post count query
        mock_post_query = Mock()
        mock_post_query.filter.return_value = mock_post_query
        mock_post_query.count.return_value = 5  # 5 posts > MIN_POSTS (3)
        
        # Mock earliest post query
        from datetime import datetime, timedelta
        mock_earliest_post = Mock()
        mock_earliest_post.published_at = datetime.utcnow() - timedelta(days=10)  # 10 days > MIN_DAYS (3)
        
        mock_earliest_query = Mock()
        mock_earliest_query.filter.return_value = mock_earliest_query
        mock_earliest_query.order_by.return_value = mock_earliest_query
        mock_earliest_query.first.return_value = mock_earliest_post
        
        # Mock engagement query
        mock_engagement_query = Mock()
        mock_engagement_query.join.return_value = mock_engagement_query
        mock_engagement_query.filter.return_value = mock_engagement_query
        mock_engagement_query.scalar.return_value = 100  # 100 > MIN_ENGAGEMENT (20)
        
        # Set up query returns based on call order
        mock_db.query.side_effect = [mock_post_query, mock_earliest_query, mock_engagement_query]
        
        generator = AISuggestionGenerator(mock_db, "fake-api-key")
        is_sufficient, stats = generator._check_data_sufficiency(uuid4())
        
        assert is_sufficient is True
        assert stats["post_count"] == 5
        assert stats["days_history"] >= 3
        assert stats["total_engagement"] == 100

    def test_data_sufficiency_check_insufficient_posts(self):
        """Test data sufficiency check with insufficient posts."""
        mock_db = Mock()
        
        # Mock post count query
        mock_post_query = Mock()
        mock_post_query.filter.return_value = mock_post_query
        mock_post_query.count.return_value = 1  # 1 post < MIN_POSTS (3)
        
        # Mock earliest post query - return None since not enough posts
        mock_earliest_query = Mock()
        mock_earliest_query.filter.return_value = mock_earliest_query
        mock_earliest_query.order_by.return_value = mock_earliest_query
        mock_earliest_query.first.return_value = None
        
        # Mock engagement query
        mock_engagement_query = Mock()
        mock_engagement_query.join.return_value = mock_engagement_query
        mock_engagement_query.filter.return_value = mock_engagement_query
        mock_engagement_query.scalar.return_value = 5
        
        mock_db.query.side_effect = [mock_post_query, mock_earliest_query, mock_engagement_query]
        
        generator = AISuggestionGenerator(mock_db, "fake-api-key")
        is_sufficient, stats = generator._check_data_sufficiency(uuid4())
        
        assert is_sufficient is False
        assert stats["post_count"] == 1

    def test_parse_suggestion_response_valid(self):
        """Test parsing a valid OpenAI response."""
        mock_db = Mock()
        generator = AISuggestionGenerator(mock_db, "fake-api-key")
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''
        {
            "title": "Test Video Title",
            "description": "Test description",
            "hook": "Test hook",
            "script_outline": "1. Intro\\n2. Main\\n3. Outro",
            "hashtags": ["test", "video"],
            "estimated_duration_seconds": 60,
            "visual_style": "modern",
            "tone": "friendly",
            "target_audience": "general",
            "recommended_platforms": ["youtube", "tiktok"]
        }
        '''
        
        result = generator._parse_suggestion_response(mock_response)
        
        assert isinstance(result, AISuggestionData)
        assert result.title == "Test Video Title"
        assert result.description == "Test description"
        assert result.hook == "Test hook"
        assert "youtube" in result.recommended_platforms
        assert "tiktok" in result.recommended_platforms

    def test_parse_suggestion_response_invalid_json(self):
        """Test parsing an invalid JSON response returns default."""
        mock_db = Mock()
        generator = AISuggestionGenerator(mock_db, "fake-api-key")
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "invalid json {{"
        
        result = generator._parse_suggestion_response(mock_response)
        
        assert isinstance(result, AISuggestionData)
        assert result.title == "5 Tips You Need to Know"  # Default title


class TestAISuggestionGeneratorPrompts:
    """Test cases for prompt generation."""

    def test_system_prompt_includes_required_fields(self):
        """Test that system prompt includes all required JSON fields."""
        mock_db = Mock()
        generator = AISuggestionGenerator(mock_db, "fake-api-key")
        
        prompt = generator._get_system_prompt()
        
        assert "title" in prompt
        assert "description" in prompt
        assert "hook" in prompt
        assert "script_outline" in prompt
        assert "hashtags" in prompt
        assert "estimated_duration_seconds" in prompt
        assert "visual_style" in prompt
        assert "tone" in prompt
        assert "target_audience" in prompt
        assert "recommended_platforms" in prompt

    def test_analytics_prompt_includes_performance_data(self):
        """Test that analytics prompt includes performance data."""
        mock_db = Mock()
        generator = AISuggestionGenerator(mock_db, "fake-api-key")
        
        performance_data = {
            "total_posts": 10,
            "total_views": 5000,
            "total_likes": 250,
            "total_shares": 50,
            "avg_engagement": 6.0,
            "top_topics": ["coding", "python", "tutorials"],
        }
        
        prompt = generator._build_analytics_prompt(performance_data)
        
        assert "10" in prompt  # total_posts
        assert "5,000" in prompt or "5000" in prompt  # total_views
        assert "coding" in prompt
        assert "python" in prompt

    def test_trends_prompt_is_valid(self):
        """Test that trends prompt is generated correctly."""
        mock_db = Mock()
        generator = AISuggestionGenerator(mock_db, "fake-api-key")
        
        prompt = generator._build_trends_prompt()
        
        assert "trend" in prompt.lower()
        assert "JSON" in prompt
