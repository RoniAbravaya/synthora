/**
 * Video Planning API Service
 *
 * API client for video scheduling and content planning features.
 */

import { apiClient } from "@/lib/api"
import type {
  PlannedVideo,
  ScheduleVideoRequest,
  CreateSeriesRequest,
  CalendarVideoItem,
  AISuggestionData,
} from "@/types"

// =============================================================================
// Types
// =============================================================================

export interface ScheduleVideoResponse {
  video: PlannedVideo
  message: string
}

export interface CreateSeriesResponse {
  series_name: string
  videos: PlannedVideo[]
  total_videos: number
  message: string
}

export interface MonthlyContentPlan {
  month: string
  plan_type: "variety" | "single_series" | "multiple_series"
  total_videos: number
  videos: AISuggestionData[]
  schedule: Array<{ video_index: number; scheduled_time: string; target_platforms?: string[] }>
}

export interface CreateMonthlyPlanRequest {
  plan: MonthlyContentPlan
}

export interface CreateMonthlyPlanResponse {
  month: string
  videos: PlannedVideo[]
  total_videos: number
  message: string
}

export interface PlannedVideoListResponse {
  videos: PlannedVideo[]
  total: number
  series?: Record<string, PlannedVideo[]>
}

export interface TriggerGenerationResponse {
  message: string
  job_id: string
  video_id: string
  estimated_time: string
}

export interface CalendarViewResponse {
  items: CalendarVideoItem[]
  start_date: string
  end_date: string
  total_planned: number
  total_ready: number
  total_posted: number
  total_failed: number
}

export interface UpdatePlannedVideoRequest {
  scheduled_post_time?: string
  target_platforms?: string[]
  title?: string
  ai_suggestion_data?: AISuggestionData
  series_name?: string
  series_order?: number
}

// =============================================================================
// Service
// =============================================================================

export const videoPlanningService = {
  /**
   * Schedule a single video for future generation and posting.
   */
  scheduleVideo: (request: ScheduleVideoRequest) =>
    apiClient.post<ScheduleVideoResponse>("/video-planning/schedule", request),

  /**
   * Create a video series with multiple scheduled parts.
   */
  createSeries: (request: CreateSeriesRequest) =>
    apiClient.post<CreateSeriesResponse>("/video-planning/series", request),

  /**
   * Create a monthly content plan.
   */
  createMonthlyPlan: (request: CreateMonthlyPlanRequest) =>
    apiClient.post<CreateMonthlyPlanResponse>("/video-planning/monthly-plan", request),

  /**
   * Get all planned/scheduled videos.
   */
  getPlannedVideos: (options?: {
    status_filter?: string
    series_name?: string
    include_posted?: boolean
  }) =>
    apiClient.get<PlannedVideoListResponse>("/video-planning/planned", {
      params: options,
    }),

  /**
   * Update a planned video.
   */
  updatePlannedVideo: (videoId: string, updates: UpdatePlannedVideoRequest) =>
    apiClient.patch<PlannedVideo>(`/video-planning/planned/${videoId}`, updates),

  /**
   * Delete a planned video.
   */
  deletePlannedVideo: (videoId: string) =>
    apiClient.delete<{ message: string }>(`/video-planning/planned/${videoId}`),

  /**
   * Trigger immediate generation for a planned video.
   * Use force=true to reset a stuck "generating" video.
   */
  triggerGeneration: (videoId: string, force = false) =>
    apiClient.post<TriggerGenerationResponse>(
      `/video-planning/planned/${videoId}/generate-now`,
      undefined,
      { params: force ? { force: true } : undefined }
    ),

  /**
   * Get calendar view of planned videos.
   */
  getCalendarView: (startDate: string, endDate: string) =>
    apiClient.get<CalendarViewResponse>("/video-planning/calendar", {
      params: { start_date: startDate, end_date: endDate },
    }),
}
