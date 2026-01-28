"""
AI Suggestion Generator Service

Generates intelligent video suggestions using OpenAI API.
Analyzes user analytics when available, falls back to trends otherwise.
"""

import logging
import json
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func
from openai import AsyncOpenAI

from app.models.post import Post
from app.models.analytics import Analytics
from app.models.video import Video
from app.schemas.ai_suggestion_data import AISuggestionData

logger = logging.getLogger(__name__)


class AISuggestionGenerator:
    """
    Service for generating AI-powered video suggestions.
    
    Checks data sufficiency and generates personalized suggestions
    based on analytics or falls back to trend-based suggestions.
    """
    
    # Data sufficiency thresholds
    MIN_POSTS = 3
    MIN_DAYS_HISTORY = 3
    MIN_TOTAL_ENGAGEMENT = 20
    
    def __init__(self, db: Session, openai_api_key: str):
        """
        Initialize the suggestion generator.
        
        Args:
            db: Database session
            openai_api_key: OpenAI API key
        """
        self.db = db
        self.client = AsyncOpenAI(api_key=openai_api_key)
    
    async def generate_suggestion(
        self, user_id: UUID
    ) -> Tuple[AISuggestionData, str, Dict[str, Any]]:
        """
        Generate a complete video suggestion for the user.
        
        1. Check data sufficiency
        2. If sufficient: analyze analytics and generate personalized suggestion
        3. If insufficient: use trends for general suggestion
        4. Return complete suggestion with all video details
        
        Args:
            user_id: User's UUID
            
        Returns:
            Tuple of (suggestion, data_source, data_stats)
            - suggestion: AISuggestionData instance
            - data_source: "analytics" or "trends"
            - data_stats: Dictionary with data statistics
        """
        has_sufficient_data, data_stats = self._check_data_sufficiency(user_id)
        
        if has_sufficient_data:
            suggestion = await self._generate_analytics_based_suggestion(user_id, data_stats)
            return suggestion, "analytics", data_stats
        else:
            suggestion = await self._generate_trend_based_suggestion(user_id)
            return suggestion, "trends", data_stats
    
    def _check_data_sufficiency(self, user_id: UUID) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if user has sufficient data for analytics-based suggestions.
        
        Returns:
            Tuple of (is_sufficient, stats_dict)
        """
        # Count published posts
        post_count = self.db.query(Post).filter(
            Post.user_id == user_id,
            Post.status == "published"
        ).count()
        
        # Get earliest post date
        earliest_post = self.db.query(Post).filter(
            Post.user_id == user_id,
            Post.status == "published"
        ).order_by(Post.published_at.asc()).first()
        
        days_history = 0
        if earliest_post and earliest_post.published_at:
            days_history = (datetime.utcnow() - earliest_post.published_at).days
        
        # Sum total engagement (views + likes + shares)
        total_engagement = self.db.query(
            func.coalesce(func.sum(Analytics.views), 0) +
            func.coalesce(func.sum(Analytics.likes), 0) +
            func.coalesce(func.sum(Analytics.shares), 0)
        ).join(Post, Analytics.post_id == Post.id).filter(
            Post.user_id == user_id
        ).scalar() or 0
        
        stats = {
            "post_count": post_count,
            "days_history": days_history,
            "total_engagement": int(total_engagement),
            "min_posts_required": self.MIN_POSTS,
            "min_days_required": self.MIN_DAYS_HISTORY,
            "min_engagement_required": self.MIN_TOTAL_ENGAGEMENT,
        }
        
        is_sufficient = (
            post_count >= self.MIN_POSTS and
            days_history >= self.MIN_DAYS_HISTORY and
            total_engagement >= self.MIN_TOTAL_ENGAGEMENT
        )
        
        logger.info(f"Data sufficiency check for user {user_id}: {is_sufficient}, stats: {stats}")
        
        return is_sufficient, stats
    
    async def _generate_analytics_based_suggestion(
        self, user_id: UUID, stats: Dict[str, Any]
    ) -> AISuggestionData:
        """Generate suggestion based on user's analytics data."""
        
        # Gather user's performance data
        performance_data = self._gather_performance_data(user_id)
        
        prompt = self._build_analytics_prompt(performance_data)
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        
        suggestion_data = self._parse_suggestion_response(response)
        suggestion_data.based_on_analytics = True
        suggestion_data.source_data = {
            "type": "analytics",
            "stats": stats,
            "performance_summary": {
                "top_topics": performance_data.get("top_topics", []),
                "best_performing_time": performance_data.get("best_time"),
                "avg_engagement": performance_data.get("avg_engagement"),
            }
        }
        
        return suggestion_data
    
    async def _generate_trend_based_suggestion(self, user_id: UUID) -> AISuggestionData:
        """Generate suggestion based on current trends."""
        
        # For now, generate based on general trending topics
        # In production, this would fetch from trending APIs
        prompt = self._build_trends_prompt()
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.9,  # Higher temperature for more creative trend-based ideas
        )
        
        suggestion_data = self._parse_suggestion_response(response)
        suggestion_data.based_on_analytics = False
        suggestion_data.source_data = {
            "type": "trends",
            "reason": "Insufficient analytics data for personalized suggestion",
        }
        
        return suggestion_data
    
    def _get_system_prompt(self) -> str:
        """System prompt for suggestion generation."""
        return """You are an expert content strategist specializing in viral video content for social media platforms like YouTube, TikTok, Instagram, and Facebook.

Your task is to generate a complete, actionable video suggestion that can be immediately used for video production.

You MUST respond with a valid JSON object containing exactly these fields:
{
    "title": "Compelling video title that grabs attention",
    "description": "Detailed description of what the video should cover (2-3 sentences)",
    "hook": "Attention-grabbing opening line or concept for the first 3 seconds",
    "script_outline": "Bullet-point outline of the video script with intro, main points, and call-to-action",
    "hashtags": ["relevant", "hashtags", "for", "discovery"],
    "estimated_duration_seconds": 60,
    "visual_style": "Description of visual style (e.g., 'fast-paced editing, bold text overlays, bright colors')",
    "tone": "Tone of the video (e.g., 'educational yet entertaining, friendly, high energy')",
    "target_audience": "Description of target audience (e.g., 'young professionals interested in productivity')",
    "recommended_platforms": ["tiktok", "instagram", "youtube"],
    "platform_specific_notes": {
        "tiktok": "Keep it under 60 seconds, use trending sounds",
        "instagram": "Optimize thumbnail for Reels, include carousel version",
        "youtube": "Create longer 8-10 minute version with more detail"
    }
}

Make suggestions that are:
- Specific and actionable (not vague)
- Optimized for high engagement and shareability
- Realistic to produce with AI video generation tools
- Aligned with current best practices for each platform
- Designed to encourage viewer retention and interaction"""
    
    def _gather_performance_data(self, user_id: UUID) -> Dict[str, Any]:
        """Gather user's performance data for analysis."""
        
        # Get posts with analytics
        posts_with_analytics = self.db.query(Post, Analytics).join(
            Analytics, Post.id == Analytics.post_id
        ).filter(
            Post.user_id == user_id,
            Post.status == "published"
        ).all()
        
        if not posts_with_analytics:
            return {}
        
        # Calculate performance metrics
        total_views = sum(a.views or 0 for _, a in posts_with_analytics)
        total_likes = sum(a.likes or 0 for _, a in posts_with_analytics)
        total_shares = sum(a.shares or 0 for _, a in posts_with_analytics)
        
        avg_engagement = (total_likes + total_shares) / max(total_views, 1) * 100
        
        # Get post titles/prompts for topic analysis
        topics = []
        for post, _ in posts_with_analytics:
            if post.video and post.video.title:
                topics.append(post.video.title)
            elif post.video and post.video.prompt:
                topics.append(post.video.prompt)
        
        # Get best performing time (simplified)
        best_time = None
        if posts_with_analytics:
            best_post = max(posts_with_analytics, key=lambda x: (x[1].views or 0) + (x[1].likes or 0))
            if best_post[0].published_at:
                best_time = {
                    "day": best_post[0].published_at.strftime("%A"),
                    "hour": best_post[0].published_at.hour
                }
        
        return {
            "total_posts": len(posts_with_analytics),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_shares": total_shares,
            "avg_engagement": round(avg_engagement, 2),
            "top_topics": topics[:5],  # Last 5 topics
            "best_time": best_time,
        }
    
    def _build_analytics_prompt(self, performance_data: Dict[str, Any]) -> str:
        """Build prompt for analytics-based suggestion."""
        
        topics_str = ", ".join(performance_data.get("top_topics", [])[:5])
        
        return f"""Based on the user's content performance data, generate a video suggestion that builds on their successful content patterns.

USER'S PERFORMANCE DATA:
- Total posts analyzed: {performance_data.get('total_posts', 0)}
- Total views: {performance_data.get('total_views', 0):,}
- Total likes: {performance_data.get('total_likes', 0):,}
- Total shares: {performance_data.get('total_shares', 0):,}
- Average engagement rate: {performance_data.get('avg_engagement', 0)}%
- Recent content topics: {topics_str or 'Various topics'}
- Best performing time: {performance_data.get('best_time', 'Not determined')}

Generate a video suggestion that:
1. Builds on topics similar to their successful content
2. Maintains the engagement patterns that worked for them
3. Introduces a fresh angle or trend to keep content interesting
4. Is optimized for maximum engagement based on their audience

Return ONLY the JSON object with the video suggestion."""
    
    def _build_trends_prompt(self) -> str:
        """Build prompt for trend-based suggestion."""
        
        return """Generate a trending video idea that's likely to perform well on social media right now.

Consider current trends like:
- Educational content (how-to, tips, hacks)
- Entertaining short-form content
- Story-driven content
- Behind-the-scenes or authentic content
- Relatable situations and experiences

The user doesn't have enough historical data for personalized suggestions, so focus on:
1. Broadly appealing topics with proven engagement
2. Content formats that work across multiple niches
3. Trending formats like listicles, challenges, or reaction content
4. Easy-to-produce content that can be created with AI tools

Return ONLY the JSON object with the video suggestion."""
    
    def _parse_suggestion_response(self, response) -> AISuggestionData:
        """Parse OpenAI response into AISuggestionData."""
        
        try:
            content = json.loads(response.choices[0].message.content)
            
            return AISuggestionData(
                title=content.get("title", "Untitled Video"),
                description=content.get("description", ""),
                hook=content.get("hook", ""),
                script_outline=content.get("script_outline", ""),
                hashtags=content.get("hashtags", []),
                estimated_duration_seconds=content.get("estimated_duration_seconds", 60),
                visual_style=content.get("visual_style", ""),
                tone=content.get("tone", ""),
                target_audience=content.get("target_audience", ""),
                recommended_platforms=content.get("recommended_platforms", ["youtube", "tiktok", "instagram"]),
                platform_specific_notes=content.get("platform_specific_notes"),
                based_on_analytics=False,  # Will be set by caller
                source_data=None,  # Will be set by caller
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse suggestion response: {e}")
            # Return a default suggestion on parse error
            return AISuggestionData(
                title="5 Tips You Need to Know",
                description="A helpful video sharing valuable tips with your audience.",
                hook="What if I told you there's a better way?",
                script_outline="1. Introduction with hook\n2. Tip 1\n3. Tip 2\n4. Tip 3\n5. Tip 4\n6. Tip 5\n7. Call to action",
                hashtags=["tips", "howto", "viral", "fyp"],
                estimated_duration_seconds=60,
                visual_style="Clean, modern, with text overlays",
                tone="Educational and friendly",
                target_audience="General audience interested in self-improvement",
                recommended_platforms=["tiktok", "instagram", "youtube"],
                platform_specific_notes=None,
                based_on_analytics=False,
                source_data={"error": "Failed to parse AI response"},
            )
