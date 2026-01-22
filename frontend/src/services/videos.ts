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
    apiClient.get<{ video: Video }>(`/videos/${id}`),

  /**
   * Get video generation status.
   */
  getStatus: (id: string) =>
    apiClient.get<VideoStatusResponse>(`/videos/${id}/status`),

  /**
   * Start video generation.
   */
  generate: (data: VideoGenerationRequest) =>
    apiClient.post<VideoGenerationResponse>("/videos", data),

  /**
   * Retry failed video generation.
   */
  retry: (id: string) =>
    apiClient.post<VideoGenerationResponse>(`/videos/${id}/retry`),

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
}

