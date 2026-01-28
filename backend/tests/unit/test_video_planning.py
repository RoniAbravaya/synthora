"""
Tests for Video Planning Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.video_planning import VideoPlanningService
from app.models.video import Video, PlanningStatus


class TestVideoPlanningService:
    """Test cases for VideoPlanningService."""

    @pytest.mark.asyncio
    async def test_schedule_video_creates_record(self):
        """Test scheduling a video creates the correct record."""
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        service = VideoPlanningService(mock_db)
        
        user_id = uuid4()
        suggestion_data = {
            "title": "Test Video",
            "description": "Test description",
            "hook": "Test hook",
        }
        scheduled_time = datetime.utcnow() + timedelta(days=1)
        platforms = ["youtube", "tiktok"]
        
        # Capture the video that gets added
        captured_video = None
        def capture_add(video):
            nonlocal captured_video
            captured_video = video
        mock_db.add.side_effect = capture_add
        
        result = await service.schedule_video(
            user_id=user_id,
            suggestion_data=suggestion_data,
            scheduled_post_time=scheduled_time,
            target_platforms=platforms,
        )
        
        assert mock_db.add.called
        assert mock_db.commit.called
        assert captured_video.user_id == user_id
        assert captured_video.planning_status == PlanningStatus.PLANNED.value
        assert captured_video.target_platforms == platforms
        assert captured_video.ai_suggestion_data == suggestion_data

    @pytest.mark.asyncio
    async def test_schedule_video_with_series_info(self):
        """Test scheduling a video with series information."""
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        service = VideoPlanningService(mock_db)
        
        captured_video = None
        def capture_add(video):
            nonlocal captured_video
            captured_video = video
        mock_db.add.side_effect = capture_add
        
        result = await service.schedule_video(
            user_id=uuid4(),
            suggestion_data={"title": "Series Part 1"},
            scheduled_post_time=datetime.utcnow() + timedelta(days=1),
            target_platforms=["youtube"],
            series_name="My Series",
            series_order=1,
        )
        
        assert captured_video.series_name == "My Series"
        assert captured_video.series_order == 1

    @pytest.mark.asyncio
    async def test_create_series_creates_multiple_videos(self):
        """Test creating a series creates multiple video records."""
        mock_db = Mock()
        added_videos = []
        
        def capture_add(video):
            added_videos.append(video)
        mock_db.add.side_effect = capture_add
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        service = VideoPlanningService(mock_db)
        
        videos_data = [
            {"title": "Part 1", "description": "First part"},
            {"title": "Part 2", "description": "Second part"},
            {"title": "Part 3", "description": "Third part"},
        ]
        
        base_time = datetime.utcnow() + timedelta(days=1)
        schedule = [
            {"video_index": 0, "scheduled_time": (base_time).isoformat()},
            {"video_index": 1, "scheduled_time": (base_time + timedelta(days=7)).isoformat()},
            {"video_index": 2, "scheduled_time": (base_time + timedelta(days=14)).isoformat()},
        ]
        
        result = await service.create_series(
            user_id=uuid4(),
            series_name="Test Series",
            videos=videos_data,
            schedule=schedule,
            target_platforms=["youtube"],
        )
        
        assert len(added_videos) == 3
        assert all(v.series_name == "Test Series" for v in added_videos)
        assert [v.series_order for v in added_videos] == [1, 2, 3]

    def test_get_videos_due_for_generation(self):
        """Test getting videos due for generation."""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [
            Mock(id=uuid4(), planning_status=PlanningStatus.PLANNED.value)
        ]
        mock_db.query.return_value = mock_query
        
        service = VideoPlanningService(mock_db)
        result = service.get_videos_due_for_generation(hours_ahead=1)
        
        assert len(result) == 1

    def test_get_videos_ready_to_post(self):
        """Test getting videos ready to post."""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [
            Mock(id=uuid4(), planning_status=PlanningStatus.READY.value)
        ]
        mock_db.query.return_value = mock_query
        
        service = VideoPlanningService(mock_db)
        result = service.get_videos_ready_to_post()
        
        assert len(result) == 1


class TestVideoPlanningServiceMonthlyPlan:
    """Test cases for monthly plan creation."""

    @pytest.mark.asyncio
    async def test_create_monthly_plan_variety(self):
        """Test creating a variety monthly plan."""
        mock_db = Mock()
        added_videos = []
        
        def capture_add(video):
            added_videos.append(video)
        mock_db.add.side_effect = capture_add
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        service = VideoPlanningService(mock_db)
        
        base_time = datetime.utcnow() + timedelta(days=1)
        plan = {
            "month": "February 2026",
            "plan_type": "variety",
            "total_videos": 4,
            "videos": [
                {"title": f"Video {i}", "description": f"Description {i}"}
                for i in range(4)
            ],
            "schedule": [
                {"video_index": i, "scheduled_time": (base_time + timedelta(days=i*7)).isoformat()}
                for i in range(4)
            ],
        }
        
        result = await service.create_monthly_plan(
            user_id=uuid4(),
            plan=plan,
        )
        
        assert len(added_videos) == 4
        # Variety plan should not have series_name
        assert all(v.series_name is None for v in added_videos)

    @pytest.mark.asyncio
    async def test_create_monthly_plan_single_series(self):
        """Test creating a single series monthly plan."""
        mock_db = Mock()
        added_videos = []
        
        def capture_add(video):
            added_videos.append(video)
        mock_db.add.side_effect = capture_add
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        service = VideoPlanningService(mock_db)
        
        base_time = datetime.utcnow() + timedelta(days=1)
        plan = {
            "month": "February 2026",
            "plan_type": "single_series",
            "total_videos": 4,
            "videos": [
                {"title": f"Part {i+1}", "description": f"Description {i}"}
                for i in range(4)
            ],
            "schedule": [
                {"video_index": i, "scheduled_time": (base_time + timedelta(days=i*7)).isoformat()}
                for i in range(4)
            ],
            "series_info": [{"name": "Monthly Series"}],
        }
        
        result = await service.create_monthly_plan(
            user_id=uuid4(),
            plan=plan,
        )
        
        assert len(added_videos) == 4
        # Single series plan should have series_name
        assert all(v.series_name == "Monthly Series" for v in added_videos)
