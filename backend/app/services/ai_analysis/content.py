"""
Content Analyzer

Uses AI to analyze content performance and generate recommendations.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import httpx

from app.models.video import Video
from app.models.post import Post, PostStatus
from app.models.analytics import Analytics
from app.models.template import Template
from app.core.config import get_settings
from app.services.suggestions import SuggestionsService
from app.models.ai_suggestion import SuggestionType

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """
    Analyzes content performance and generates AI-powered recommendations.
    
    Uses OpenAI to:
    - Analyze successful content patterns
    - Generate content ideas based on performance
    - Recommend topics and styles
    """
    
    def __init__(self, db: Session):
        """
        Initialize the analyzer.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    async def analyze_top_performing_content(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Analyze top performing content to identify patterns.
        
        Args:
            user_id: User UUID
            limit: Number of top posts to analyze
            
        Returns:
            Analysis results
        """
        # Get top performing posts
        posts = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                Post.status == "published",
            )
        ).all()
        
        if not posts:
            return {"success": False, "reason": "No published posts found"}
        
        # Get analytics and sort by engagement
        post_data = []
        for post in posts:
            analytics = self.db.query(Analytics).filter(
                Analytics.post_id == post.id
            ).all()
            
            if not analytics:
                continue
            
            total_views = sum(a.views for a in analytics)
            total_engagement = sum(a.likes + a.comments + a.shares for a in analytics)
            
            engagement_rate = 0.0
            if total_views > 0:
                engagement_rate = (total_engagement / total_views) * 100
            
            # Get video info
            video = self.db.query(Video).filter(Video.id == post.video_id).first()
            
            post_data.append({
                "post_id": str(post.id),
                "title": post.title,
                "description": post.description,
                "hashtags": post.hashtags,
                "template_id": str(video.template_id) if video and video.template_id else None,
                "views": total_views,
                "engagement": total_engagement,
                "engagement_rate": engagement_rate,
                "platforms": post.platforms,
            })
        
        # Sort by engagement rate
        post_data.sort(key=lambda x: x["engagement_rate"], reverse=True)
        top_posts = post_data[:limit]
        
        # Identify patterns
        patterns = self._identify_patterns(top_posts)
        
        return {
            "success": True,
            "posts_analyzed": len(posts),
            "top_posts": top_posts,
            "patterns": patterns,
        }
    
    def _identify_patterns(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify patterns in successful content."""
        patterns = {
            "common_hashtags": {},
            "title_lengths": [],
            "description_lengths": [],
            "platforms": {},
            "templates_used": {},
        }
        
        for post in posts:
            # Hashtag frequency
            for hashtag in (post.get("hashtags") or []):
                patterns["common_hashtags"][hashtag] = patterns["common_hashtags"].get(hashtag, 0) + 1
            
            # Title/description lengths
            if post.get("title"):
                patterns["title_lengths"].append(len(post["title"]))
            if post.get("description"):
                patterns["description_lengths"].append(len(post["description"]))
            
            # Platform frequency
            for platform in (post.get("platforms") or []):
                patterns["platforms"][platform] = patterns["platforms"].get(platform, 0) + 1
            
            # Template usage
            if post.get("template_id"):
                patterns["templates_used"][post["template_id"]] = patterns["templates_used"].get(post["template_id"], 0) + 1
        
        # Calculate averages
        patterns["avg_title_length"] = (
            sum(patterns["title_lengths"]) / len(patterns["title_lengths"])
            if patterns["title_lengths"] else 0
        )
        patterns["avg_description_length"] = (
            sum(patterns["description_lengths"]) / len(patterns["description_lengths"])
            if patterns["description_lengths"] else 0
        )
        
        # Sort hashtags by frequency
        patterns["top_hashtags"] = sorted(
            patterns["common_hashtags"].items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]
        
        return patterns
    
    async def generate_content_ideas(
        self,
        user_id: UUID,
        count: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate content ideas using AI based on user's performance data.
        
        Args:
            user_id: User UUID
            count: Number of ideas to generate
            
        Returns:
            List of content ideas
        """
        # Get analysis
        analysis = await self.analyze_top_performing_content(user_id)
        
        if not analysis.get("success"):
            return []
        
        # Build context for AI
        context = self._build_ai_context(analysis)
        
        # Generate ideas using OpenAI
        ideas = await self._call_openai_for_ideas(context, count)
        
        return ideas
    
    def _build_ai_context(self, analysis: Dict[str, Any]) -> str:
        """Build context string for AI prompt."""
        patterns = analysis.get("patterns", {})
        top_posts = analysis.get("top_posts", [])
        
        context_parts = [
            "Based on the user's content performance data:",
            "",
        ]
        
        # Top performing content
        if top_posts:
            context_parts.append("Top performing posts:")
            for i, post in enumerate(top_posts[:5], 1):
                context_parts.append(f"{i}. '{post.get('title', 'Untitled')}' - {post['engagement_rate']:.1f}% engagement")
        
        # Patterns
        if patterns.get("top_hashtags"):
            hashtags = [h[0] for h in patterns["top_hashtags"][:5]]
            context_parts.append(f"\nTop hashtags: {', '.join(hashtags)}")
        
        if patterns.get("avg_title_length"):
            context_parts.append(f"Optimal title length: ~{int(patterns['avg_title_length'])} characters")
        
        return "\n".join(context_parts)
    
    async def _call_openai_for_ideas(
        self,
        context: str,
        count: int,
    ) -> List[Dict[str, Any]]:
        """Call OpenAI to generate content ideas."""
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAI API key not configured")
            return self._generate_fallback_ideas(count)
        
        try:
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
                                "content": "You are a social media content strategist. Generate viral video content ideas based on performance data. Return JSON array with objects containing: topic, hook, description, suggested_hashtags (array), estimated_engagement (low/medium/high).",
                            },
                            {
                                "role": "user",
                                "content": f"{context}\n\nGenerate {count} viral video content ideas based on this data. Return valid JSON array only.",
                            },
                        ],
                        "temperature": 0.8,
                        "max_tokens": 1000,
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Parse JSON from response
                    try:
                        # Handle markdown code blocks
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0]
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0]
                        
                        ideas = json.loads(content.strip())
                        return ideas if isinstance(ideas, list) else []
                    except json.JSONDecodeError:
                        logger.error("Failed to parse OpenAI response as JSON")
                        return self._generate_fallback_ideas(count)
                else:
                    logger.error(f"OpenAI API error: {response.status_code}")
                    return self._generate_fallback_ideas(count)
                    
        except Exception as e:
            logger.error(f"Failed to call OpenAI: {e}")
            return self._generate_fallback_ideas(count)
    
    def _generate_fallback_ideas(self, count: int) -> List[Dict[str, Any]]:
        """Generate fallback ideas when AI is unavailable."""
        fallback_ideas = [
            {
                "topic": "Behind the Scenes",
                "hook": "Ever wondered what goes on behind the camera?",
                "description": "Show your audience the process behind your content creation.",
                "suggested_hashtags": ["#BehindTheScenes", "#ContentCreator", "#Process"],
                "estimated_engagement": "high",
            },
            {
                "topic": "Quick Tips",
                "hook": "3 things I wish I knew earlier...",
                "description": "Share valuable quick tips in your niche.",
                "suggested_hashtags": ["#Tips", "#LifeHacks", "#LearnOnTikTok"],
                "estimated_engagement": "medium",
            },
            {
                "topic": "Day in the Life",
                "hook": "A day in my life as a...",
                "description": "Authentic day-in-the-life content performs well across platforms.",
                "suggested_hashtags": ["#DayInTheLife", "#DITL", "#Vlog"],
                "estimated_engagement": "high",
            },
            {
                "topic": "Myth Busting",
                "hook": "This common belief is actually wrong...",
                "description": "Debunk common misconceptions in your field.",
                "suggested_hashtags": ["#MythBusted", "#FactCheck", "#TheMoreYouKnow"],
                "estimated_engagement": "high",
            },
            {
                "topic": "Tutorial/How-To",
                "hook": "Here's exactly how to...",
                "description": "Step-by-step tutorials always perform well.",
                "suggested_hashtags": ["#Tutorial", "#HowTo", "#LearnWithMe"],
                "estimated_engagement": "medium",
            },
        ]
        
        return fallback_ideas[:count]
    
    async def generate_suggestions(
        self,
        user_id: UUID,
        suggestions_service: SuggestionsService,
    ) -> List[Dict[str, Any]]:
        """
        Generate content suggestions for a user.
        
        Args:
            user_id: User UUID
            suggestions_service: Service to create suggestions
            
        Returns:
            List of created suggestions
        """
        ideas = await self.generate_content_ideas(user_id, count=3)
        
        created_suggestions = []
        
        for idea in ideas:
            suggestion = suggestions_service.create_content_suggestion(
                user_id=user_id,
                content_type=idea.get("topic", "General"),
                recommendation=idea.get("hook", ""),
                reasoning=idea.get("description", ""),
                examples=idea.get("suggested_hashtags", []),
            )
            created_suggestions.append({
                "id": str(suggestion.id),
                "topic": idea.get("topic"),
            })
        
        return created_suggestions

