"""
Subtitle Service

Generates subtitle files (SRT and ASS format) from timing data.
Handles subtitle styling based on user preferences.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.models.user_generation_settings import (
    SubtitleStyle,
    SUBTITLE_STYLE_CONFIGS,
)

logger = logging.getLogger(__name__)


@dataclass
class TimingSegment:
    """A segment of text with timing information."""
    text: str
    start_ms: int
    end_ms: int
    
    @property
    def duration_ms(self) -> int:
        """Duration of this segment in milliseconds."""
        return self.end_ms - self.start_ms


class SubtitleService:
    """
    Service for generating subtitle files.
    
    Supports:
    - SRT format (simple, widely compatible)
    - ASS format (styled, used by FFmpeg)
    
    Subtitle styles:
    - classic: White text with black outline
    - modern: Clean with semi-transparent background
    - bold: Yellow text centered on screen
    - minimal: Subtle with dark background
    """
    
    # ASS file header template
    ASS_HEADER_TEMPLATE = """[Script Info]
Title: Synthora Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_line}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def __init__(self, style: str = SubtitleStyle.DEFAULT):
        """
        Initialize the subtitle service.
        
        Args:
            style: Subtitle style name (classic, modern, bold, minimal)
        """
        self.style = style if style in SubtitleStyle.ALL else SubtitleStyle.DEFAULT
        self.style_config = SUBTITLE_STYLE_CONFIGS.get(
            self.style, 
            SUBTITLE_STYLE_CONFIGS[SubtitleStyle.DEFAULT]
        )
    
    def generate_srt(self, segments: List[TimingSegment]) -> str:
        """
        Generate SRT format subtitle content.
        
        SRT is a simple format with just timing and text.
        
        Args:
            segments: List of timing segments
            
        Returns:
            SRT file content as string
        """
        if not segments:
            return ""
        
        lines = []
        
        for i, segment in enumerate(segments, start=1):
            start_time = self._ms_to_srt_time(segment.start_ms)
            end_time = self._ms_to_srt_time(segment.end_ms)
            
            lines.append(str(i))
            lines.append(f"{start_time} --> {end_time}")
            lines.append(segment.text)
            lines.append("")  # Empty line between entries
        
        return "\n".join(lines)
    
    def generate_ass(self, segments: List[TimingSegment]) -> str:
        """
        Generate ASS format subtitle content with styling.
        
        ASS (Advanced SubStation Alpha) supports rich styling
        and is used by FFmpeg for subtitle burning.
        
        Args:
            segments: List of timing segments
            
        Returns:
            ASS file content as string
        """
        if not segments:
            return ""
        
        # Generate style line
        style_line = self._generate_ass_style_line()
        
        # Generate header
        header = self.ASS_HEADER_TEMPLATE.format(style_line=style_line)
        
        # Generate dialogue lines
        dialogue_lines = []
        for segment in segments:
            start_time = self._ms_to_ass_time(segment.start_ms)
            end_time = self._ms_to_ass_time(segment.end_ms)
            
            # Escape special characters
            text = self._escape_ass_text(segment.text)
            
            dialogue_lines.append(
                f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
            )
        
        return header + "\n".join(dialogue_lines)
    
    def _generate_ass_style_line(self) -> str:
        """Generate the ASS style definition line."""
        config = self.style_config
        
        # Convert colors to ASS format (already in ASS format in config)
        primary_color = config.get("primary_color", "&HFFFFFF")
        outline_color = config.get("outline_color", "&H000000")
        back_color = config.get("background_color", "&H00000000")
        
        if back_color is None:
            back_color = "&H00000000"  # Transparent
        
        # Border style: 1 = outline + shadow, 3 = opaque box
        border_style = 3 if config.get("background_color") else 1
        
        style_parts = [
            "Default",                          # Name
            config.get("font_name", "Arial"),   # Fontname
            str(config.get("font_size", 24)),   # Fontsize
            primary_color,                       # PrimaryColour
            "&H000000FF",                        # SecondaryColour
            outline_color or "&H000000",        # OutlineColour
            back_color,                          # BackColour
            "0",                                 # Bold
            "0",                                 # Italic
            "0",                                 # Underline
            "0",                                 # StrikeOut
            "100",                               # ScaleX
            "100",                               # ScaleY
            "0",                                 # Spacing
            "0",                                 # Angle
            str(border_style),                   # BorderStyle
            str(config.get("outline_width", 2)),# Outline
            str(config.get("shadow", 0)),        # Shadow
            str(config.get("alignment", 2)),     # Alignment
            "10",                                # MarginL
            "10",                                # MarginR
            str(config.get("margin_v", 30)),     # MarginV
            "1",                                 # Encoding
        ]
        
        return "Style: " + ",".join(style_parts)
    
    def _ms_to_srt_time(self, ms: int) -> str:
        """
        Convert milliseconds to SRT time format.
        
        Format: HH:MM:SS,mmm
        
        Args:
            ms: Time in milliseconds
            
        Returns:
            SRT formatted time string
        """
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        millis = ms % 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
    
    def _ms_to_ass_time(self, ms: int) -> str:
        """
        Convert milliseconds to ASS time format.
        
        Format: H:MM:SS.cc (centiseconds)
        
        Args:
            ms: Time in milliseconds
            
        Returns:
            ASS formatted time string
        """
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        centiseconds = (ms % 1000) // 10
        
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
    
    def _escape_ass_text(self, text: str) -> str:
        """
        Escape special characters for ASS format.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text
        """
        # Replace newlines with ASS line break
        text = text.replace("\n", "\\N")
        
        # Escape curly braces (used for override tags)
        text = text.replace("{", "\\{")
        text = text.replace("}", "\\}")
        
        return text
    
    @staticmethod
    def segments_from_voice_response(
        voice_data: Dict[str, Any],
        provider: str,
    ) -> List[TimingSegment]:
        """
        Convert voice provider response to timing segments.
        
        Different providers return timing data in different formats.
        This method normalizes them to TimingSegment objects.
        
        Args:
            voice_data: Voice generation response data
            provider: Provider name
            
        Returns:
            List of TimingSegment objects
        """
        segments = []
        
        # Handle ElevenLabs format
        if provider == "elevenlabs":
            # ElevenLabs provides character-level timestamps
            # We'll aggregate to sentence level
            alignment = voice_data.get("alignment", {})
            chars = alignment.get("characters", [])
            char_times = alignment.get("character_start_times_seconds", [])
            char_durations = alignment.get("character_end_times_seconds", [])
            
            if chars and char_times and char_durations:
                segments = SubtitleService._aggregate_to_sentences(
                    chars, char_times, char_durations
                )
        
        # Handle OpenAI TTS format (no timing, estimate from text)
        elif provider == "openai_tts":
            text = voice_data.get("text", "")
            duration_ms = voice_data.get("duration_seconds", 0) * 1000
            segments = SubtitleService._estimate_timing_from_text(text, duration_ms)
        
        # Handle generic word-level timing
        elif "words" in voice_data:
            for word_data in voice_data["words"]:
                segments.append(TimingSegment(
                    text=word_data.get("word", word_data.get("text", "")),
                    start_ms=int(word_data.get("start", word_data.get("start_ms", 0)) * 1000)
                        if isinstance(word_data.get("start", word_data.get("start_ms", 0)), float)
                        else word_data.get("start_ms", 0),
                    end_ms=int(word_data.get("end", word_data.get("end_ms", 0)) * 1000)
                        if isinstance(word_data.get("end", word_data.get("end_ms", 0)), float)
                        else word_data.get("end_ms", 0),
                ))
        
        # Handle sentence-level timing
        elif "sentences" in voice_data:
            for sent_data in voice_data["sentences"]:
                segments.append(TimingSegment(
                    text=sent_data.get("text", ""),
                    start_ms=int(sent_data.get("start_ms", 0)),
                    end_ms=int(sent_data.get("end_ms", 0)),
                ))
        
        # Fallback: use timing_segments if provided
        elif "timing_segments" in voice_data:
            for seg in voice_data["timing_segments"]:
                segments.append(TimingSegment(
                    text=seg.get("text", ""),
                    start_ms=int(seg.get("start_ms", 0)),
                    end_ms=int(seg.get("end_ms", 0)),
                ))
        
        return segments
    
    @staticmethod
    def _aggregate_to_sentences(
        chars: List[str],
        start_times: List[float],
        end_times: List[float],
    ) -> List[TimingSegment]:
        """
        Aggregate character-level timing to sentence level.
        
        Args:
            chars: List of characters
            start_times: Start time for each character (seconds)
            end_times: End time for each character (seconds)
            
        Returns:
            List of sentence-level TimingSegments
        """
        if not chars:
            return []
        
        segments = []
        current_sentence = ""
        sentence_start = None
        sentence_end = None
        
        sentence_enders = ".!?"
        
        for i, char in enumerate(chars):
            if sentence_start is None:
                sentence_start = start_times[i] if i < len(start_times) else 0
            
            current_sentence += char
            sentence_end = end_times[i] if i < len(end_times) else sentence_start
            
            # Check if this ends a sentence
            if char in sentence_enders and current_sentence.strip():
                segments.append(TimingSegment(
                    text=current_sentence.strip(),
                    start_ms=int(sentence_start * 1000),
                    end_ms=int(sentence_end * 1000),
                ))
                current_sentence = ""
                sentence_start = None
        
        # Add remaining text
        if current_sentence.strip():
            segments.append(TimingSegment(
                text=current_sentence.strip(),
                start_ms=int((sentence_start or 0) * 1000),
                end_ms=int((sentence_end or 0) * 1000),
            ))
        
        return segments
    
    @staticmethod
    def _estimate_timing_from_text(
        text: str,
        total_duration_ms: int,
    ) -> List[TimingSegment]:
        """
        Estimate timing for text when no timing data is available.
        
        Splits text into sentences and estimates timing based on
        character count.
        
        Args:
            text: Full text
            total_duration_ms: Total audio duration in milliseconds
            
        Returns:
            List of estimated TimingSegments
        """
        if not text or total_duration_ms <= 0:
            return []
        
        # Split into sentences
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return [TimingSegment(text=text, start_ms=0, end_ms=total_duration_ms)]
        
        # Calculate timing based on character proportion
        total_chars = sum(len(s) for s in sentences)
        if total_chars == 0:
            total_chars = 1
        
        segments = []
        current_time = 0
        
        for sentence in sentences:
            proportion = len(sentence) / total_chars
            duration = int(total_duration_ms * proportion)
            
            segments.append(TimingSegment(
                text=sentence,
                start_ms=current_time,
                end_ms=current_time + duration,
            ))
            
            current_time += duration
        
        # Adjust last segment to match total duration
        if segments:
            segments[-1].end_ms = total_duration_ms
        
        return segments


def generate_subtitles(
    segments: List[TimingSegment],
    style: str = SubtitleStyle.DEFAULT,
    format: str = "ass",
) -> str:
    """
    Convenience function to generate subtitles.
    
    Args:
        segments: List of timing segments
        style: Subtitle style name
        format: Output format ("srt" or "ass")
        
    Returns:
        Subtitle file content
    """
    service = SubtitleService(style=style)
    
    if format.lower() == "srt":
        return service.generate_srt(segments)
    else:
        return service.generate_ass(segments)
