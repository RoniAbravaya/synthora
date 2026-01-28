"""
Video Generation Pipeline

This module contains all components for the video generation pipeline:
- Modular pipeline with provider system (new)
- State management for resume capability
- Legacy pipeline (for backwards compatibility)

Components:
- ModularGenerationPipeline: New provider-based pipeline
- PipelineStateManager: State tracking and persistence
- GenerationPipeline: Legacy pipeline (deprecated)
"""

# New modular pipeline
from app.services.generation.modular_pipeline import (
    ModularGenerationPipeline,
    PipelineConfig as ModularPipelineConfig,
    run_modular_pipeline,
    ConcurrencyError,
    VideoNotFoundError,
    VideoCancelledError,
)
from app.services.generation.state_manager import (
    PipelineStateManager,
    PipelineState,
    StepState,
)

# Legacy pipeline (for backwards compatibility)
from app.services.generation.pipeline import GenerationPipeline, PipelineConfig
from app.services.generation.script import ScriptGenerator
from app.services.generation.voice import VoiceGenerator
from app.services.generation.media import MediaFetcher
from app.services.generation.video_ai import VideoAIGenerator
from app.services.generation.assembly import VideoAssembler

__all__ = [
    # New modular pipeline
    "ModularGenerationPipeline",
    "ModularPipelineConfig",
    "run_modular_pipeline",
    "PipelineStateManager",
    "PipelineState",
    "StepState",
    "ConcurrencyError",
    "VideoNotFoundError",
    "VideoCancelledError",
    
    # Legacy (deprecated)
    "GenerationPipeline",
    "PipelineConfig",
    "ScriptGenerator",
    "VoiceGenerator",
    "MediaFetcher",
    "VideoAIGenerator",
    "VideoAssembler",
]

