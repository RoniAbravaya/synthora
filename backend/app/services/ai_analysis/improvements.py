"""
Improvement Analyzer

Analyzes content and suggests improvements.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_
import httpx

from app.models.video import Video
from app.models.post import Post, PostStatus
from app.models.analytics import Analytics
from app.core.config import get_settings
from app.services.suggestions import SuggestionsService
from app.models.ai_suggestion import SuggestionType

logger = logging.getLogger(__name__)


class ImprovementAnalyzer:
    """
    Analyzes content performance and suggests specific improvements.
    
    Focuses on:
    - Hook effectiveness
    - Title optimization
    - Hashtag suggestions
    - Description improvements
    - Posting time optimization
    """
    
    def __init__(self, db: Session):
        """
        Initialize the analyzer.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    async def analyze_underperforming_content(
        self,
        user_id: UUID,
        threshold_percentile: float = 25,
    ) -> List[Dict[str, Any]]:
        """
        Find and analyze underperforming content.
        
        Args:
            user_id: User UUID
            threshold_percentile: Percentile below which content is "underperforming"
            
        Returns:
            List of underperforming posts with improvement suggestions
        """
        cutoff = datetime.utcnow() - timedelta(days=90)
        
        # Get all published posts
        posts = self.db.query(Post).filter(
            and_(
                Post.user_id == user_id,
                Post.status == "published",
                Post.published_at >= cutoff,
            )
        ).all()
        
        if len(posts) < 5:
            return []
        
        # Calculate engagement for each post
        post_performance = []
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
            
            post_performance.append({
                "post": post,
                "views": total_views,
                "engagement_rate": engagement_rate,
            })
        
        if not post_performance:
            return []
        
        # Sort by engagement rate
        post_performance.sort(key=lambda x: x["engagement_rate"])
        
        # Get threshold
        threshold_idx = int(len(post_performance) * (threshold_percentile / 100))
        threshold_engagement = post_performance[threshold_idx]["engagement_rate"] if threshold_idx < len(post_performance) else 0
        
        # Find underperforming posts
        underperforming = [p for p in post_performance if p["engagement_rate"] <= threshold_engagement]
        
        # Analyze each and suggest improvements
        results = []
        for item in underperforming[:5]:  # Limit to 5
            improvements = await self._analyze_post_for_improvements(item["post"], item)
            if improvements:
                results.append({
                    "post_id": str(item["post"].id),
                    "title": item["post"].title,
                    "current_engagement": round(item["engagement_rate"], 2),
                    "improvements": improvements,
                })
        
        return results
    
    async def _analyze_post_for_improvements(
        self,
        post: Post,
        performance: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Analyze a post and suggest specific improvements."""
        improvements = []
        
        # Check title
        title_issues = self._analyze_title(post.title)
        if title_issues:
            improvements.extend(title_issues)
        
        # Check description
        desc_issues = self._analyze_description(post.description)
        if desc_issues:
            improvements.extend(desc_issues)
        
        # Check hashtags
        hashtag_issues = self._analyze_hashtags(post.hashtags)
        if hashtag_issues:
            improvements.extend(hashtag_issues)
        
        # Use AI for deeper analysis if available
        if settings.OPENAI_API_KEY:
            ai_suggestions = await self._get_ai_improvements(post, performance)
            if ai_suggestions:
                improvements.extend(ai_suggestions)
        
        return improvements
    
    def _analyze_title(self, title: Optional[str]) -> List[Dict[str, Any]]:
        """Analyze title for issues."""
        issues = []
        
        if not title:
            issues.append({
                "category": "title",
                "issue": "Missing title",
                "suggestion": "Add a compelling title to improve discoverability",
                "impact": "high",
            })
            return issues
        
        # Check length
        if len(title) < 20:
            issues.append({
                "category": "title",
                "issue": "Title too short",
                "suggestion": "Expand your title to 40-60 characters for better engagement",
                "impact": "medium",
            })
        elif len(title) > 100:
            issues.append({
                "category": "title",
                "issue": "Title too long",
                "suggestion": "Shorten your title to under 60 characters for better visibility",
                "impact": "medium",
            })
        
        # Check for power words
        power_words = ["how", "why", "best", "top", "secret", "amazing", "ultimate", "easy", "quick", "free"]
        has_power_word = any(word in title.lower() for word in power_words)
        
        if not has_power_word:
            issues.append({
                "category": "title",
                "issue": "Missing hook words",
                "suggestion": "Add engaging words like 'How', 'Why', 'Best', 'Secret' to grab attention",
                "impact": "medium",
            })
        
        # Check for numbers
        has_number = any(char.isdigit() for char in title)
        if not has_number:
            issues.append({
                "category": "title",
                "issue": "No numbers in title",
                "suggestion": "Consider adding numbers (e.g., '5 Tips', '3 Ways') - they increase click-through rate",
                "impact": "low",
            })
        
        return issues
    
    def _analyze_description(self, description: Optional[str]) -> List[Dict[str, Any]]:
        """Analyze description for issues."""
        issues = []
        
        if not description:
            issues.append({
                "category": "description",
                "issue": "Missing description",
                "suggestion": "Add a description to improve SEO and provide context",
                "impact": "high",
            })
            return issues
        
        if len(description) < 50:
            issues.append({
                "category": "description",
                "issue": "Description too short",
                "suggestion": "Expand your description to at least 100 characters",
                "impact": "medium",
            })
        
        # Check for call-to-action
        cta_words = ["follow", "like", "subscribe", "comment", "share", "click", "link", "check out"]
        has_cta = any(word in description.lower() for word in cta_words)
        
        if not has_cta:
            issues.append({
                "category": "description",
                "issue": "No call-to-action",
                "suggestion": "Add a call-to-action like 'Follow for more' or 'Comment below'",
                "impact": "medium",
            })
        
        return issues
    
    def _analyze_hashtags(self, hashtags: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Analyze hashtags for issues."""
        issues = []
        
        if not hashtags or len(hashtags) == 0:
            issues.append({
                "category": "hashtags",
                "issue": "No hashtags",
                "suggestion": "Add 3-5 relevant hashtags to increase discoverability",
                "impact": "high",
            })
            return issues
        
        if len(hashtags) < 3:
            issues.append({
                "category": "hashtags",
                "issue": "Too few hashtags",
                "suggestion": "Use at least 3-5 hashtags for better reach",
                "impact": "medium",
            })
        elif len(hashtags) > 15:
            issues.append({
                "category": "hashtags",
                "issue": "Too many hashtags",
                "suggestion": "Reduce to 5-10 highly relevant hashtags",
                "impact": "low",
            })
        
        # Check for generic vs specific hashtags
        generic_tags = ["fyp", "foryou", "viral", "trending", "explore"]
        generic_count = sum(1 for h in hashtags if h.lower().replace("#", "") in generic_tags)
        
        if generic_count > len(hashtags) / 2:
            issues.append({
                "category": "hashtags",
                "issue": "Too many generic hashtags",
                "suggestion": "Mix generic hashtags with niche-specific ones for better targeting",
                "impact": "medium",
            })
        
        return issues
    
    async def _get_ai_improvements(
        self,
        post: Post,
        performance: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Get AI-powered improvement suggestions."""
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
                                "content": "You are a social media optimization expert. Analyze the content and suggest specific, actionable improvements. Return JSON array with objects containing: category (hook/title/description/hashtags/timing), issue, suggestion, impact (high/medium/low).",
                            },
                            {
                                "role": "user",
                                "content": f"""Analyze this underperforming social media post:
Title: {post.title or 'None'}
Description: {post.description or 'None'}
Hashtags: {', '.join(post.hashtags or [])}
Platforms: {', '.join(post.platforms)}
Engagement Rate: {performance['engagement_rate']:.2f}%

Suggest 2-3 specific improvements. Return valid JSON array only.""",
                            },
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500,
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    try:
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0]
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0]
                        
                        suggestions = json.loads(content.strip())
                        return suggestions if isinstance(suggestions, list) else []
                    except json.JSONDecodeError:
                        return []
                        
        except Exception as e:
            logger.error(f"Failed to get AI improvements: {e}")
        
        return []
    
    async def generate_suggestions(
        self,
        user_id: UUID,
        suggestions_service: SuggestionsService,
    ) -> List[Dict[str, Any]]:
        """
        Generate improvement suggestions for a user.
        
        Args:
            user_id: User UUID
            suggestions_service: Service to create suggestions
            
        Returns:
            List of created suggestions
        """
        underperforming = await self.analyze_underperforming_content(user_id)
        
        created_suggestions = []
        
        for item in underperforming:
            for improvement in item.get("improvements", [])[:2]:  # Max 2 per post
                suggestion = suggestions_service.create_improvement_tip(
                    user_id=user_id,
                    tip_category=improvement.get("category", "general"),
                    tip_title=improvement.get("issue", "Improvement opportunity"),
                    tip_description=improvement.get("suggestion", ""),
                    impact_level=improvement.get("impact", "medium"),
                    related_post_id=UUID(item["post_id"]),
                )
                created_suggestions.append({
                    "id": str(suggestion.id),
                    "category": improvement.get("category"),
                    "post_id": item["post_id"],
                })
        
        return created_suggestions

