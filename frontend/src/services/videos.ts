/**
 * Videos API Service
 */

import { apiClient } from "@/lib/api"
import type { Video, VideoGenerationRequest, VideoStatus } from "@/types"

export interface VideoListResponse {
  videos: Video[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface VideoGenerationResponse {
  video: Video
  job_id: string
  message: string
}

export interface VideoStatusResponse {
  id: string
  status: VideoStatus
  progress: number
  current_step: string | null
  error_message: string | null
  error_payload: Record<string, unknown> | null
  video_url: string | null
  thumbnail_url: string | null
}

export interface DailyLimitResponse {
  used: number
  limit: number
  remaining: number
  resets_at: string
}

export interface SwapIntegrationRequest {
  step: string
  new_provider: string
}

// New video action types
export interface GenerateNowResponse {
  success: boolean
  video_id: string
  message: string
  job_id: string | null
}

export interface CancelVideoResponse {
  success: boolean
  video_id: string
  message: string
}

export interface RescheduleVideoResponse {
  success: boolean
  video_id: string
  new_scheduled_time: string
  message: string
}

export interface EditVideoRequest {
  title?: string
  prompt?: string
  template_id?: string
  target_platforms?: string[]
}

export interface ScheduledVideoListResponse {
  videos: Video[]
  total: number
  skip: number
  limit: number
}

export const videosService = {
  /**
   * Get user's videos.
   */
  list: (params?: { status?: VideoStatus; limit?: number; offset?: number }) =>
    apiClient.get<VideoListResponse>("/videos", { params }),

  /**
   * Get a specific video.
   */
  get: (id: string) =>
    apiClient.get<Video>(`/videos/${id}`).then(video => ({ video })),

  /**
   * Get video generation status.
   */
  getStatus: (id: string) =>
    apiClient.get<VideoStatusResponse>(`/videos/${id}/status`),

  /**
   * Start video generation.
   */
  generate: (data: VideoGenerationRequest) =>
    apiClient.post<Video>("/videos", data).then(video => ({ 
      video, 
      job_id: video.id, 
      message: "Video generation started" 
    })),

  /**
   * Retry failed video generation.
   */
  retry: (id: string) =>
    apiClient.post<Video>(`/videos/${id}/retry`).then(video => ({ 
      video, 
      job_id: video.id, 
      message: "Video retry started" 
    })),

  /**
   * Swap integration for a failed step.
   */
  swapIntegration: (id: string, data: SwapIntegrationRequest) =>
    apiClient.post<VideoGenerationResponse>(`/videos/${id}/swap-integration`, data),

  /**
   * Delete a video.
   */
  delete: (id: string) =>
    apiClient.delete<{ message: string }>(`/videos/${id}`),

  /**
   * Get daily generation limit status.
   */
  getDailyLimit: () =>
    apiClient.get<DailyLimitResponse>("/videos/daily-limit"),

  /**
   * Download video file.
   */
  getDownloadUrl: (id: string) =>
    apiClient.get<{ url: string; expires_at: string }>(`/videos/${id}/download`),

  // ==========================================================================
  // New Video Actions
  // ==========================================================================

  /**
   * Get list of scheduled/planned videos.
   */
  listScheduled: (params?: { limit?: number; skip?: number }) =>
    apiClient.get<ScheduledVideoListResponse>("/videos/scheduled", { params }),

  /**
   * Trigger immediate generation for a scheduled video.
   */
  generateNow: (id: string) =>
    apiClient.post<GenerateNowResponse>(`/videos/${id}/generate-now`),

  /**
   * Cancel a video generation in progress.
   */
  cancel: (id: string) =>
    apiClient.post<CancelVideoResponse>(`/videos/${id}/cancel`),

  /**
   * Reschedule a planned video.
   */
  reschedule: (id: string, scheduledPostTime: string) =>
    apiClient.put<RescheduleVideoResponse>(`/videos/${id}/reschedule`, null, {
      params: { scheduled_post_time: scheduledPostTime },
    }),

  /**
   * Edit a planned video's details.
   */
  edit: (id: string, data: EditVideoRequest) =>
    apiClient.put<Video>(`/videos/${id}/edit`, null, {
      params: data,
    }),
}

