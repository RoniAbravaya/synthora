"""
Trend Analyzer

Monitors and analyzes trending topics to generate relevant suggestions.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import json

from sqlalchemy.orm import Session
import httpx

from app.core.config import get_settings
from app.services.suggestions import SuggestionsService
from app.models.ai_suggestion import SuggestionType

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    Analyzes trending topics and matches them to user's content niche.
    
    Note: This is a basic implementation. For production, you would want
    to integrate with trend APIs like Google Trends, Twitter Trends, etc.
    """
    
    # Predefined trending categories (in production, fetch from APIs)
    TRENDING_CATEGORIES = [
        "technology",
        "entertainment",
        "sports",
        "business",
        "lifestyle",
        "education",
        "gaming",
        "music",
        "food",
        "travel",
    ]
    
    def __init__(self, db: Session):
        """
        Initialize the analyzer.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    async def fetch_trending_topics(
        self,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch current trending topics.
        
        In production, this would integrate with:
        - Google Trends API
        - Twitter/X Trends API
        - TikTok Discover API
        - YouTube Trending
        
        Args:
            category: Optional category filter
            
        Returns:
            List of trending topics
        """
        # For now, use AI to generate "trending" topics
        # In production, replace with actual API calls
        topics = await self._generate_trending_topics_with_ai(category)
        
        return topics
    
    async def _generate_trending_topics_with_ai(
        self,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Use AI to generate plausible trending topics."""
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            return self._get_fallback_trends(category)
        
        try:
            category_context = f" in the {category} category" if category else ""
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a social media trend analyst. Generate realistic trending topics that content creators could make videos about. Return JSON array with objects containing: topic, description, platforms (array of relevant platforms), virality_score (1-10), suggested_angle.",
                            },
                            {
                                "role": "user",
                                "content": f"Generate 5 currently trending topics{category_context} that would work well for short-form video content. Return valid JSON array only.",
                            },
                        ],
                        "temperature": 0.9,
                        "max_tokens": 800,
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Parse JSON
                    try:
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0]
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0]
                        
                        topics = json.loads(content.strip())
                        return topics if isinstance(topics, list) else []
                    except json.JSONDecodeError:
                        return self._get_fallback_trends(category)
                        
        except Exception as e:
            logger.error(f"Failed to fetch trends from AI: {e}")
        
        return self._get_fallback_trends(category)
    
    def _get_fallback_trends(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return fallback trending topics."""
        fallback_trends = [
            {
                "topic": "AI Tools for Creators",
                "description": "New AI tools that help content creators work faster and smarter.",
                "platforms": ["youtube", "tiktok", "instagram"],
                "virality_score": 8,
                "suggested_angle": "Review and tutorial of the latest AI tools",
            },
            {
                "topic": "Productivity Hacks",
                "description": "Quick tips to boost productivity and manage time better.",
                "platforms": ["tiktok", "instagram", "youtube"],
                "virality_score": 7,
                "suggested_angle": "Share your personal productivity routine",
            },
            {
                "topic": "Sustainable Living",
                "description": "Eco-friendly lifestyle tips and sustainable product alternatives.",
                "platforms": ["instagram", "tiktok", "youtube"],
                "virality_score": 7,
                "suggested_angle": "Easy swaps for a more sustainable life",
            },
            {
                "topic": "Side Hustle Ideas",
                "description": "Ways to make extra income with minimal investment.",
                "platforms": ["tiktok", "youtube", "instagram"],
                "virality_score": 9,
                "suggested_angle": "Share a side hustle that actually works",
            },
            {
                "topic": "Mental Health Awareness",
                "description": "Tips for managing stress, anxiety, and maintaining mental wellness.",
                "platforms": ["tiktok", "instagram", "youtube"],
                "virality_score": 8,
                "suggested_angle": "Personal story or coping strategies",
            },
        ]
        
        return fallback_trends
    
    async def match_trends_to_user(
        self,
        user_id: UUID,
        trends: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Match trending topics to user's content history.
        
        Args:
            user_id: User UUID
            trends: List of trending topics
            
        Returns:
            Trends with relevance scores
        """
        from app.models.video import Video
        from app.models.post import Post
        
        # Get user's content history
        videos = self.db.query(Video).filter(Video.user_id == user_id).limit(20).all()
        posts = self.db.query(Post).filter(Post.user_id == user_id).limit(20).all()
        
        # Extract keywords from user's content
        user_keywords = set()
        for video in videos:
            if video.title:
                user_keywords.update(video.title.lower().split())
            if video.prompt:
                user_keywords.update(video.prompt.lower().split()[:20])
        
        for post in posts:
            if post.title:
                user_keywords.update(post.title.lower().split())
            for hashtag in (post.hashtags or []):
                user_keywords.add(hashtag.lower().replace("#", ""))
        
        # Score each trend
        matched_trends = []
        for trend in trends:
            topic_words = set(trend.get("topic", "").lower().split())
            desc_words = set(trend.get("description", "").lower().split())
            
            # Calculate overlap
            topic_overlap = len(topic_words & user_keywords)
            desc_overlap = len(desc_words & user_keywords)
            
            # Calculate relevance (0-1)
            max_possible = max(len(topic_words) + len(desc_words), 1)
            relevance = min(1.0, (topic_overlap * 2 + desc_overlap) / max_possible)
            
            # Boost relevance for high virality trends
            virality = trend.get("virality_score", 5) / 10
            final_relevance = (relevance * 0.6) + (virality * 0.4)
            
            matched_trends.append({
                **trend,
                "relevance_score": round(final_relevance, 2),
            })
        
        # Sort by relevance
        matched_trends.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return matched_trends
    
    async def generate_suggestions(
        self,
        user_id: UUID,
        suggestions_service: SuggestionsService,
    ) -> List[Dict[str, Any]]:
        """
        Generate trend-based suggestions for a user.
        
        Args:
            user_id: User UUID
            suggestions_service: Service to create suggestions
            
        Returns:
            List of created suggestions
        """
        # Fetch trends
        trends = await self.fetch_trending_topics()
        
        # Match to user
        matched_trends = await self.match_trends_to_user(user_id, trends)
        
        # Create suggestions for top relevant trends
        created_suggestions = []
        
        for trend in matched_trends[:3]:  # Top 3 trends
            if trend["relevance_score"] >= 0.3:  # Minimum relevance threshold
                suggestion = suggestions_service.create_trend_alert(
                    user_id=user_id,
                    trend_topic=trend["topic"],
                    trend_description=trend["description"],
                    relevance_score=trend["relevance_score"],
                    suggested_action=trend.get("suggested_angle", "Create content about this topic"),
                )
                created_suggestions.append({
                    "id": str(suggestion.id),
                    "topic": trend["topic"],
                    "relevance": trend["relevance_score"],
                })
        
        return created_suggestions

