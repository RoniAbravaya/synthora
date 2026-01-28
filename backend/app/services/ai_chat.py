"""
AI Chat Service

Handles conversational AI interactions for the suggestions page.
Supports refining ideas, creating series, and planning content.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from openai import AsyncOpenAI

from app.models.ai_chat_session import AIChatSession
from app.models.post import Post
from app.models.video import Video
from app.models.template import Template
from app.models.analytics import Analytics
from app.schemas.ai_chat import ChatMessageResponse, ActionCard

logger = logging.getLogger(__name__)


class AIChatService:
    """
    Service for AI chat functionality.
    
    Handles:
    - Processing user messages
    - Generating AI responses with context
    - Detecting intents (refine, create series, create plan)
    - Creating actionable response cards
    """
    
    def __init__(self, db: Session, openai_api_key: str):
        """
        Initialize the chat service.
        
        Args:
            db: Database session
            openai_api_key: OpenAI API key
        """
        self.db = db
        self.client = AsyncOpenAI(api_key=openai_api_key)
    
    async def process_message(
        self,
        session: AIChatSession,
        user_id: UUID,
        message: str,
    ) -> ChatMessageResponse:
        """
        Process a user message and generate AI response.
        
        1. Load session and context
        2. Gather user data (analytics, videos, templates, trends)
        3. Generate response with OpenAI
        4. Parse response and create action cards
        5. Update session with messages
        
        Args:
            session: Chat session
            user_id: User's UUID
            message: User's message
            
        Returns:
            ChatMessageResponse with AI response and action cards
        """
        # Gather context
        context = self._gather_user_context(user_id)
        
        # Build messages for OpenAI
        messages = self._build_chat_messages(session, message, context)
        
        # Call OpenAI
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        # Parse response
        ai_response = self._parse_chat_response(response)
        
        # Update session with new messages
        self._update_session_messages(session, message, ai_response)
        
        return ai_response
    
    def _gather_user_context(self, user_id: UUID) -> Dict[str, Any]:
        """Gather all relevant user context for AI."""
        
        # Get analytics summary
        analytics_summary = self._get_analytics_summary(user_id)
        
        # Get recent videos
        recent_videos = self._get_recent_videos(user_id)
        
        # Get user templates
        templates = self._get_user_templates(user_id)
        
        return {
            "analytics": analytics_summary,
            "recent_videos": recent_videos,
            "templates": templates,
        }
    
    def _get_analytics_summary(self, user_id: UUID) -> Dict[str, Any]:
        """Get analytics summary for context."""
        
        posts = self.db.query(Post).filter(
            Post.user_id == user_id,
            Post.status == "published"
        ).limit(20).all()
        
        if not posts:
            return {"has_data": False, "message": "No published posts yet"}
        
        total_views = 0
        total_likes = 0
        
        for post in posts:
            analytics = self.db.query(Analytics).filter(
                Analytics.post_id == post.id
            ).first()
            if analytics:
                total_views += analytics.views or 0
                total_likes += analytics.likes or 0
        
        return {
            "has_data": True,
            "total_posts": len(posts),
            "total_views": total_views,
            "total_likes": total_likes,
            "avg_views": total_views // max(len(posts), 1),
        }
    
    def _get_recent_videos(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get recent videos for context."""
        
        videos = self.db.query(Video).filter(
            Video.user_id == user_id,
            Video.status == "completed"
        ).order_by(Video.created_at.desc()).limit(5).all()
        
        return [
            {
                "title": v.title,
                "prompt": v.prompt[:100] if v.prompt else None,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in videos
        ]
    
    def _get_user_templates(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get user's templates for context."""
        
        templates = self.db.query(Template).filter(
            Template.user_id == user_id
        ).limit(5).all()
        
        return [
            {
                "name": t.name,
                "category": t.category.value if t.category else None,
            }
            for t in templates
        ]
    
    def _build_chat_messages(
        self,
        session: AIChatSession,
        new_message: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """Build message list for OpenAI API."""
        
        system_prompt = self._get_chat_system_prompt(session.suggestion_context, context)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (limit to last 10 messages)
        for msg in (session.messages or [])[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add new user message
        messages.append({"role": "user", "content": new_message})
        
        return messages
    
    def _get_chat_system_prompt(
        self, 
        suggestion_context: Optional[Dict[str, Any]], 
        user_context: Dict[str, Any]
    ) -> str:
        """Generate system prompt for chat."""
        
        suggestion_str = json.dumps(suggestion_context, indent=2) if suggestion_context else "No suggestion context"
        analytics_str = json.dumps(user_context.get('analytics', {}), indent=2)
        videos_str = json.dumps(user_context.get('recent_videos', []), indent=2)
        
        return f"""You are an AI content strategist assistant helping a user plan their video content.

CURRENT SUGGESTION BEING DISCUSSED:
{suggestion_str}

USER'S ANALYTICS SUMMARY:
{analytics_str}

USER'S RECENT VIDEOS:
{videos_str}

YOUR CAPABILITIES:
1. Refine and improve the current video idea
2. Create video series (Part 1, 2, 3...) - ask clarifying questions first
3. Create monthly content plans - ask about variety vs series, number of videos
4. Schedule videos for specific times
5. Suggest optimal posting times based on analytics

RESPONSE FORMAT:
You MUST respond with a valid JSON object:
{{
    "message": "Your conversational response to the user",
    "action_cards": [
        {{
            "type": "single_video|series|monthly_plan|schedule",
            "title": "Action card title",
            "description": "What this action does",
            "data": {{...action-specific data...}}
        }}
    ],
    "needs_clarification": true/false,
    "clarification_question": "Question if needs_clarification is true"
}}

RULES:
1. When user asks about series or monthly plans, ALWAYS ask clarifying questions first:
   - For series: "How many parts would you like?" "What should each part cover?"
   - For monthly plans: "Would you like variety or a continuous series?" "How many videos?"

2. Include action_cards ONLY when you have enough information:
   - type "single_video": Include full suggestion data for one video
   - type "series": Include array of video suggestions with schedule
   - type "monthly_plan": Include full plan with videos and schedule
   - type "schedule": Include suggestion and proposed schedule time

3. For action card data, include complete suggestion information like:
   - title, description, hook, script_outline
   - hashtags, estimated_duration_seconds
   - visual_style, tone, target_audience
   - recommended_platforms

4. Be conversational but concise. Help the user refine their ideas.

5. If user wants to "generate" or "create" a video, provide a single_video action card.

6. If user wants to schedule, ask for their preferred date/time and platforms."""
    
    def _parse_chat_response(self, response) -> ChatMessageResponse:
        """Parse OpenAI response into ChatMessageResponse."""
        
        try:
            content = json.loads(response.choices[0].message.content)
            
            action_cards = []
            for card_data in content.get("action_cards", []):
                action_cards.append(ActionCard(
                    type=card_data.get("type", "single_video"),
                    title=card_data.get("title", ""),
                    description=card_data.get("description", ""),
                    data=card_data.get("data", {}),
                ))
            
            return ChatMessageResponse(
                message=content.get("message", "I apologize, I couldn't process that request."),
                action_cards=action_cards,
                needs_clarification=content.get("needs_clarification", False),
                clarification_question=content.get("clarification_question"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse chat response: {e}")
            return ChatMessageResponse(
                message="I apologize, but I encountered an error processing your request. Could you please try rephrasing?",
                action_cards=[],
                needs_clarification=False,
                clarification_question=None,
            )
    
    def _update_session_messages(
        self,
        session: AIChatSession,
        user_message: str,
        ai_response: ChatMessageResponse,
    ):
        """Update session with new messages."""
        
        # Add user message
        session.add_message("user", user_message)
        
        # Add assistant message with action cards
        action_cards_data = [card.model_dump() for card in ai_response.action_cards] if ai_response.action_cards else None
        session.add_message("assistant", ai_response.message, action_cards_data)
        
        self.db.commit()
